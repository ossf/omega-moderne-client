from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from omega_moderne_client.campaign.campaign_executor import RecipeExecutionResult
from omega_moderne_client.client.client_types import Repository


@dataclass(frozen=True)
class FilterDetailedReason:
    """A reason for why a repository was filtered out."""
    reason: 'FilterReason'
    """The details about why the repository was filtered out."""
    details: str


class FilterReason(Enum):
    """The high level reason for why a repository was filtered out."""
    GH_ROBOTS_TXT = "GH_ROBOTS_TXT"
    """The repository has a .github/GH-ROBOTS.txt file that disallows the bot."""
    TOP_TEN_THOUSAND = "TOP_TEN_THOUSAND"
    """The repository is in the top 10,000 critical OSS projects."""
    OTHER = "OTHER"
    """The repository was filtered out for some other reason."""
    # TODO: Use `StringEnum` when it's available in Python 3.11


@dataclass(frozen=True)
class FilteredRecipeExecutionResult(RecipeExecutionResult):
    """The result of a recipe execution that has been filtered."""
    filtered_repositories: Dict[Repository, List[FilterDetailedReason]]
