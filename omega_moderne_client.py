#!/usr/bin/env python
import argparse

from omega_moderne_client.campaign.campaign import Campaign
from omega_moderne_client.campaign.campaign_executor import CampaignExecutor
from omega_moderne_client.client.gpg_key_config import GpgKeyConfig
from omega_moderne_client.client.moderne_client import ModerneClient


def main():
    parser = argparse.ArgumentParser(
        description='Run a campaign to fix security vulnerabilities using Moderne.'
    )
    parser.add_argument(
        'campaign_id',
        type=str,
        choices=Campaign.list_campaigns(),
        help='The campaign to to run.'
    )
    parser.add_argument(
        '--moderne-organization',
        type=str,
        default='Default',
        help='The Moderne SaaS organization ID to run the campaign under. Defaults to `Default`.'
    )
    parser.add_argument(
        '--generate-prs',
        action='store_true',
        help='If set, the script will attempt to create pull requests.'
    )

    args = parser.parse_args()
    if args.generate_prs:
        print("Generate prs enabled. Pull requests will be created!")
    else:
        print("Generate prs not enabled. No pull requests will be created!")

    campaign = Campaign.load(args.campaign_id)
    client = ModerneClient.load_from_env()
    executor = CampaignExecutor(campaign, client)

    recipe_execution_result = executor.execute_recipe_and_await(
        target_organization_id=args.moderne_organization
    )

    if not args.generate_prs:
        print("Dry run enabled. Exiting without creating pull requests.")
        exit(0)

    gpg_key_config = GpgKeyConfig.load_from_env()
    executor.execute_pull_request_generation(gpg_key_config, recipe_execution_result)


if __name__ == "__main__":
    main()
