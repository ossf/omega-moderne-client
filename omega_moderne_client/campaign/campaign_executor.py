import time
from dataclasses import dataclass
from typing import Any, List

from .campaign import Campaign
from omega_moderne_client.client.gpg_key_config import GpgKeyConfig
from omega_moderne_client.client.moderne_client import ModerneClient


@dataclass(frozen=True)
class CampaignExecutor:
    campaign: Campaign
    client: ModerneClient

    def execute_recipe_and_await(
            self,
            target_organization_id="Default"
    ) -> 'RecipeExecutionResult':
        print(f"Running campaign {self.campaign.name}...")
        run_id = self.client.run_campaign(
            self.campaign,
            target_organization_id=target_organization_id
        )
        print(f"Waiting for recipe run {run_id} to complete...")
        print(f"View live on Moderne https://{self.client.domain}/results/{run_id}")

        while True:
            state = self.client.query_recipe_run_status(run_id)
            print(f"Recipe {run_id} state: {state}")
            if state == "FINISHED":
                print("Recipe run FINISHED")
                break
            elif state == "CANCELED":
                print("Recipe run CANCELED")
                break
            time.sleep(5)

        print(f"Querying recipe run {run_id} results...")
        repositories = self.client.query_recipe_run_results(run_id)
        return RecipeExecutionResult(run_id=run_id, repositories=repositories)

    def execute_pull_request_generation(
            self,
            gpg_key_config: GpgKeyConfig,
            recipe_execution_result: 'RecipeExecutionResult',
    ):
        print(f"Forking and creating pull requests for campaign {self.campaign.name}...")
        commit_id = self.client.fork_and_pull_request(
            recipe_execution_result.run_id,
            self.campaign,
            gpg_key_config,
            recipe_execution_result.repositories
        )
        print(f"Waiting for commit job {commit_id} to complete...")
        while True:
            status = self.client.query_commit_job_status(commit_id)
            if status == "COMPLETED":
                print("Commit job COMPLETED")
                break
            time.sleep(5)
        print(f'Campaign {self.campaign.name} completed!')


@dataclass(frozen=True)
class RecipeExecutionResult:
    run_id: str
    repositories: List[Any]
