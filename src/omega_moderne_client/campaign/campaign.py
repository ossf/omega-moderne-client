import base64
from dataclasses import dataclass
from importlib.abc import Traversable
from importlib.resources import files
from typing import Tuple, List

import yaml
from liquid import Template


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
        return cls._load(CampaignGlobals.load(), name)

    @classmethod
    def _load(cls, campaign_globals: 'CampaignGlobals', name: str) -> 'Campaign':
        campaign_yaml = yaml.safe_load(cls._load_file_contents(name, "campaign.yaml"))
        recipe_id = campaign_yaml['recipe']['id']
        branch = campaign_yaml['branch_name']
        commit_title, commit_extended = cls._load_file_contents_as_title_and_body(name, "commit.txt")
        commit_extended = commit_extended + campaign_globals.get_commit_footer(campaign_yaml)
        pr_title, pr_body = cls._load_file_contents_as_title_and_body(name, "pr_message.md")
        pr_body = pr_body + campaign_globals.get_pr_message_footer(campaign_yaml)
        return Campaign(
            name=name,
            recipe_id=recipe_id,
            branch=branch,
            commit_title=commit_title,
            commit_extended=commit_extended,
            pr_title=pr_title,
            pr_body=pr_body,
        )

    @classmethod
    def load_all(cls) -> List['Campaign']:
        campaign_globals = CampaignGlobals.load()
        return [cls._load(campaign_globals, campaign) for campaign in cls.list_campaigns()]

    @classmethod
    def list_campaigns(cls) -> List[str]:
        return [file.name for file in _campaigns_dir().iterdir() if file.is_dir()]

    @classmethod
    def _load_campaign_resource(cls, campaign: str, path: str) -> Traversable:
        resource = _campaigns_dir().joinpath(campaign).joinpath(path)
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
            return file.readline(), file.read().strip() + '\n'


@dataclass(frozen=True)
class CampaignGlobals:
    commit_footer: Template
    pr_message_footer_top: Template
    pr_message_footer: str
    pr_message_footer_bottom: Template

    def get_commit_footer(self, campaign_yaml: dict) -> str:
        return self.commit_footer.render(campaign_yaml)

    def get_pr_message_footer(self, campaign_yaml: dict) -> str:
        return self.pr_message_footer_top.render(campaign_yaml) + \
            self.pr_message_footer + \
            self.pr_message_footer_bottom.render(campaign_yaml)

    @classmethod
    def load(cls) -> 'CampaignGlobals':
        return cls(
            commit_footer=cls._load_file_contents_as_template("commit_footer.txt.liquid"),
            pr_message_footer_top=cls._load_file_contents_as_template("pr_message_footer_top.md.liquid"),
            pr_message_footer=cls._load_file_contents("pr_message_footer.md"),
            pr_message_footer_bottom=cls._load_file_contents_as_template("pr_message_footer_bottom.md.liquid"),
        )

    @classmethod
    def _load_file_contents_as_template(cls, path: str) -> Template:
        return Template(cls._load_file_contents(path))

    @classmethod
    def _load_file_contents(cls, path: str) -> str:
        resource = _campaigns_dir().joinpath(path)
        # noinspection PyTypeChecker
        with open(resource, 'r', encoding='utf-8') as file:  # pytype: disable=wrong-arg-types
            return file.read()


def _campaigns_dir() -> Traversable:
    return files('omega_moderne_client.campaign').joinpath('campaigns')
