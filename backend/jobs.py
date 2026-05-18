import os, sys, asyncio, logging
from datetime import date
from dotenv import load_dotenv
load_dotenv()
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/vynda-jobs.log", mode="a"),
    ],
)
log = logging.getLogger("vynda.jobs")
TIMEZONE = "America/Chicago"

def job_sync():
    log.info("Starting Axxess sync")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from sync import run_sync
        asyncio.run(run_sync())
        log.info("Axxess sync completed")
    except Exception as e:
        log.error(f"Axxess sync failed: {e}", exc_info=True)

def job_scheduler():
    today = date.today()
    log.info(f"Starting AI scheduler for {today}")
    try:
        from supabase import create_client
        sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
        existing = sb.table("schedules").select("id", count="exact").eq("visit_date", str(today)).execute()
        if existing.count and existing.count > 0:
            log.info(f"Schedule already exists for {today} — skipping")
            return
        from scheduler import run_scheduler, save_schedule_to_supabase, print_schedule
        result = run_scheduler(today)
        print_schedule(result)
        if result["scheduled"]:
            saved = save_schedule_to_supabase(result)
            log.info(f"Schedule generated: {saved} visits saved")
        else:
            log.info("No visits to schedule today")
    except Exception as e:
        log.error(f"Scheduler failed: {e}", exc_info=True)

def job_compliance(label="Morning"):
    log.info(f"Starting {label} compliance scan")
    try:
        from compliance import run_compliance_scan, print_compliance_report
        result = run_compliance_scan(write_to_db=True)
        print_compliance_report(result)
        log.info(f"Compliance scan complete: {result['total_alerts']} alerts")
    except Exception as e:
        log.error(f"Compliance scan failed: {e}", exc_info=True)

def job_compliance_morning(): job_compliance("Morning")
def job_compliance_evening(): job_compliance("Evening")

def main():
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(job_sync, CronTrigger(hour=6, minute=0, timezone=TIMEZONE), id="axxess_sync", max_instances=1, misfire_grace_time=300)
    scheduler.add_job(job_scheduler, CronTrigger(hour=6, minute=30, timezone=TIMEZONE), id="ai_scheduler", max_instances=1, misfire_grace_time=300)
    scheduler.add_job(job_compliance_morning, CronTrigger(hour=7, minute=0, timezone=TIMEZONE), id="compliance_morning", max_instances=1, misfire_grace_time=300)
    scheduler.add_job(job_compliance_evening, CronTrigger(hour=18, minute=0, timezone=TIMEZONE), id="compliance_evening", max_instances=1, misfire_grace_time=300)
    log.info("Vynda Job Scheduler started")
    log.info("06:00 AM — Axxess sync")
    log.info("06:30 AM — AI scheduler")
    log.info("07:00 AM — Morning compliance scan")
    log.info("06:00 PM — Evening compliance scan")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped")

if __name__ == "__main__":
    main()
