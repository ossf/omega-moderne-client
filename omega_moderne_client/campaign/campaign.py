import base64
from dataclasses import dataclass
from importlib.abc import Traversable
from importlib.resources import files
from typing import Tuple, List


@dataclass(frozen=True)
class Campaign:
    """
    Represents a campaign to run with Moderne.

    Use the `Campaign.create` method to load a campaign from the `campaigns` directory.
    """
    name: str
    recipe_id: str
    branch: str
    commit_title: str
    commit_extended: str
    pr_title: str
    pr_body: str

    def get_recipe_yaml(self) -> str:
        # language=yaml
        return f"""\
        type: specs.openrewrite.org/v1beta/recipe
        name: org.jlleitschuh.research.SecurityFixRecipe
        displayName: Apply `{self.recipe_id}`
        description: >
         Applies the `{self.recipe_id}` to non-test sources first, if changes are made, then apply to all sources.
        applicability:
          anySource:
            - org.openrewrite.java.search.IsLikelyNotTest
            - {self.recipe_id}
        recipeList:
          - {self.recipe_id}
        """

    def get_recipe_yaml_base_64(self) -> str:
        return base64.b64encode(self.get_recipe_yaml().encode('utf-8')).decode('utf-8')

    @classmethod
    def load(cls, name: str) -> 'Campaign':
        commit = cls._load_file_contents_as_title_and_body(name, "commit.txt")
        pr_message = cls._load_file_contents_as_title_and_body(name, "pr_message.md")
        return Campaign(
            name=name,
            recipe_id=cls._load_file_contents(name, "recipe.txt").strip(),
            branch=cls._load_file_contents(name, "branch_name.txt").strip(),
            commit_title=commit[0],
            commit_extended=commit[1],
            pr_title=pr_message[0],
            pr_body=pr_message[1],
        )

    @classmethod
    def load_all(cls) -> List['Campaign']:
        return [cls.load(campaign) for campaign in cls.list_campaigns()]

    @classmethod
    def list_campaigns(cls) -> List[str]:
        return [file.name for file in cls._campaigns_dir().iterdir()]

    @staticmethod
    def _campaigns_dir() -> Traversable:
        return files('omega_moderne_client.campaign').joinpath('campaigns')

    @classmethod
    def _load_campaign_resource(cls, campaign: str, path: str) -> Traversable:
        resource = cls._campaigns_dir().joinpath(campaign).joinpath(path)
        if not resource.is_file():
            raise ValueError(f"File {path} does not exist, and must to create a campaign")
        return resource

    @classmethod
    def _load_file_contents(cls, campaign: str, path: str) -> str:
        resource = cls._load_campaign_resource(campaign, path)
        # noinspection PyTypeChecker
        with open(resource, 'r', encoding='utf-8') as file:  # pytype: disable=wrong-arg-types
            return file.read()

    @classmethod
    def _load_file_contents_as_title_and_body(cls, campaign: str, path: str) -> Tuple[str, str]:
        resource = cls._load_campaign_resource(campaign, path)
        # noinspection PyTypeChecker
        with open(resource, 'r', encoding='utf-8') as file:  # pytype: disable=wrong-arg-types
            return file.readline(), file.read()
