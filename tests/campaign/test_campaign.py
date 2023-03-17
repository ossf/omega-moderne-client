import asyncio
import re

import aiohttp
import markdown
from aiounittest.case import AsyncTestCase

from omega_moderne_client.campaign.campaign import Campaign


def get_links_from_markdown(markdown_content: str) -> set[str]:
    html = markdown.markdown(markdown_content)
    links = list(set(re.findall(r'href=[\'"]?([^\'" >]+)', html)))
    return set(filter(lambda l: l[0] != "{" and 'mailto:' not in l, links))


class CachingLinkChecker:
    _headers = {'User-Agent': 'Mozilla/5.0'}

    def __init__(self):
        self.session = None
        self.cache = {}

    async def __aenter__(self) -> 'CachingLinkChecker':
        if not self.session:
            # GitHub's rate limiter is pretty aggressive, so we need to limit the number of connections
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=5)
            self.session = aiohttp.ClientSession(connector=connector)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            self.session = None

    async def check_link(self, link: str) -> int:
        if link in self.cache:
            return self.cache[link]
        if not self.session:
            raise RuntimeError("Must enter context manager before checking links!")
        async with self.session.head(link, allow_redirects=True, headers=self._headers, timeout=10) as resp:
            self.cache[link] = resp.status
            return resp.status


class TestCampaign(AsyncTestCase):
    link_cache = CachingLinkChecker()

    async def test_load_one_campaign(self):
        campaign = Campaign.load('http_in_gradle_build')
        assert campaign.name == 'http_in_gradle_build'
        async with self.link_cache:
            await self.assert_campaign(campaign)

    async def test_load_all_campaigns(self):
        campaigns = Campaign.load_all()
        assert len(campaigns) >= 6
        async with self.link_cache:
            for campaign in campaigns:
                await self.assert_campaign(campaign)

    async def assert_campaign(self, campaign: Campaign):
        self.assert_string_field_is_sane('name', campaign.name)
        self.assert_string_field_is_sane('branch', campaign.branch)
        self.assert_string_field_is_sane('recipe_id', campaign.recipe_id)
        self.assert_string_field_is_sane('commit_title', campaign.commit_title)
        assert campaign.commit_title.startswith('vuln-fix: ')
        self.assert_string_field_is_sane('commit_extended', campaign.commit_extended)
        self.assert_commit_extended_is_sane(campaign.commit_extended)
        self.assert_string_field_is_sane('pr_title', campaign.pr_title)
        self.assert_string_field_is_sane('pr_body', campaign.pr_body)
        self.assert_long_field_is_stane('pr_body', campaign.pr_body)
        await self.assert_pr_body_is_sane(campaign.pr_body)

    @staticmethod
    def assert_long_field_is_stane(field_name: str, field_value: str):
        assert field_value.endswith('\n'), f"{field_name} must end with a newline"
        assert not field_value.endswith('\n\n'), f"{field_name} must not end with two newlines"
        assert not field_value.startswith('\n'), f"{field_name} must not start with a newline"

    @staticmethod
    def assert_string_field_is_sane(field: str, string: str):
        assert string is not None, f"{field} is None"
        assert not string.isspace(), f"{field} is empty"
        assert not string.endswith(' '), f"{field} ends with a space"
        assert not string.startswith(' '), f"{field} starts with a space"

    def assert_commit_extended_is_sane(self, commit_extended: str):
        self.assert_long_field_is_stane('commit_extended', commit_extended)
        lines = commit_extended.splitlines()
        assert any(line.startswith('Weakness: CWE-') for line in lines), f"Missing 'Weakness:' in {commit_extended}"
        assert any(line.startswith('Severity: ') for line in lines), f"Missing 'Severity:' in {commit_extended}"
        assert any(line.startswith('CVSS: ') for line in lines), f"Missing 'CVSS:' in {commit_extended}"
        assert any(line.startswith('Detection: ') for line in lines), f"Missing 'Detection:' in {commit_extended}"

        assert any(line.startswith('Reported-by: ') for line in lines), f"Missing 'Reported-by:' in {commit_extended}"
        assert any(
            line.startswith('Signed-off-by: ') for line in lines), f"Missing 'Signed-off-by:' in {commit_extended}"

    async def assert_pr_body_is_sane(self, pr_body: str):
        links = get_links_from_markdown(pr_body)
        await asyncio.gather(*map(self.assert_link_is_valid, links))

    async def assert_link_is_valid(self, link: str):
        self.assertEqual(await self.link_cache.check_link(link), 200, f"Link {link} is not valid")
