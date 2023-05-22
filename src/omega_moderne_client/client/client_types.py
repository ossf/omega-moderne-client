from typing import NamedTuple, List


class RecipeRunSummary(NamedTuple):
    debugMarkers: int
    errorMarkers: int
    infoMarkers: int
    warningMarkers: int
    timeSavings: str
    totalChanged: int
    totalSearched: int
    state: str
    performance: 'RecipeRunPerformance'
    repository: 'Repository'


class RecipeRunPerformance(NamedTuple):
    recipeRun: str


class RecipeRunHistory(NamedTuple):
    recipeRun: 'RecipeRun'
    runId: str


class RecipeRun(NamedTuple):
    id: str
    recipe: 'Recipe'
    state: str


class Recipe(NamedTuple):
    id: str
    name: str
    tags: List[str]
    description: str


class Repository(NamedTuple):
    origin: str
    path: str
    branch: str

    def as_url(self):
        return f"https://{self.origin}/{self.path}"


class RepositoryInput(NamedTuple):
    origin: str
    path: str
    branch: str


class Commit(NamedTuple):
    modified: str
    repository: Repository
    resultLink: str
    state: str
    """One of: "CANCELED", "COMPLETED", "FAILED", "NO_CHANGES", "ORPHANED, "PROCESSING", or "QUEUED"."""
    stateMessage: str
