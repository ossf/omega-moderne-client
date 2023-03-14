from omega_moderne_client.campaign.campaign_executor import RecipeExecutionResult
from omega_moderne_client.client.client_types import Repository
from omega_moderne_client.repository_filter import Filter

OMEGA_MODERNE_CLIENT_REPOSITORY = Repository(
    origin="github.com",
    path="ossf/omega-moderne-client",
    branch="main",
)


def test_loaded_filters():
    repository_filter = Filter.create_all()
    assert repository_filter is not None
    filtered_repositories = repository_filter.filter_repositories(
        RecipeExecutionResult(
            run_id="run_id",
            repositories=[OMEGA_MODERNE_CLIENT_REPOSITORY]
        )
    )
    assert filtered_repositories is not None
    assert filtered_repositories.repositories == [OMEGA_MODERNE_CLIENT_REPOSITORY]
    assert not filtered_repositories.filtered_repositories
