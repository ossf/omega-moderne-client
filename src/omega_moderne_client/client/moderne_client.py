import abc
import asyncio
import base64
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import TracebackType
from typing import List, Any, Dict, Optional, TypeVar, Generic, cast, Union, Type
from uuid import uuid1, UUID

from gql import gql, Client
from gql.client import AsyncClientSession
from gql.transport.aiohttp import AIOHTTPTransport
from graphql import DocumentNode, ExecutionResult, GraphQLSchema

from .client_types import RecipeRunSummary, Repository, Commit, RecipeRunPerformance, RecipeRun, RecipeRunHistory, \
    Recipe, RepositoryInput
from ..campaign.campaign import Campaign
from ..client.gpg_key_config import GpgKeyConfig

__all__ = ["ModerneClient"]

DEFAULT_DOMAIN = "app.moderne.io"


class ClientWrapper(abc.ABC):
    @abc.abstractmethod
    async def connect(self) -> None:
        pass

    @abc.abstractmethod
    async def execute(
            self,
            document: DocumentNode,
            variable_values: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], ExecutionResult]:
        pass

    @abc.abstractmethod
    async def get_schema(self) -> GraphQLSchema:
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        pass


@dataclass(frozen=True)
class ModerneClient:
    domain: str
    _client: ClientWrapper

    @classmethod
    def load_from_env(cls, domain: str = DEFAULT_DOMAIN) -> "ModerneClient":
        token_file = Path.home().joinpath('.moderne/token.txt')
        api_token: str
        if token_file.exists():
            with open(token_file, 'r', encoding='utf-8') as file:
                read_token = file.read().strip()
            if not read_token:
                raise ValueError(f"Token file {token_file} is empty")
            api_token = read_token
        else:
            read_token = os.getenv("MODERNE_API_TOKEN")
            if not read_token:
                raise ValueError(
                    "No token file found at `~/.moderne/token.txt` and " +
                    "`MODERNE_API_TOKEN` environment variable is not set!"
                )
            api_token = read_token
        return cls.create(api_token, domain=domain)

    @staticmethod
    def create(moderne_api_token: str, domain: str = DEFAULT_DOMAIN) -> "ModerneClient":
        # Some requests can take a very long time, for example, scheduling a recipe run
        # Modernes API will automatically time out after 60 seconds, we need to set a slightly lower timeout
        timeout = 58
        client = Client(
            transport=AIOHTTPTransport(
                url=f"https://api.{domain}/",
                headers={
                    "Authorization": f'Bearer {moderne_api_token}'
                },
                timeout=timeout
            ),
            fetch_schema_from_transport=True,
            execute_timeout=timeout,
            parse_results=True
        )

        class ModerneClientWrapper(ClientWrapper):
            session: AsyncClientSession = None

            async def connect(self) -> None:
                self.session = await client.connect_async(reconnecting=True, retry_execute=False)

            async def execute(
                    self,
                    document: DocumentNode,
                    variable_values: Optional[Dict[str, Any]] = None,
            ) -> Union[Dict[str, Any], ExecutionResult]:
                start = time.time()
                if self.session is None:
                    raise ValueError("Client is not connected! Did you use `async with` to wrap the ModerneClient?")
                try:
                    return await self.session.execute(document, variable_values=variable_values)
                except asyncio.exceptions.TimeoutError as error:
                    end = time.time()
                    raise asyncio.exceptions.TimeoutError(
                        f"The Moderne API timed out after {end - start} seconds. Please try again later."
                    ) from error

            async def get_schema(self) -> GraphQLSchema:
                # Run a query to force the schema to get loaded
                await self.execute(gql("{ __schema { types { name } } }"))
                return client.schema

            async def close(self) -> None:
                await client.close_async()

        return ModerneClient(
            domain=domain,
            _client=ModerneClientWrapper()
        )

    async def __aenter__(self) -> "ModerneClient":
        await self._client.connect()
        return self

    async def close(self):
        await self._client.close()

    async def __aexit__(
            self,
            exc_type: Optional[Type[BaseException]] = None,
            exc_val: Optional[BaseException] = None,
            exc_tb: Optional[TracebackType] = None,
    ) -> None:
        await self.close()

    async def run_organization_campaign(
            self,
            campaign: Campaign,
            target_organization_id: str = "Default",
            priority: str = "LOW"
    ) -> str:
        """
        Runs a campaign on the target organization.
        :param campaign: The campaign to execute.
        :param target_organization_id: The Moderne SaaS organization to run the campaign on.
        :param priority: The priority of the campaign. Can be one of "LOW" or "NORMAL".
        :return: The id of the recipe.
        """
        # A Hacky Solution:
        # The `runYamlRecipe` API endpoint can take longer than the Moderne gateway timeout of 60 seconds to respond.
        # Particularly, when we are launching a recipe run against 30k+ repositories.
        # When the gateway times out, we don't get the run ID back, so we need an alternate way to get it.
        #
        # As such, we embed our own custom 'uuid' in the recipe name, so that we can repeatedly poll the
        # `previousRecipeRuns` API endpoint to search for our `uuid` and get the run ID,
        # once the run has actually started.
        uuid = uuid1()
        run_fix_query = gql(
            # language=GraphQL
            """
            mutation runSecurityFix($organizationId: ID, $yaml: Base64!, $priority: RecipeRunPriority) {
              runYamlRecipe(organizationId: $organizationId, yaml: $yaml, priority: $priority) {
                id
                start
              }
            }
            """
        )

        params = {
            "organizationId": target_organization_id,
            "yaml": campaign.get_recipe_yaml_base_64(uuid),
            "priority": priority
        }
        # Execute the query on the transport
        try:
            result = await self._client.execute(run_fix_query, variable_values=params)
            return result["runYamlRecipe"]["id"]
        except asyncio.exceptions.TimeoutError as error:
            logging.warning(
                "The Moderne API timed out on 'runYamlRecipe'. Trying to find the recipe run with uuid %s", uuid
            )
            try:
                return (await self._find_recipe_run_with_uuid(uuid)).runId
            except ValueError as value_error:
                raise value_error from error

    async def _find_recipe_run_with_uuid(self, uuid: UUID) -> RecipeRunHistory:
        total_attempts = 20
        for attempt in range(0, total_attempts):
            try:
                run_history = await GetAllRecipeRunHistory(self._client).get_first_page()
            except asyncio.exceptions.TimeoutError:
                run_history = []
            for run in run_history:
                if str(uuid) in run.recipeRun.recipe.id:
                    return run
            logging.warning(
                "Attempt[%s/%s]: Could not find recipe run with uuid %s. Trying again in 5 seconds.",
                attempt + 1,
                total_attempts,
                uuid
            )
            await asyncio.sleep(10)
        raise ValueError(f"Could not find recipe run with uuid {uuid} after {total_attempts} attempts.")

    async def run_custom_filter_campaign(
            self,
            campaign: Campaign,
            repository_filter: List[RepositoryInput],
            priority: str = "LOW"
    ) -> str:
        run_fix_query = gql(
            # language=GraphQL
            """
            mutation runSecurityFix(
                $repositoryFilter: [RepositoryInput!],
                $yaml: Base64!,
                $priority: RecipeRunPriority
            ) {
              runYamlRecipe(repositoryFilter: $repositoryFilter, yaml: $yaml, priority: $priority) {
                id
                start
              }
            }
            """
        )
        params = {
            "repositoryFilter": [f._asdict() for f in repository_filter],
            "yaml": campaign.get_recipe_yaml_base_64(uuid1()),
            "priority": priority
        }
        result = await self._client.execute(run_fix_query, variable_values=params)
        return result["runYamlRecipe"]["id"]

    async def query_recipe_run_status(self, recipe_run_id: str) -> Dict[str, Any]:
        recipe_run_results = gql(
            # language=GraphQL
            """
            query getRecipeRun($id: ID!) {
                recipeRun(id: $id) {
                    id
                    state
                    totals {
                        totalFilesChanged
                        totalFilesSearched
                        totalRepositoriesSuccessful
                        totalRepositoriesWithErrors
                        totalRepositoriesWithResults
                        totalRepositoriesWithNoChanges
                        totalResults
                        totalTimeSavings
                    }
                }
            }
            """
        )
        params = {"id": recipe_run_id}
        result = await self._client.execute(recipe_run_results, variable_values=params)
        return result["recipeRun"]

    async def query_recipe_run(
            self,
            recipe_run_id: str,
            filter_by: Optional[Dict[str, Any]] = None
    ) -> List['RecipeRunSummary']:
        return await GetRecipeRunSummaryResults(self._client).get_all(recipe_run_id, filter_by=filter_by)

    async def query_recipe_run_sorted_by_results(self, recipe_run_id: str) -> List['RecipeRunSummary']:
        all_finished, unfinished = await asyncio.gather(
            GetRecipeRunSummaryResults(self._client).get_all(
                recipe_run_id,
                filter_by={'statuses': ['FINISHED'], 'onlyWithResults': True},
                order_by={'direction': 'DESC', 'field': 'TOTAL_RESULTS'}
            ),
            GetRecipeRunSummaryResults(self._client).get_first_page(
                recipe_run_id,
                filter_by={'statuses': ['ERROR', 'LOADING', 'QUEUED', 'RUNNING', 'CREATED', 'UNAVAILABLE']},
            )
        )
        return all_finished + unfinished

    async def query_recipe_run_repositories(
            self,
            recipe_run_id: str,
            filter_by: Optional[Dict[str, Any]] = None
    ) -> List['Repository']:
        return [summary.repository for summary in await self.query_recipe_run(recipe_run_id, filter_by)]

    async def query_recipe_run_results_repositories(self, recipe_run_id: str) -> List['Repository']:
        return await self.query_recipe_run_repositories(
            recipe_run_id, {'statuses': ['FINISHED'], 'onlyWithResults': True}
        )

    async def fork_and_pull_request(
            self,
            recipe_id: str,
            campaign: Campaign,
            gpg_key_config: GpgKeyConfig,
            repositories: List[Repository]
    ) -> str:
        fork_and_pull_request_query = gql(
            # language=GraphQL
            """
            mutation forkAndPullRequest(
              $commit: CommitInput!,
              $organization: String!,
              $pullRequestBody:Base64!,
              $pullRequestTitle:String!
            ) {
                forkAndPullRequest(
                    commit: $commit,
                    draft: false,
                    maintainerCanModify: true,
                    organization: $organization,
                    pullRequestBody: $pullRequestBody,
                    pullRequestTitle: $pullRequestTitle,
                    shouldPrefixOrganizationName: true
                ) {
                    id
                }
            }
            """
        )

        params = {
            "commit": {
                "branchName": campaign.branch,
                "gpgKey": {
                    "passphrase": gpg_key_config.key_passphrase,
                    "privateKey": gpg_key_config.key_private_key.replace("\\n", "\n"),
                    "publicKey": gpg_key_config.key_public_key.replace("\\n", "\n")
                },
                "message": campaign.commit_title,
                "extendedMessage": base64.b64encode(campaign.commit_extended.encode()).decode(),
                "recipeRunId": recipe_id,
                "repositories": [r._asdict() for r in repositories]
            },
            "organization": "BulkSecurityGeneratorProjectV2",  # TODO: Make this configurable
            "pullRequestTitle": campaign.pr_title,
            "pullRequestBody": base64.b64encode(campaign.pr_body.encode()).decode()
        }
        result = await self._client.execute(fork_and_pull_request_query, variable_values=params)
        return result["forkAndPullRequest"]["id"]

    async def query_commit_job_commits(self, commit_job_id: str) -> List[Commit]:
        return await GetCommitJobCommits(self._client).call(commit_job_id)

    async def query_commit_job_with_summary(self, commit_job_id: str) -> Dict[str, Any]:
        commit_job_summary_query = gql(
            # language=GraphQL
            """
            query getCommitJob($id: ID!) {
                commitJob(id: $id) {
                    id
                    state
                    completed
                    summaryResults {
                        count
                        failedCount
                        noChangeCount
                        successfulCount
                    }
                }
            }
            """
        )
        params = {"id": commit_job_id}
        result = await self._client.execute(
            commit_job_summary_query,
            variable_values=params
        )
        return result["commitJob"]

    async def query_commit_job_status(self, commit_job_id: str) -> Dict[str, Any]:
        results: List[Commit] = await self.query_commit_job_commits(commit_job_id)
        commit_job = await self.query_commit_job_with_summary(commit_job_id)
        summary_results = commit_job["summaryResults"]
        state: str
        if "state" in commit_job:
            # Not currently supported, but hopefully will be in the future.
            # https://linuxfoundation.slack.com/archives/C04HR6EJ38D/p1678137720981939
            state = commit_job["state"]
        elif "CANCELED" in (node.state for node in results):
            # TODO: This is a hack, we should be able to get the state from the commit job
            state = "CANCELED"
        elif summary_results["count"] == commit_job["completed"]:
            state = "COMPLETED"
        elif summary_results["failedCount"] + summary_results["noChangeCount"] + summary_results["successfulCount"] < \
                summary_results["count"]:
            state = "RUNNING"
        else:
            state = "COMPLETED"

        commit_job["commits"] = results
        commit_job["state"] = state
        return commit_job

    async def schema(self) -> str:
        # noinspection PyPackageRequirements
        from graphql import print_schema  # pylint: disable=import-outside-toplevel
        return print_schema(await self._client.get_schema())


T = TypeVar('T')


@dataclass(frozen=True)
class PagedQuery(abc.ABC, Generic[T]):
    client: ClientWrapper
    query: DocumentNode

    @abc.abstractmethod
    def map_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def map_node(self, node: Dict[str, Any]) -> T:
        return cast(T, node)

    async def request_page(self, after: Optional[str], **kwargs) -> dict:
        """
        Execute a paged query. Return the page of results.
        """
        params = {"after": after}
        params.update(kwargs)
        return await self.client.execute(self.query, variable_values=params)

    async def request_all(self, **kwargs) -> List[T]:
        """
        Take a paged query and return all results.
        """
        next_after = None
        results: List[T] = []
        while True:
            paged = self.map_page(await self.request_page(next_after, **kwargs))
            results.extend([self.map_node(edge["node"]) for edge in paged["edges"]])
            if not paged["pageInfo"]["hasNextPage"]:
                break
            next_after = paged["pageInfo"]["endCursor"]
        return results

    async def get_page_results(self, after: Optional[str], **kwargs) -> List[T]:
        """
        Execute a paged query. Return the page of results.
        """
        paged = self.map_page(await self.request_page(after, **kwargs))
        return [self.map_node(edge["node"]) for edge in paged["edges"]]


@dataclass(frozen=True)
class GetAllRecipeRunHistory(PagedQuery[RecipeRunHistory]):
    query: DocumentNode = field(default=gql(
        # language=GraphQL
        """
        query allRecipeRunHistory($after: String, $sortOrder: SortOrder = DESC, $filterBy: RecipeRunFilterInput) {
            allRecipeRuns(after: $after, sortOrder: $sortOrder, filterBy: $filterBy, first: 20) {
                count
                pageInfo {
                    hasNextPage
                    startCursor
                    endCursor
                }
                edges {
                    node {
                        runId
                        recipeRun {
                            id
                            recipe {
                                id
                                name
                                description
                                tags
                            }
                            state
                        }
                    }
                }

            }
        }
        """
    ))

    def map_node(self, node: Dict[str, Any]) -> RecipeRunHistory:
        node = node.copy()
        node["recipeRun"]["recipe"] = Recipe(**node["recipeRun"]["recipe"])
        node["recipeRun"] = RecipeRun(**node["recipeRun"])
        return RecipeRunHistory(**node)

    def map_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data["allRecipeRuns"]

    async def get_first_page(self) -> List[RecipeRunHistory]:
        return await self.get_page_results(None)


@dataclass(frozen=True)
class GetRecipeRunSummaryResults(PagedQuery[RecipeRunSummary]):
    query: DocumentNode = field(default=gql(
        # language=GraphQL
        """
        query getRecipeRun(
            $id: ID!,
            $after: String,
            $filterBy: SummaryResultsFilterInput,
            $orderBy: SummaryResultsOrderInput
        ) {
          recipeRun(id: $id) {
            id
            state
            summaryResultsPages(after: $after, filterBy: $filterBy, orderBy: $orderBy) {
              pageInfo {
                hasNextPage
                startCursor
                endCursor
              }
              count
              edges {
                node {
                  debugMarkers
                  errorMarkers
                  infoMarkers
                  warningMarkers
                  timeSavings
                  totalChanged
                  totalSearched
                  state
                  performance {
                    recipeRun
                  }
                  repository {
                    origin
                    path
                    branch
                  }
                }
              }
            }
          }
        }
        """
    ))

    def map_node(self, node: Dict[str, Any]) -> RecipeRunSummary:
        node = node.copy()
        node["performance"] = RecipeRunPerformance(**node["performance"])
        node["repository"] = Repository(**node["repository"])
        return RecipeRunSummary(**node)

    async def get_first_page(
            self,
            recipe_run_id: str,
            filter_by: Optional[Dict[str, Any]] = None,
            order_by: Optional[Dict[str, Any]] = None,
    ) -> List[RecipeRunSummary]:
        args = {"id": recipe_run_id}
        if filter_by:
            args["filterBy"] = filter_by
        if order_by:
            args["orderBy"] = order_by
        return await self.get_page_results(None, **args)

    async def get_all(
            self,
            recipe_run_id: str,
            filter_by: Optional[Dict[str, Any]] = None,
            order_by: Optional[Dict[str, Any]] = None,
    ) -> List[RecipeRunSummary]:
        args = {"id": recipe_run_id}
        if filter_by:
            args["filterBy"] = filter_by
        if order_by:
            args["orderBy"] = order_by
        return await self.request_all(**args)

    def map_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data["recipeRun"]["summaryResultsPages"]


@dataclass(frozen=True)
class GetCommitJobCommits(PagedQuery[Commit]):
    query: DocumentNode = field(default=gql(
        # language=GraphQL
        """
        query getCommitJob($id: ID!, $after: String) {
            commitJob(id: $id) {
                id
                completed
                commits(after: $after) {
                    pageInfo {
                        hasNextPage
                        startCursor
                        endCursor
                    }
                    count
                    edges {
                        node {
                            modified
                            repository {
                                origin
                                path
                                branch
                            }
                            resultLink
                            state
                            stateMessage
                        }
                    }
                }
                summaryResults {
                    count
                    failedCount
                    noChangeCount
                    successfulCount
                }
            }
        }
        """
    ))

    def map_node(self, node: Dict[str, Any]) -> Commit:
        node = node.copy()
        node["repository"] = Repository(**node["repository"])
        return Commit(**node)

    async def call(self, commit_job_id: str) -> List[Commit]:
        return await self.request_all(**{"id": commit_job_id})

    def map_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data["commitJob"]["commits"]


if __name__ == "__main__":
    async def main():
        async with ModerneClient.load_from_env() as client:
            print(await client.schema())


    asyncio.run(main())
