from dataclasses import dataclass, field
from typing import Optional, List
from urllib.parse import urlparse, urlencode, urlunparse
from urllib.robotparser import RobotFileParser

import requests

from ..client.client_types import Repository
from . import Filter
from .filter_types import FilterDetailedReason, FilterReason


@dataclass(frozen=True)
class GitHubRobotsTxtFilter(Filter):
    """A filter that filters out repositories that have a .github/GH-ROBOTS.txt file that disallows the bot."""

    user_agents: List[str] = field(
        default_factory=lambda: ['JLLeitschuh/security-research']
    )

    def should_filter_repository(self, repository: 'Repository') -> List[FilterDetailedReason]:
        """Determine if the repository should be filtered out."""
        if repository.origin != 'github.com':
            return []
        user, repo = repository.path.split('/')
        return self.should_filter(user, repo, repository.branch)

    def should_filter(self, user: str, repository: str, branch: str) -> List[FilterDetailedReason]:
        """Determine if the repository should be filtered out.

        :param user: The user that owns the repository.
        :param repository: The repository to check.
        :param branch: The branch to check.
        :return: The reason for why the repository was filtered out, or an empty list if it should not be filtered out.
        """
        parser = self._get_gh_robots_txt(user, repository, branch)
        if parser is None:
            return []
        filter_reasons: List[FilterDetailedReason] = []
        for user_agent in self.user_agents:
            if parser.applies_to(user_agent):
                reason = f"Repository {user}/{repository} is disallowed by .github/GH-ROBOTS.txt containing agent " \
                         f"{user_agent}."
                filter_reasons.append(
                    FilterDetailedReason(
                        reason=FilterReason.GH_ROBOTS_TXT,
                        details=reason
                    )
                )
        return filter_reasons

    @classmethod
    def _get_gh_robots_txt(cls, user: str, repository: str, branch: str) -> Optional['_GitHubRobotFileParser']:
        """Get the contents of the .github/GH-ROBOTS.txt file if it's present."""
        url = cls._build_url(
            "https://raw.githubusercontent.com",
            f"/{user}/{repository}/{branch}/.github/GH-ROBOTS.txt"
        )
        response = requests.get(url, timeout=10)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            response.raise_for_status()
        return _GitHubRobotFileParser(response.text)

    @staticmethod
    def _build_url(base_url, path, args_dict=None) -> str:
        # Returns a list in the structure of urlparse.ParseResult
        if args_dict is None:
            args_dict = {}
        url_parts = list(urlparse(base_url))
        url_parts[2] = path
        url_parts[4] = urlencode(args_dict)
        return urlunparse(url_parts)


class _GitHubRobotFileParser(RobotFileParser):
    """A RobotFileParser that can be used to parse the contents of a .github/GH-ROBOTS.txt file."""

    def __init__(self, content: str):
        super().__init__()
        self.parse(content.splitlines())

    def applies_to(self, useragent: str) -> bool:
        """Determine if the user agent is allowed to access the repository.

        :param useragent: The user agent to check.
        :return: True if the user agent is allowed to access the repository.
        """
        for entry in self.entries:  # pytype: disable=attribute-error
            if self._applies_to_entry(useragent, entry):
                return True
        return False

    @staticmethod
    def _applies_to_entry(useragent: str, entry) -> bool:
        """Determine if the user agent is allowed to access the repository.

        :param useragent: The user agent to check.
        :return: True if the user agent is allowed to access the repository.
        """
        # check if this entry applies to the specified agent
        # split the name token and make it lower case
        useragent = useragent.lower()
        for agent in entry.useragents:
            if agent == '*':
                # we have the catch-all agent
                return True
            agent = agent.lower()
            if agent in useragent:
                return True
        return False
