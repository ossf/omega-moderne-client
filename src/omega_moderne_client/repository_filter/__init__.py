"""Filtering the set of repositories to generate pull requests for."""
import abc
from dataclasses import dataclass
from typing import List, Dict, Set

from omega_moderne_client.campaign.campaign_executor import RecipeExecutionResult
from omega_moderne_client.client.client_types import Repository
from omega_moderne_client.repository_filter.filter_types import FilterDetailedReason, FilteredRecipeExecutionResult, \
    FilterReason

__all__ = ['Filter', 'FilterDetailedReason', 'FilterReason']


class Filter(abc.ABC):
    """A filter that can be applied to a repository to determine if it should be filtered out."""

    @abc.abstractmethod
    def should_filter_repository(self, repository: 'Repository') -> List[FilterDetailedReason]:
        """Determine if the repository should be filtered out.

        :param repository: The repository to check.
        :return: The reason for why the repository was filtered out, or an empty list if it should not be filtered out.
        """
        raise NotImplementedError

    def filter_repositories(self, recipe_execution_result: RecipeExecutionResult) -> FilteredRecipeExecutionResult:
        """Filter the repositories in the given recipe execution result.

        :param recipe_execution_result: The recipe execution result to filter.
        :return: The filtered recipe execution result.
        """
        filtered_repositories: Dict[Repository, List[FilterDetailedReason]] = {}
        for repository in recipe_execution_result.repositories:
            filter_reasons = self.should_filter_repository(repository)
            if filter_reasons:
                filtered_repositories[repository] = filter_reasons
        return FilteredRecipeExecutionResult(
            run_id=recipe_execution_result.run_id,
            repositories=list(set(recipe_execution_result.repositories) - set(filtered_repositories.keys())),
            filtered_repositories=filtered_repositories
        )

    @classmethod
    def create_all(cls) -> 'Filter':
        """Create a filter that filters out repositories based on all reasons."""
        return cls.create_filter(set(FilterReason))

    @classmethod
    def create_filter(cls, filter_reasons: Set[FilterReason]) -> 'Filter':
        """Create a filter that filters out repositories based on the given reasons.

        :param filter_reasons: The reasons to filter out repositories.
        :return: The filter to use.
        """

        filters = [cls._filter_for_filter_reason(filter_reason) for filter_reason in filter_reasons]
        return CombinedFilter(filters=filters)

    @staticmethod
    def _filter_for_filter_reason(filter_reason: FilterReason) -> 'Filter':
        # pylint: disable=import-outside-toplevel
        from omega_moderne_client.repository_filter.github import \
            GitHubRobotsTxtFilter  # pylint: disable=cyclic-import
        from omega_moderne_client.repository_filter.top_ten_thousand import \
            TopTenThousandProjects  # pylint: disable=cyclic-import
        from omega_moderne_client.repository_filter.other import \
            OtherRepositoryFilter  # pylint: disable=cyclic-import

        if filter_reason is FilterReason.GH_ROBOTS_TXT:
            return GitHubRobotsTxtFilter()
        if filter_reason is FilterReason.TOP_TEN_THOUSAND:
            return TopTenThousandProjects.load_from_remote()
        if filter_reason is FilterReason.OTHER:
            return OtherRepositoryFilter()
        raise ValueError(f"Unknown filter reason: {filter_reason}")


@dataclass(frozen=True)
class CombinedFilter(Filter):
    """A filter that combines multiple filters together."""
    filters: List[Filter]

    def should_filter_repository(self, repository: 'Repository') -> List[FilterDetailedReason]:
        """Determine if the repository should be filtered out."""
        filter_reasons: List[FilterDetailedReason] = []
        for the_filter in self.filters:
            filter_reasons.extend(the_filter.should_filter_repository(repository))
        return filter_reasons
