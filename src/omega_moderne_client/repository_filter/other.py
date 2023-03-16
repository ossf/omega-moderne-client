from dataclasses import dataclass, field
from typing import List, Dict

from ..client.client_types import Repository
from . import Filter, FilterDetailedReason, FilterReason


@dataclass(frozen=True)
class OtherRepositoryFilter(Filter):
    """A filter that filters out repositories based on the other reason."""
    repository_to_reasons: Dict[str, List[str]] = field(default_factory=lambda: {
        "https://github.com/wmaintw/DependencyCheck": [
            "Fork of the upstream `jeremylong/DependencyCheck`"
        ]
    })

    def should_filter_repository(self, repository: 'Repository') -> List[FilterDetailedReason]:
        """Determine if the repository should be filtered out.

        :param repository: The repository to check.
        :return: The reason for why the repository was filtered out, or an empty list if it should not be filtered out.
        """
        if repository.as_url() in self.repository_to_reasons:
            return [FilterDetailedReason(reason=FilterReason.OTHER, details=reason) for reason in
                    self.repository_to_reasons[repository.as_url()]]
        return []
