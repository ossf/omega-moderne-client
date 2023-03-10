#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
import argparse
import base64
import json
import os
import sys
from dataclasses import dataclass
from typing import Dict, Any, List

from isodate import parse_duration
from rich.align import Align
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.markup import escape
from rich.table import Table
from rich.text import Text
from rich_argparse import RichHelpFormatter

from omega_moderne_client.campaign.campaign import Campaign
from omega_moderne_client.campaign.campaign_executor import CampaignExecutor, PrintingCampaignExecutorProgressMonitor
from omega_moderne_client.client.gpg_key_config import GpgKeyConfig
from omega_moderne_client.client.moderne_client import ModerneClient, Repository, RecipeRunSummary
from omega_moderne_client.util import verbose_timedelta, headers

console = Console()
# Credit: https://patorjk.com/software/taag/#p=display&f=ANSI%20Shadow&t=Omega%20Moderne%0A%20%20%20%20%20%20%20Client
header: str
if console.width < 80 or "CI" in os.environ:
    header = headers.HEADER_NARROW
else:
    header = headers.HEADER_NORMAL
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
            if summary['totalChanged'] == 0 and summary['state'] == 'FINISHED':
                continue
            repository: Repository = summary['repository']
            organization = repository['path'].split('/')[0]
            repository_name = repository['path'].split('/')[1]
            repository_name_cell = repository_name
            if summary['totalChanged'] != 0:
                base64_repository_json = base64.b64encode(json.dumps(repository).encode('utf-8')).decode('utf-8')
                link = f"https://{self.domain}/results/{run_id}/details/{base64_repository_json}"
                repository_name_cell = f"[blue][link={link}]{repository_name}[/link]"
            table.add_row(
                self._color_state(summary['state']),
                organization,
                repository_name_cell,
                repository['branch'],
                str(summary['totalChanged']),
                str(summary['totalSearched']),
                verbose_timedelta(parse_duration(summary['performance']['recipeRun']))
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
        console.log(*(escape(arg) for arg in args))


def main():
    console.print(header, justify="center")
    parser = argparse.ArgumentParser(
        description='Run a campaign to fix security vulnerabilities using Moderne.',
        formatter_class=RichHelpFormatter
    )
    parent = argparse.ArgumentParser(add_help=False, formatter_class=RichHelpFormatter)
    parent.add_argument(
        '--moderne-domain',
        type=str,
        default='public.moderne.io',
        help='The Moderne SaaS domain to communicate with. Defaults to `public.moderne.io`.'
    )

    subparsers = parser.add_subparsers(title="actions")

    def add_recipe_args(subparser):
        subparser.add_argument(
            'campaign_id',
            type=str,
            choices=Campaign.list_campaigns(),
            help='The campaign to to run.'
        )
        subparser.add_argument(
            '--moderne-organization',
            type=str,
            default='Default',
            help='The Moderne SaaS organization ID to run the campaign under. Defaults to `Default`.'
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

    args = parser.parse_args()
    if not hasattr(args, 'func'):
        parser.print_help()
        sys.exit(1)

    with Live(layout, console=console, redirect_stderr=False, refresh_per_second=1):
        layout["header"].update(Align.center(Text(header, justify="center"), vertical="middle"))
        try:
            args.func(args)
        except KeyboardInterrupt:
            console.print("Interrupted by user. Exiting...")
            sys.exit(130)


def run_recipe_maybe_generate_prs(args):
    if args.generate_prs:
        console.print("Generate prs enabled. Pull requests will be created!")
    else:
        console.print("Generate prs not enabled. No pull requests will be created!")

    campaign = Campaign.load(args.campaign_id)
    client = ModerneClient.load_from_env(args.moderne_domain)
    executor = CampaignExecutor(client, ConsolePrintingCampaignExecutorProgressMonitor(client.domain))

    console.print(f"Running campaign {campaign.name}...")
    run_id = executor.launch_recipe(
        campaign=campaign,
        target_organization_id=args.moderne_organization
    )
    recipe_execution_result = executor.await_recipe(run_id=run_id)

    if not args.generate_prs:
        console.print("Generate prs not enabled. Complete!")
        sys.exit(0)

    gpg_key_config = GpgKeyConfig.load_from_env()
    console.print(f"Forking and creating pull requests for campaign {campaign.name}...")
    commit_id = executor.launch_pull_request(
        campaign,
        gpg_key_config,
        recipe_execution_result
    )
    executor.await_pull_request(commit_id=commit_id)


def recipe_attach(args):
    client = ModerneClient.load_from_env(args.moderne_domain)
    console.print(f"View live on Moderne https://{client.domain}/results/{args.run_id}")
    executor = CampaignExecutor(client, ConsolePrintingCampaignExecutorProgressMonitor(client.domain))
    executor.await_recipe(args.run_id)


def pr_attach(args):
    client = ModerneClient.load_from_env(args.moderne_domain)
    executor = CampaignExecutor(client, ConsolePrintingCampaignExecutorProgressMonitor(client.domain))
    executor.await_pull_request(args.commit_id)


if __name__ == "__main__":
    main()
