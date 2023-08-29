import argparse
import asyncio
import base64
import json
import re
import sys
from dataclasses import dataclass
from typing import Dict, Any, List

try:
    from isodate import parse_duration
    from rich.align import Align
    from rich.console import Console, Group
    from rich.emoji import Emoji
    from rich.layout import Layout
    from rich.live import Live
    from rich.markup import escape
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.tree import Tree
    from rich_argparse import RichHelpFormatter
except ImportError as e:
    sys.stderr.write('It seems omega-moderne-client is not installed with cli option. \n'
                     'Run `pip install "omega-moderne-client[cli]"` to fix this.')
    sys.exit(1)

from omega_moderne_client.campaign.campaign import Campaign
from omega_moderne_client.campaign.campaign_executor import CampaignExecutor, PrintingCampaignExecutorProgressMonitor
from omega_moderne_client.client.gpg_key_config import GpgKeyConfig
from omega_moderne_client.client.moderne_client import ModerneClient
from omega_moderne_client.client.client_types import RecipeRunSummary, Repository, RepositoryInput
from omega_moderne_client.repository_filter import Filter, FilterDetailedReason, FilterReason, \
    FilteredRecipeExecutionResult
from omega_moderne_client.util import verbose_timedelta, headers

console = Console()
HEADER = headers.HEADER_NORMAL
layout = Layout()
layout.split(
    Layout(name='header', size=17),
    Layout(name='body', ratio=1),
)
layout["body"].split(Layout(name='top', size=6), Layout(name='bottom', ratio=1))


@dataclass(frozen=True)
class ConsolePrintingCampaignExecutorProgressMonitor(PrintingCampaignExecutorProgressMonitor):

    @staticmethod
    def _generate_recipe_overview_table(totals: Dict[str, Any]) -> Table:
        table = Table()
        table.add_column('Repositories Searched', justify='right')
        table.add_column('Repositories Changed', justify='right')
        table.add_column('Files Searched', justify='right')
        table.add_column('Files Changed', justify='right')
        table.add_column('Total Results', justify='right')
        table.add_column('Total Time Savings', justify='right')
        table.add_row(
            str(totals['totalRepositoriesWithErrors'] +
                totals['totalRepositoriesSuccessful'] +
                totals['totalRepositoriesWithNoChanges'] +
                totals['totalRepositoriesWithResults']),
            str(totals['totalRepositoriesWithResults']),
            str(totals['totalFilesSearched']),
            str(totals['totalFilesChanged']),
            str(totals['totalResults']),
            verbose_timedelta(parse_duration(totals['totalTimeSavings']))
        )
        return table

    def _generate_recipe_repositories_table(
            self,
            run_id: str,
            repository_run_summaries: List['RecipeRunSummary']
    ) -> Table:
        table = Table()
        table.add_column('Status')
        table.add_column('Organization')
        table.add_column('Repository')
        table.add_column('Branch')
        table.add_column('Total Results', justify='right')
        table.add_column('Files Searched', justify='right')
        table.add_column('Recipe Run', justify='right')

        for summary in repository_run_summaries:
            if summary.totalChanged == 0 and summary.state == 'FINISHED':
                continue
            repository: Repository = summary.repository
            organization = repository.path.split('/')[0]
            repository_name = repository.path.split('/')[1]
            repository_name_cell = repository_name
            if summary.totalChanged != 0:
                base64_repository_json = \
                    base64.b64encode(json.dumps(repository._asdict()).encode('utf-8')).decode('utf-8')
                link = f"https://{self.domain}/results/{run_id}/details/{base64_repository_json}"
                repository_name_cell = f"[blue][link={link}]{repository_name}[/link]"
            table.add_row(
                self._color_state(summary.state),
                organization,
                repository_name_cell,
                repository.branch,
                str(summary.totalChanged),
                str(summary.totalSearched),
                verbose_timedelta(parse_duration(summary.performance.recipeRun))
            )
        return table

    @staticmethod
    def _color_state(state: str) -> str:
        # ["CANCELED", "CREATED", "ERROR", "FINISHED", "LOADING", "QUEUED", "RUNNING", "UNAVAILABLE"]
        if state == 'FINISHED':
            return f'[green]{state}[/green]'
        if state == 'ERROR':
            return f'[red]{state}[/red]'
        if state in ['CREATED', 'QUEUED', 'RUNNING', 'LOADING']:
            return f'[yellow]{state}[/yellow]'
        if state in ['CANCELED', 'UNAVAILABLE']:
            return f'[grey]{state}[/grey]'
        return state

    def on_recipe_progress(
            self,
            run_id: str,
            state: str,
            totals: Dict[str, Any],
            repository_run_summaries: List['RecipeRunSummary']
    ) -> None:
        console.log(escape(f'[{run_id}] {state}'))
        layout["top"].update(Align.center(
            self._generate_recipe_overview_table(totals),
            vertical="middle"
        ))
        layout["bottom"].update(Align.center(
            self._generate_recipe_repositories_table(run_id, repository_run_summaries),
            vertical="top"
        ))

    def print(self, *args):
        console.log(*(escape(arg) if isinstance(arg, str) else arg for arg in args))


def print_recipe_filter_reason(filtered_repositories: Dict[Repository, List[FilterDetailedReason]]):
    if not filtered_repositories:
        return
    root = Tree("Filtered repositories", style="bold red")
    reverse_reason_map: Dict[FilterReason, Tree] = {}
    for repository, reasons in filtered_repositories.items():
        # console.print(f"Repository {repository} was filtered out because:")
        for reason in reasons:
            # console.print(f"  - {reason.reason}: {reason.details}")
            if reason.reason not in reverse_reason_map:
                reverse_reason_map[reason.reason] = root.add(reason.reason.name, style="bold red")
            reverse_reason_map[reason.reason].add(f"{repository} ({reason.details})")
    console.print(root)


async def create_pull_request_for_recipe_results(
        gpg_key_config: GpgKeyConfig,
        campaign: Campaign,
        executor: CampaignExecutor,
        filtered_recipe_execution_result: FilteredRecipeExecutionResult
):
    if not isinstance(gpg_key_config, GpgKeyConfig):
        raise ValueError("GPG key config must be provided to create pull requests")
    console.print(f"Forking and creating pull requests for campaign {campaign.name}...")
    commit_id = await executor.launch_pull_request(
        campaign,
        gpg_key_config,
        filtered_recipe_execution_result
    )
    await executor.await_pull_request(commit_id=commit_id)


async def run_recipe_maybe_generate_prs(args):
    if args.generate_prs:
        gpg_key_config = GpgKeyConfig.load_from_env()
        console.print("Generate prs enabled. Pull requests will be created!")
    else:
        console.print("Generate prs not enabled. No pull requests will be created!")
        gpg_key_config = None

    campaign = Campaign.load(args.campaign_id)
    async with ModerneClient.load_from_env(args.moderne_domain) as client:
        executor = CampaignExecutor(client, ConsolePrintingCampaignExecutorProgressMonitor(client.domain))

        console.print(f"Running campaign {campaign.name}...")
        if args.repository_filter:
            run_id = await executor.launch_recipe_against_repositories(
                campaign=campaign,
                repository_filter=args.repository_filter
            )
        else:
            run_id = await executor.launch_recipe_against_organization_id(
                campaign=campaign,
                target_organization_id=args.moderne_organization
            )
        recipe_execution_result = await executor.await_recipe(run_id=run_id)

        repository_filter = Filter.create_all()
        filtered_recipe_execution_result = repository_filter.filter_repositories(recipe_execution_result)
        print_recipe_filter_reason(filtered_recipe_execution_result.filtered_repositories)

        if not args.generate_prs:
            console.print("Generate prs not enabled. Complete!")
            sys.exit(0)

        await create_pull_request_for_recipe_results(
            gpg_key_config,
            campaign,
            executor,
            filtered_recipe_execution_result
        )


async def recipe_attach(args):
    if args.generate_prs:
        gpg_key_config = GpgKeyConfig.load_from_env()
    else:
        gpg_key_config = None

    async with ModerneClient.load_from_env(args.moderne_domain) as client:
        console.print(f"View live on Moderne https://{client.domain}/results/{args.run_id}")
        executor = CampaignExecutor(client, ConsolePrintingCampaignExecutorProgressMonitor(client.domain))
        recipe_execution_result = await executor.await_recipe(args.run_id)
        # Display the filtered repositories
        repository_filter = Filter.create_all()
        filtered_recipe_execution_result = repository_filter.filter_repositories(recipe_execution_result)
        print_recipe_filter_reason(filtered_recipe_execution_result.filtered_repositories)

        if not args.generate_prs:
            console.print("Generate prs not enabled. Complete!")
            sys.exit(0)

        # TODO: Load campaign from recipe execution result instead of args
        campaign = Campaign.load(args.campaign_id)
        await create_pull_request_for_recipe_results(
            gpg_key_config,
            campaign,
            executor,
            filtered_recipe_execution_result
        )


async def pr_attach(args):
    async with ModerneClient.load_from_env(args.moderne_domain) as client:
        executor = CampaignExecutor(client, ConsolePrintingCampaignExecutorProgressMonitor(client.domain))
        await executor.await_pull_request(args.commit_id)


async def print_campaign(args):
    def bright_white(string: str) -> str:
        return f"[bright_white]{string}[/bright_white]"

    def orange(string: str) -> str:
        return f"[orange3]{string}[/orange3]"

    def green(string: str) -> str:
        return f"[green]{string}[/green]"

    def bright_magenta(string: str) -> str:
        return f"[bright_magenta]{string}[/bright_magenta]"

    def bold(string: str) -> str:
        return f"[bold]{string}[/bold]"

    campaign = Campaign.load(args.campaign_id)
    root = Tree(
        f"{bright_magenta(bold('Campaign('))}name={bright_white(campaign.name)}{bright_magenta(bold(')'))}"
    )
    root.add(f"{orange('Recipe Id:')} {green(campaign.recipe_id)}")
    root.add(f"{orange('Branch:')} {green(campaign.branch)}")
    root.add(Group(
        orange("Commit Message:"),
        Panel(campaign.commit_title + '\n' + campaign.commit_extended, border_style="green")
    ))
    root.add(Group(
        orange("Pull Request Body:"),
        Panel(Markdown(Emoji.replace('# ' + campaign.pr_title + '\n' + campaign.pr_body)), border_style="green")
    ))
    console.print(root)


def cli():
    console.print(HEADER, justify="center")
    parser = argparse.ArgumentParser(
        description='Run a campaign to fix security vulnerabilities using Moderne.',
        formatter_class=RichHelpFormatter
    )
    parent = argparse.ArgumentParser(add_help=False, formatter_class=RichHelpFormatter)
    parent.add_argument(
        '--moderne-domain',
        type=str,
        default='app.moderne.io',
        help='The Moderne SaaS domain to communicate with. Defaults to `app.moderne.io`.'
    )

    subparsers = parser.add_subparsers(title="actions")

    pattern = re.compile(r'^(?P<origin>[^/]+)/(?P<owner>[^/]+)/(?P<repo>[^@]+)(@(?P<branch>.+))?$')

    def create_repository_input(arg_value) -> RepositoryInput:
        match = pattern.match(arg_value)
        if not match:
            raise argparse.ArgumentTypeError(
                f"Invalid Repository Filter {arg_value}."
                " Must be of format `origin/owner/repo[@branch]`"
            )
        return RepositoryInput(
            origin=match.group('origin'),
            path=match.group('owner') + '/' + match.group('repo'),
            branch=match.group('branch') or 'main'
        )

    def add_campaign_id_argument(subparser):
        subparser.add_argument(
            'campaign_id',
            type=str,
            choices=Campaign.list_campaigns(),
            help='The campaign to to run.'
        )

    def add_recipe_args(subparser):
        add_campaign_id_argument(subparser)
        group = subparser.add_mutually_exclusive_group()
        group.add_argument(
            '--moderne-organization',
            type=str,
            default='Default',
            help='The Moderne SaaS organization ID to run the campaign under. Defaults to `Default`.'
        )
        group.add_argument(
            '--repository-filter',
            type=create_repository_input,
            action='append',
            help='Filter repositories to run the campaign against. ' +
                 escape('Must be of format `origin/owner/repo[@branch]`. ') +
                 'For example: `github.com/openrewrite/rewrite`. '
                 'If a branch is not specified, `main` is used. '
                 'Can be specified multiple times.'
        )
        subparser.set_defaults(func=run_recipe_maybe_generate_prs)

    run_recipe_parser = subparsers.add_parser(
        'run-recipe',
        help='Run a recipe without creating pull requests.',
        formatter_class=RichHelpFormatter,
        parents=[parent],
    )
    run_recipe_parser.set_defaults(generate_prs=False)
    run_prs_parser = subparsers.add_parser(
        'run-pull-requests',
        help='Run a recipe and create pull requests.',
        formatter_class=RichHelpFormatter,
        parents=[parent],
    )
    run_prs_parser.set_defaults(generate_prs=True)
    add_recipe_args(run_recipe_parser)
    add_recipe_args(run_prs_parser)

    recipe_attach_parser = subparsers.add_parser(
        'recipe-attach',
        help='Attach to a running recipe execution.',
        formatter_class=RichHelpFormatter,
        parents=[parent],
    )
    recipe_attach_parser.add_argument(
        'run_id',
        type=str,
        help='The Moderne recipe execution id run to attach to.'
    )
    recipe_attach_parser.set_defaults(func=recipe_attach)

    recipe_attach_and_pull_request_parser = subparsers.add_parser(
        'recipe-attach-and-run-pull-request',
        help='Attach to a running recipe execution, then generate pull requests from it.',
        formatter_class=RichHelpFormatter,
        parents=[parent],
    )
    add_campaign_id_argument(recipe_attach_and_pull_request_parser)
    recipe_attach_and_pull_request_parser.add_argument(
        'run_id',
        type=str,
        help='The Moderne recipe execution id run to attach to.'
    )
    recipe_attach_and_pull_request_parser.set_defaults(generate_prs=True)
    recipe_attach_and_pull_request_parser.set_defaults(func=recipe_attach)

    pr_attach_parser = subparsers.add_parser(
        'pr-attach',
        help='Attach to a running pull request execution.',
        formatter_class=RichHelpFormatter,
        parents=[parent],
    )
    pr_attach_parser.add_argument(
        'commit_id',
        type=str,
        help='The Moderne commit id to attach to.'
    )
    pr_attach_parser.set_defaults(func=pr_attach)

    campaign_printer_parser = subparsers.add_parser(
        'campaign',
        help='Print data about a campaign.',
        formatter_class=RichHelpFormatter,
        parents=[parent],
    )
    campaign_printer_parser.add_argument(
        'campaign_id',
        type=str,
        choices=Campaign.list_campaigns(),
        help='The campaign to to print.'
    )
    campaign_printer_parser.set_defaults(func=print_campaign)
    campaign_printer_parser.set_defaults(not_live=True)

    args = parser.parse_args()
    if not hasattr(args, 'func'):
        parser.print_help()
        sys.exit(1)

    try:
        if hasattr(args, 'not_live') and args.not_live:
            asyncio.run(args.func(args))
        else:
            with Live(layout, console=console, redirect_stderr=False, refresh_per_second=1):
                layout["header"].update(Align.center(Text(HEADER, justify="center"), vertical="middle"))
                asyncio.run(args.func(args))
    except KeyboardInterrupt:
        console.print("Interrupted by user. Exiting...")
        sys.exit(130)
