import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.scheduler_job import SchedulerJob
from app.services.notification_service import run_automated_escalation_scan
from app.services.document_validity_service import DocumentValidityService
from app.models.document_validity import DocumentValidityRecord, DocumentValidityStatus

logger = logging.getLogger(__name__)


def init_default_scheduler_jobs(db: Session):
    jobs = [
        ("DEADLINE_ESCALATION_MONITOR", "ESCALATION_CHECK", 60),
        ("DOCUMENT_EXPIRY_SCANNER", "EXPIRY_SCAN", 120),
        ("PROMISE_LEDGER_CLOCK_TICK", "CLOCK_EVALUATION", 60)
    ]
    for name, jtype, interval in jobs:
        existing = db.query(SchedulerJob).filter(SchedulerJob.job_name == name).first()
        if not existing:
            db.add(SchedulerJob(
                job_name=name,
                job_type=jtype,
                interval_seconds=interval,
                status="IDLE"
            ))
    db.commit()


def run_scheduled_job_cycle(db: Session):
    """
    Executes one cycle of automated regulatory background checks.
    """
    now = datetime.utcnow()

    # 1. Deadline & Escalation Scan
    job1 = db.query(SchedulerJob).filter(SchedulerJob.job_name == "DEADLINE_ESCALATION_MONITOR").first()
    if job1 and job1.is_enabled:
        job1.status = "RUNNING"
        job1.last_run = now
        try:
            res1 = run_automated_escalation_scan(db)
            job1.status = "SUCCESS"
            job1.last_result = f"Evaluated {res1.get('total_active_evaluated', 0)} obligations; escalated: {res1.get('escalated_count', 0)}, reminded: {res1.get('reminded_count', 0)}"
        except Exception as e:
            job1.status = "FAILED"
            job1.last_result = str(e)
            logger.error(f"Scheduler job {job1.job_name} failed: {e}")

    # 2. Document Expiry Scanner
    job2 = db.query(SchedulerJob).filter(SchedulerJob.job_name == "DOCUMENT_EXPIRY_SCANNER").first()
    if job2 and job2.is_enabled:
        job2.status = "RUNNING"
        job2.last_run = now
        try:
            records = db.query(DocumentValidityRecord).all()
            expiring_count = 0
            for r in records:
                days_rem = (r.expiry_date - now).days
                r.days_remaining = days_rem
                if days_rem <= 0:
                    r.status = DocumentValidityStatus.EXPIRED.value
                    expiring_count += 1
                elif days_rem <= 90 and r.status != DocumentValidityStatus.RENEWAL_SUBMITTED.value:
                    r.status = DocumentValidityStatus.EXPIRING_SOON.value
                    expiring_count += 1
            job2.status = "SUCCESS"
            job2.last_result = f"Scanned {len(records)} validity records; {expiring_count} requiring renewal."
        except Exception as e:
            job2.status = "FAILED"
            job2.last_result = str(e)

    db.commit()


async def background_scheduler_worker():
    """Persistent background task running cycles gracefully."""
    logger.info("ReguLens AI Regulatory Background Scheduler starting...")
    while True:
        try:
            db = SessionLocal()
            try:
                run_scheduled_job_cycle(db)
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Scheduler loop encountered error: {e}")
        await asyncio.sleep(60)
