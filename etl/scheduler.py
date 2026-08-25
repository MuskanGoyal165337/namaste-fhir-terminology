import time
import logging
import threading
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from etl.who_sync import WHOICDClient
from etl.namaste_ingestor import NamasteIngestor
from db.session import SessionLocal
from db.models import CodeSystemVersion

logger = logging.getLogger("ayush_emr.etl.scheduler")

class WHOSyncScheduler:
    """
    Scheduler for automated nightly WHO ICD-11 synchronization and manual trigger execution.
    """

    def __init__(self, who_client: Optional[WHOICDClient] = None, interval_seconds: int = 86400):
        self.who_client = who_client or WHOICDClient()
        self.interval_seconds = interval_seconds
        self._timer: Optional[threading.Timer] = None
        self._running = False

    def run_sync_job(self, since_version: str = "2024-01", db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Executes manual or scheduled WHO ICD-11 sync job.
        Fetches delta updates, records version metadata in database, and returns summary stats.
        """
        logger.info(f"Starting WHO ICD-11 synchronization job (since_version={since_version})...")
        should_close = False
        if db is None:
            from db.session import init_db
            init_db()
            db = SessionLocal()
            should_close = True

        try:
            # Fetch catalog or delta updates from WHO provider
            sync_data = self.who_client.fetch_delta_sync(since_version)
            current_version = sync_data.get("current_version", "2024-01")
            updated_concepts = sync_data.get("updated_concepts", [])

            # Update database CodeSystemVersion tracking
            version_rec = db.query(CodeSystemVersion).filter(
                CodeSystemVersion.system_uri == "http://id.who.int/icd/release/11/mms",
                CodeSystemVersion.version == current_version
            ).first()

            if not version_rec:
                version_rec = CodeSystemVersion(
                    system_uri="http://id.who.int/icd/release/11/mms",
                    name="WHO ICD-11 Traditional Medicine Module 2",
                    version=current_version,
                    release_date=datetime.now(timezone.utc).date(),
                    concept_count=len(updated_concepts),
                    is_active=True
                )
                db.add(version_rec)
            else:
                version_rec.concept_count = max(version_rec.concept_count, len(updated_concepts))
                version_rec.updated_at = datetime.now(timezone.utc)

            db.commit()

            logger.info(f"WHO ICD-11 sync completed successfully. Version: {current_version}, Concepts: {len(updated_concepts)}")
            return {
                "status": "success",
                "current_version": current_version,
                "concepts_synced": len(updated_concepts),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            if should_close and db:
                db.rollback()
            logger.error(f"Error during WHO ICD-11 sync job: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        finally:
            if should_close and db:
                db.close()

    def _schedule_next_run(self):
        if not self._running:
            return
        self.run_sync_job()
        self._timer = threading.Timer(self.interval_seconds, self._schedule_next_run)
        self._timer.daemon = True
        self._timer.start()

    def start(self):
        """Starts background periodic scheduler."""
        if self._running:
            return
        self._running = True
        logger.info(f"Starting WHO sync scheduler (interval={self.interval_seconds}s)")
        self._timer = threading.Timer(self.interval_seconds, self._schedule_next_run)
        self._timer.daemon = True
        self._timer.start()

    def stop(self):
        """Stops background periodic scheduler."""
        self._running = False
        if self._timer:
            self._timer.cancel()
        logger.info("Stopped WHO sync scheduler.")

def execute_manual_sync() -> Dict[str, Any]:
    """Helper function to execute manual WHO sync on demand."""
    scheduler = WHOSyncScheduler()
    return scheduler.run_sync_job()
