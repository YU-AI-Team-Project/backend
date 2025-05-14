from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone

def start_scheduler(tickers, fetch_and_store_func, engine, logging):
    eastern = timezone("US/Eastern")
    scheduler = BackgroundScheduler(timezone=eastern)
    scheduler.add_job(lambda: [fetch_and_store_func(t, engine, logging) for t in tickers],
                      'cron', hour=9, minute=0)
    scheduler.start()
    logging.info("스케줄러 시작됨")