import csv
from dataclasses import dataclass
from typing import List, Dict

import requests

from omega_moderne_client.client.client_types import Repository
from omega_moderne_client.repository_filter import Filter
from omega_moderne_client.repository_filter.filter_types import FilterDetailedReason, FilterReason


@dataclass(frozen=True)
class TopTenThousandProjects(Filter):
    list: List[Dict[str, str]]

    def should_filter_repository(self, repository: 'Repository') -> List[FilterDetailedReason]:
        repository_url = f"https://{repository.origin}/{repository.path}"
        for project in self.list:
            if project['URL'] == repository_url:
                return [FilterDetailedReason(
                    FilterReason.TOP_TEN_THOUSAND,
                    'The repository is in the top 10,000 critical OSS projects.'
                )]
        return []

    @staticmethod
    def load_from_remote() -> 'TopTenThousandProjects':
        # pylint: disable=line-too-long
        csv_url = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQJjUIa78qOs19mmZ2AmpehplONAsnAsAoji-oQcd8phurjEyoG6_BgPeTgCYzAtEzgkC_W6Bx2LZOD/pub?output=csv'  # noqa
        response = requests.get(csv_url, timeout=10)
        response.raise_for_status()
        # Pre-filter for elements that have a URL
        top_ten_thousand_csv = [element for element in csv.DictReader(response.text.splitlines()) if element['URL']]
        return TopTenThousandProjects(top_ten_thousand_csv)
