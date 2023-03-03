import base64
import os
from dataclasses import dataclass
from typing import List, Any, Dict

from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

from omega_moderne_client.campaign.campaign import Campaign
from omega_moderne_client.client.gpg_key_config import GpgKeyConfig


@dataclass(frozen=True)
class ModerneClient:
    domain: str
    _client: Client

    @staticmethod
    def load_from_env() -> "ModerneClient":
        api_token = os.getenv("MODERNE_API_TOKEN")
        if not api_token:
            raise Exception("`MODERNE_API_TOKEN` environment variable is not set")
        return ModerneClient.create(api_token)

    @staticmethod
    def create(moderne_api_token: str, domain: str = "public.moderne.io") -> "ModerneClient":
        return ModerneClient(
            domain=domain,
            _client=Client(
                transport=AIOHTTPTransport(
                    url=f"https://api.{domain}/",
                    headers={
                        "Authorization": f'Bearer {moderne_api_token}'
                    }
                ),
                fetch_schema_from_transport=True,
            )
        )

    def run_campaign(self, campaign: Campaign, target_organization_id: str = "Default") -> str:
        """
        Runs a campaign on the target organization.
        :param campaign: The campaign to execute.
        :param target_organization_id: The Moderne SaaS organization to run the campaign on.
        :return: The id of the recipe.
        """
        run_fix_query = gql(
            # language=GraphQL
            """
            # noinspection GraphQLUnresolvedReference
            mutation runSecurityFix($organizationId: ID, $yaml: Base64!) {
              runYamlRecipe(organizationId: $organizationId, yaml: $yaml) {
                id
                start
              }
            }
            """
        )

        params = {
            "organizationId": target_organization_id,
            "yaml": campaign.get_recipe_yaml_base_64()
        }
        # Execute the query on the transport
        result = self._client.execute(run_fix_query, variable_values=params)
        print(result)
        return result["runYamlRecipe"]["id"]

    def query_recipe_run_status(self, recipe_run_id: str) -> str:
        recipe_run_results = gql(
            # language=GraphQL
            """
            # noinspection GraphQLUnresolvedReference
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
                        totalResults
                        totalTimeSavings
                    }
                }
            }
            """
        )
        params = {"id": recipe_run_id}
        result = self._client.execute(recipe_run_results, variable_values=params)
        print(result)
        return result["recipeRun"]["state"]

    def query_recipe_run_results(self, recipe_run_id: str) -> List[Dict[str, Any]]:
        def query_recipient_run_results_page(after: int) -> dict:
            recipe_run_results = gql(
                # language=GraphQL
                """
                # noinspection GraphQLUnresolvedReference
                query getRecipeRun($id: ID!, $after: String) {
                  recipeRun(id: $id) {
                    id
                    state
                    summaryResultsPages(after: $after, filterBy: {statuses: [FINISHED], onlyWithResults:true}) {
                      pageInfo {
                        hasNextPage
                        startCursor
                        endCursor
                      }
                      count
                      edges {
                        node {
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
            )
            params = {
                "id": recipe_run_id,
                "after": str(after)
            }
            result = self._client.execute(recipe_run_results, variable_values=params)
            return result["recipeRun"]["summaryResultsPages"]

        next_after = -1
        results: List[Any] = []
        while True:
            page = query_recipient_run_results_page(next_after)
            results.extend([edge["node"]["repository"] for edge in page["edges"]])
            if not page["pageInfo"]["hasNextPage"]:
                break
            next_after = page["pageInfo"]["endCursor"]

        return results

    def fork_and_pull_request(
            self,
            recipe_id: str,
            campaign: Campaign,
            gpg_key_config: GpgKeyConfig,
            repositories: List[Dict[str, str]]
    ) -> str:
        fork_and_pull_request_query = gql(
            # language=GraphQL
            """
            # noinspection GraphQLUnresolvedReference
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
        # Execute the query on the transport
        # print(json.dumps(params, indent=4))
        result = self._client.execute(fork_and_pull_request_query, variable_values=params)
        print(result)
        return result["forkAndPullRequest"]["id"]

    def query_commit_job_status(self, commit_job_id: str) -> str:
        def query_commit_job_status_page(after: int) -> dict:
            commit_job_status_query = gql(
                # language=GraphQL
                """
                # noinspection GraphQLUnresolvedReference
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
                                        weight
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
            )
            params = {
                "id": commit_job_id
            }
            if after is not None:
                params["after"] = str(after)
            result = self._client.execute(commit_job_status_query, variable_values=params)
            print(result)
            return result

        next_after = None
        results: List[Any] = []
        while True:
            commit_status = query_commit_job_status_page(next_after)["commitJob"]
            page = commit_status["commits"]
            results.extend([edge["node"] for edge in page["edges"]])
            if not page["pageInfo"]["hasNextPage"]:
                break
            next_after = page["pageInfo"]["endCursor"]
        summary_results = commit_status["summaryResults"]
        print(f"Summary results: {summary_results}")
        if summary_results["count"] == commit_status["completed"]:
            return "COMPLETED"
        elif summary_results["failedCount"] + summary_results["noChangeCount"] + summary_results["successfulCount"] < \
                summary_results["count"]:
            return "RUNNING"
        else:
            return "COMPLETED"
