#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from typing import Generator

from omega_moderne_client.campaign.campaign import Campaign

from croniter import croniter
from datetime import datetime
import pytz


def cron_iterate(cron: croniter) -> Generator[datetime, None, None]:
    while True:
        yield cron.get_next(datetime)


def main():
    timezone = pytz.timezone('EST5EDT')
    today = datetime.now(timezone)
    campaigns = sorted(Campaign.load_all(), key=lambda c: c.name)

    base = datetime(2023, 1, 1, tzinfo=timezone)
    it = croniter('0 0 * * Mon,Wed,Thu,Fri', base)

    for i, t in enumerate(cron_iterate(it)):
        if t.month == today.month and t.day == today.day and t.year == today.year:
            print(campaigns[i % len(campaigns)].name)
            break
        if t > today:
            print('could not compute next campaign')
            sys.exit(1)


if __name__ == '__main__':
    main()
