"""
Decide whether the scheduled price update should run right now.

GitHub cron runs in UTC and has no idea about daylight saving time or market
holidays, so the workflow fires at both 5pm EDT and 5pm EST times. This
script keeps only the one that matches the current Eastern offset and skips
weekends and NYSE holidays. Manual runs always go through.

Prints "true" or "false".
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import holidays

EASTERN = ZoneInfo("America/Detroit")
CRON_FOR_DST = {True: "0 21 * * 1-5", False: "0 22 * * 1-5"}


def is_dst(moment: datetime) -> bool:
    return bool(moment.dst())


def should_run(event_name: str, schedule: str, now: datetime) -> bool:
    if event_name != "schedule":
        return True
    if schedule != CRON_FOR_DST[is_dst(now)]:
        return False
    if now.weekday() >= 5:
        return False
    return now.date() not in holidays.financial_holidays("NYSE", years=now.year)


def main() -> None:
    now = datetime.now(EASTERN)
    if len(sys.argv) > 1:  # optional ISO timestamp, for testing
        now = datetime.fromisoformat(sys.argv[1]).astimezone(EASTERN)
    result = should_run(os.environ.get("EVENT_NAME", ""), os.environ.get("SCHEDULE", ""), now)
    print("true" if result else "false")


if __name__ == "__main__":
    main()
