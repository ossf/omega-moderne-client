import abc
import asyncio
import base64
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Any, Dict, Optional, TypeVar, Generic, cast, Union

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
# noinspection PyPackageRequirements
from graphql import DocumentNode, ExecutionResult, GraphQLSchema

from omega_moderne_client.campaign.campaign import Campaign
from omega_moderne_client.client.client_types import RecipeRunSummary, Repository, Commit, RecipeRunPerformance
from omega_moderne_client.client.gpg_key_config import GpgKeyConfig

__all__ = ["ModerneClient"]


class ClientWrapper(abc.ABC):
    @abc.abstractmethod
    def execute(
            self,
            document: DocumentNode,
            variable_values: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict[str, Any], ExecutionResult]:
        pass

    @abc.abstractmethod
    def get_schema(self) -> GraphQLSchema:
        pass


@dataclass(frozen=True)
class ModerneClient:
    domain: str
    _client: ClientWrapper

    @staticmethod
    def load_from_env(domain: str = "public.moderne.io") -> "ModerneClient":
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
        return ModerneClient.create(api_token, domain=domain)

    @staticmethod
    def create(moderne_api_token: str, domain: str = "public.moderne.io") -> "ModerneClient":
        client = Client(
            transport=AIOHTTPTransport(
                url=f"https://api.{domain}/",
                headers={
                    "Authorization": f'Bearer {moderne_api_token}'
                },
                timeout=60,
            ),
            fetch_schema_from_transport=True,
            parse_results=True
        )

        class ModerneClientWrapper(ClientWrapper):
            def execute(
                    self,
                    document: DocumentNode,
                    variable_values: Optional[Dict[str, Any]] = None,
            ) -> Union[Dict[str, Any], ExecutionResult]:
                start = time.time()
                try:
                    return client.execute(document, variable_values=variable_values)
                except asyncio.exceptions.TimeoutError as error:
                    end = time.time()
                    raise TimeoutError(
                        f"The Moderne API timed out after {end - start} seconds. Please try again later."
                    ) from error

            def get_schema(self) -> GraphQLSchema:
                # Run a query to force the schema to get loaded
                self.execute(gql("{ __schema { types { name } } }"))
                return client.schema

        return ModerneClient(
            domain=domain,
            _client=ModerneClientWrapper()
        )

    def run_campaign(self, campaign: Campaign, target_organization_id: str = "Default", priority: str = "LOW") -> str:
        """
        Runs a campaign on the target organization.
        :param campaign: The campaign to execute.
        :param target_organization_id: The Moderne SaaS organization to run the campaign on.
        :param priority: The priority of the campaign. Can be one of "LOW" or "NORMAL".
        :return: The id of the recipe.
        """
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
            "yaml": campaign.get_recipe_yaml_base_64(),
            "priority": priority
        }
        # Execute the query on the transport
        result = self._client.execute(run_fix_query, variable_values=params)
        return result["runYamlRecipe"]["id"]

    def query_recipe_run_status(self, recipe_run_id: str) -> Dict[str, Any]:
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
        result = self._client.execute(recipe_run_results, variable_values=params)
        return result["recipeRun"]

    def query_recipe_run(
            self,
            recipe_run_id: str,
            filter_by: Optional[Dict[str, Any]] = None
    ) -> List['RecipeRunSummary']:
        return GetRecipeRunSummaryResults(self._client).get_all(recipe_run_id, filter_by=filter_by)

    def query_recipe_run_sorted_by_results(self, recipe_run_id: str) -> List['RecipeRunSummary']:
        return GetRecipeRunSummaryResults(self._client).get_all(
            recipe_run_id,
            filter_by={'statuses': ['FINISHED'], 'onlyWithResults': True},
            order_by={'direction': 'DESC', 'field': 'TOTAL_RESULTS'}
        ) + GetRecipeRunSummaryResults(self._client).get_first_page(
            recipe_run_id,
            filter_by={'statuses': ['ERROR', 'LOADING', 'QUEUED', 'RUNNING', 'CREATED', 'UNAVAILABLE']},
        )

    def query_recipe_run_repositories(
            self,
            recipe_run_id: str,
            filter_by: Optional[Dict[str, Any]] = None
    ) -> List['Repository']:
        return [summary.repository for summary in self.query_recipe_run(recipe_run_id, filter_by)]

    def query_recipe_run_results_repositories(self, recipe_run_id: str) -> List['Repository']:
        return self.query_recipe_run_repositories(recipe_run_id, {'statuses': ['FINISHED'], 'onlyWithResults': True})

    def fork_and_pull_request(
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
                "repositories": repositories
            },
            "organization": "BulkSecurityGeneratorProjectV2",  # TODO: Make this configurable
            "pullRequestTitle": campaign.pr_title,
            "pullRequestBody": base64.b64encode(campaign.pr_body.encode()).decode()
        }
        result = self._client.execute(fork_and_pull_request_query, variable_values=params)
        return result["forkAndPullRequest"]["id"]

    def query_commit_job_commits(self, commit_job_id: str) -> List[Commit]:
        return GetCommitJobCommits(self._client).call(commit_job_id)

    def query_commit_job_with_summary(self, commit_job_id: str) -> Dict[str, Any]:
        commit_job_summary_query = gql(
            # language=GraphQL
            """
            query getCommitJob($id: ID!) {
                commitJob(id: $id) {
                    id
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
        result = self._client.execute(
            commit_job_summary_query,
            variable_values=params
        )
        return result["commitJob"]

    def query_commit_job_status(self, commit_job_id: str) -> Dict[str, Any]:
        results: List[Commit] = self.query_commit_job_commits(commit_job_id)
        commit_job = self.query_commit_job_with_summary(commit_job_id)
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

    def schema(self) -> str:
        # noinspection PyPackageRequirements
        from graphql import print_schema  # pylint: disable=import-outside-toplevel
        return print_schema(self._client.get_schema())


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

    def request_page(self, after: Optional[str], **kwargs) -> dict:
        """
        Execute a paged query. Return the page of results.
        """
        params = {"after": after}
        params.update(kwargs)
        return self.client.execute(self.query, variable_values=params)

    def request_all(self, **kwargs) -> List[T]:
        """
        Take a paged query and return all results.
        """
        next_after = None
        results: List[T] = []
        while True:
            paged = self.map_page(self.request_page(next_after, **kwargs))
            results.extend([self.map_node(edge["node"]) for edge in paged["edges"]])
            if not paged["pageInfo"]["hasNextPage"]:
                break
            next_after = paged["pageInfo"]["endCursor"]
        return results

    def get_page_results(self, after: Optional[str], **kwargs) -> List[T]:
        """
        Execute a paged query. Return the page of results.
        """
        paged = self.map_page(self.request_page(after, **kwargs))
        return [self.map_node(edge["node"]) for edge in paged["edges"]]


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

    def get_first_page(
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
        # https://github.com/google/pytype/issues/1395
        return self.get_page_results(None, **args)  # pytype: disable=bad-return-type

    def get_all(
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
        # https://github.com/google/pytype/issues/1395
        return self.request_all(**args)  # pytype: disable=bad-return-type

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

    def call(self, commit_job_id: str) -> List[Commit]:
        # https://github.com/google/pytype/issues/1395
        return self.request_all(**{"id": commit_job_id})  # pytype: disable=bad-return-type

    def map_page(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return data["commitJob"]["commits"]


if __name__ == "__main__":
    print(ModerneClient.load_from_env().schema())
