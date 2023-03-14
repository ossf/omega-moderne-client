# pylint: disable=protected-access
from omega_moderne_client.repository_filter.filter_types import FilterReason
from omega_moderne_client.repository_filter.github import GitHubRobotsTxtFilter


def test_repository_with_gh_robots_txt():
    parser = GitHubRobotsTxtFilter._get_gh_robots_txt("JLLeitschuh", "code-sandbox", "main")
    assert parser is not None
    assert parser.applies_to("JLLeitschuh/security-research")
    assert not parser.applies_to('ossf/omega-moderne-client')


def test_repository_without_gh_robots_txt():
    parser = GitHubRobotsTxtFilter._get_gh_robots_txt("ossf", "omega-moderne-client", "main")
    assert parser is None


def test_repository_filter():
    gh_robots_filter = GitHubRobotsTxtFilter()
    reasons = gh_robots_filter.should_filter("JLLeitschuh", "code-sandbox", "main")
    assert len(reasons) == 1
    assert reasons[0].reason == FilterReason.GH_ROBOTS_TXT
    assert reasons[0].details ==\
           "Repository JLLeitschuh/code-sandbox is disallowed by .github/GH-ROBOTS.txt containing agent " \
           "JLLeitschuh/security-research."
