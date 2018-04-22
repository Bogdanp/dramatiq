import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

import dramatiq


@dramatiq.actor
def print_current_date():
    print(datetime.now())


def main(args):
    scheduler = BlockingScheduler()
    scheduler.add_job(
        print_current_date.send,
        CronTrigger.from_crontab("* * * * *"),
    )
    try:
        scheduler.start()
    except KeyboardInterrupt:
        scheduler.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
