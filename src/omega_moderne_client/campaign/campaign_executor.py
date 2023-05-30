import abc
import asyncio
from dataclasses import dataclass
from typing import Any, List, Dict

from .campaign import Campaign
from ..client.client_types import RecipeRunSummary, Repository, RepositoryInput
from ..client.gpg_key_config import GpgKeyConfig
from ..client.moderne_client import ModerneClient


@dataclass(frozen=True)
class CampaignExecutor:
    client: ModerneClient
    progress_monitor: 'CampaignExecutorProgressMonitor'

    async def launch_recipe_against_organization_id(self, campaign: Campaign, target_organization_id: str = "Default"):
        run_id = await self.client.run_organization_campaign(
            campaign,
            target_organization_id=target_organization_id
        )
        self.progress_monitor.on_recipe_run_started(run_id)
        return run_id

    async def launch_recipe_against_repositories(self, campaign: Campaign, repository_filter: List[RepositoryInput]):
        run_id = await self.client.run_custom_filter_campaign(
            campaign,
            repository_filter=repository_filter
        )
        self.progress_monitor.on_recipe_run_started(run_id)
        return run_id

    async def await_recipe(self, run_id: str) -> 'RecipeExecutionResult':
        previous = {}
        while True:
            status = await self.client.query_recipe_run_status(run_id)
            state = status["state"]
            if status != previous:
                # Only print if the status has changed
                recipe_run_summaries = await self.client.query_recipe_run_sorted_by_results(run_id)
                self.progress_monitor.on_recipe_progress(run_id, state, status["totals"], recipe_run_summaries)
                previous = status
            if state in ("FINISHED", "CANCELED"):
                self.progress_monitor.on_recipe_run_completed(run_id, state)
                break
            await asyncio.sleep(5)

        repositories_with_results = await self.client.query_recipe_run_results_repositories(run_id)
        return RecipeExecutionResult(run_id=run_id, repositories=repositories_with_results)

    async def launch_pull_request(
            self,
            campaign: Campaign,
            gpg_key_config: GpgKeyConfig,
            recipe_execution_result: 'RecipeExecutionResult'
    ) -> str:
        commit_id = await self.client.fork_and_pull_request(
            recipe_execution_result.run_id,
            campaign,
            gpg_key_config,
            recipe_execution_result.repositories
        )
        self.progress_monitor.on_pull_request_generation_started(commit_id)
        return commit_id

    async def await_pull_request(self, commit_id: str):
        while True:
            job_state = await self.client.query_commit_job_status(commit_id)
            state = job_state["state"]
            self.progress_monitor.on_pull_request_generation_progress(commit_id, state, job_state["commits"])
            if state != "RUNNING":
                self.progress_monitor.on_pull_request_generation_completed(commit_id, state)
                break
            await asyncio.sleep(5)


@dataclass(frozen=True)
class RecipeExecutionResult:
    run_id: str
    repositories: List[Repository]


class CampaignExecutorProgressMonitor(abc.ABC):

    @abc.abstractmethod
    def on_recipe_run_started(self, run_id: str) -> None:
        pass

    @abc.abstractmethod
    def on_recipe_progress(
            self,
            run_id: str,
            state: str,
            totals: Dict[str, Any],
            repository_run_summaries: List['RecipeRunSummary']
    ) -> None:
        pass

    @abc.abstractmethod
    def on_recipe_run_completed(self, run_id: str, state: str) -> None:
        pass

    @abc.abstractmethod
    def on_pull_request_generation_started(self, commit_id: str) -> None:
        pass

    @abc.abstractmethod
    def on_pull_request_generation_progress(self, commit_id: str, state: str, commits: Dict[str, Any]) -> None:
        pass

    @abc.abstractmethod
    def on_pull_request_generation_completed(self, commit_id: str, state: str) -> None:
        pass


@dataclass(frozen=True)
class PrintingCampaignExecutorProgressMonitor(CampaignExecutorProgressMonitor):
    domain: str

    # noinspection PyMethodMayBeStatic
    def print(self, *args):
        print(*args)

    def on_recipe_run_started(self, run_id: str) -> None:
        self.print(f"Waiting for recipe run {run_id} to complete...")
        self.print(f"View live on Moderne https://{self.domain}/results/{run_id}")

    def on_recipe_progress(
            self,
            run_id: str,
            state: str,
            totals: Dict[str, Any],
            repository_run_summaries: List['RecipeRunSummary']
    ) -> None:
        self.print(f"Recipe {run_id} state: {state} totals: ", totals)

    def on_recipe_run_completed(self, run_id: str, state: str) -> None:
        self.print(f"Recipe run {state}")
        self.print(f"Querying recipe run {run_id} results...")

    def on_pull_request_generation_started(self, commit_id: str) -> None:
        self.print(f"Waiting for commit job {commit_id} to complete...")
        self.print(f"View live on Moderne https://{self.domain}/commits/{commit_id}")

    def on_pull_request_generation_progress(self, commit_id: str, state: str, commits: Dict[str, Any]) -> None:
        self.print(f"Commit job {commit_id} state: {state} commits:", commits)

    def on_pull_request_generation_completed(self, commit_id: str, state: str) -> None:
        self.print(f"Pull request generation for commit run {commit_id} completed with state {state}")
