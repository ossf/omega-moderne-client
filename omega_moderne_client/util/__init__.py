"""Utilities for the Omega Moderne Client"""
from datetime import timedelta


def verbose_timedelta(delta: timedelta):
    """
    Inspiration: https://codereview.stackexchange.com/a/37287
    >>> verbose_timedelta(timedelta(days=1, seconds=1))
    '1 day 1s'
    >>> verbose_timedelta(timedelta(minutes=1, seconds=30))
    '1 min 30s'
    >>> verbose_timedelta(timedelta(minutes=1, seconds=30, milliseconds=500))
    '1 min 30.5s'
    >>> verbose_timedelta(timedelta())
    ''
    """
    # pylint: disable=invalid-name
    d = delta.days
    h, s = divmod(delta.seconds, 3600)
    m, s = divmod(s, 60)
    ms = delta.microseconds // 1000
    if ms != 0:
        s = round(s + ms / 1000, 2)
    labels = [' day', ' hr', ' min', 's']
    dhms = [f'{i}{lbl}{"s" if i != 1 and lbl != "s" else ""}' for i, lbl in zip([d, h, m, s], labels) if i != 0]
    if len(dhms) == 0:
        return ''
    # pylint: disable-next=consider-using-enumerate
    for start in range(len(dhms)):
        if not dhms[start].startswith('0'):
            break
    for end in range(len(dhms) - 1, -1, -1):
        if not dhms[end].startswith('0'):
            break
    return ' '.join(dhms[start:end + 1])
