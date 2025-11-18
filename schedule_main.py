from datetime import datetime, timedelta
from croniter import croniter
from utils.consts import program
from config import cron_expression
from main import main
from loguru import logger
import time

def get_next_runtime(cron_expression, base_time=None):
    base_time = base_time or datetime.now()
    cron = croniter(cron_expression, base_time)
    return cron.get_next(datetime)


def run_scheduled_tasks(cron_expression):
    logger.info(f"{program}运行中")
    main()
    next_run = get_next_runtime(cron_expression)
    logger.info(f"下次更新任务时间为{next_run}")
    while True:
        now = datetime.now()
        if now >= next_run:
            main()
            next_run = get_next_runtime(cron_expression, now + timedelta(seconds=1))
            logger.info(f"下次更新任务时间为{next_run}")
        time.sleep(1)


if __name__ == "__main__":
    run_scheduled_tasks(cron_expression)
