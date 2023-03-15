from omega_moderne_client.client.client_types import Repository
from omega_moderne_client.repository_filter.filter_types import FilterReason
from omega_moderne_client.repository_filter.top_ten_thousand import TopTenThousandProjects


def test_load_top_ten_thousand():
    top_ten_thousand = TopTenThousandProjects.load_from_remote()
    assert len(top_ten_thousand.list) >= 5_000
    omega_filter_details = top_ten_thousand.should_filter_repository(
        Repository(**{'origin': 'github.com', 'path': 'ossf/omega-moderne-client', 'branch': 'main'})
    )
    assert len(omega_filter_details) == 0
    filter_details = top_ten_thousand.should_filter_repository(
        Repository(**{'origin': 'github.com', 'path': 'apache/struts', 'branch': 'main'})
    )
    assert len(filter_details) == 1
    assert filter_details[0].reason == FilterReason.TOP_TEN_THOUSAND
    assert filter_details[0].details == 'The repository is in the top 10,000 critical OSS projects.'
