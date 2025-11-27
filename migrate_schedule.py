#!/usr/bin/env python3
"""
One-time migration/backfill for provider/student schedules
- Ensures the new `schedule` table exists (created by app.create_all)
- Copies rows from legacy table `scholarship_application_schedules` if it exists
- Derives provider_id and user_id for each schedule
- Skips duplicates when a matching schedule already exists

Usage:
  python migrate_schedule.py [--drop-legacy]
"""

from datetime import datetime, date
from typing import Optional
import argparse

from sqlalchemy import inspect, text

# Import app context, db and models from the main app
from app import app, db, Schedule


def parse_date(d: Optional[str]) -> Optional[date]:
    if not d:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(d[:10], fmt).date()
        except Exception:
            continue
    return None


def parse_datetime(ts: Optional[str]) -> datetime:
    if not ts:
        return datetime.utcnow()
    try:
        # ISO 8601 or SQLite stored string
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        pass
    # Try common formats
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except Exception:
            continue
    return datetime.utcnow()


def backfill_from_legacy(drop_legacy: bool = False):
    insp = inspect(db.engine)

    # Ensure new tables exist
    with app.app_context():
        db.create_all()

    has_legacy = insp.has_table("scholarship_application_schedules")
    if not has_legacy:
        print("No legacy table found. Nothing to migrate.")
        return

    # Fetch legacy rows
    legacy_rows = db.session.execute(
        text(
            """
            SELECT id, application_id, schedule_date, schedule_time, location, notes, created_at, created_by
            FROM scholarship_application_schedules
            ORDER BY id ASC
            """
        )
    ).fetchall()

    if not legacy_rows:
        print("Legacy table is empty. Nothing to migrate.")
        if drop_legacy:
            print("Dropping empty legacy table scholarship_application_schedules ...")
            db.session.execute(text("DROP TABLE IF EXISTS scholarship_application_schedules"))
            db.session.commit()
            print("Legacy table dropped.")
        return

    migrated = 0
    skipped = 0

    for row in legacy_rows:
        _, application_id, sdate, stime, location, notes, created_at, created_by = row

        # Determine student user_id and provider_id
        app_info = db.session.execute(
            text(
                """
                SELECT sa.user_id, s.provider_id
                FROM scholarship_applications sa
                JOIN scholarships s ON sa.scholarship_id = s.id
                WHERE sa.id = :aid
                """
            ),
            {"aid": application_id},
        ).fetchone()
        if not app_info:
            skipped += 1
            continue
        user_id, provider_id_from_join = app_info
        provider_id = created_by or provider_id_from_join

        created_dt = parse_datetime(created_at)
        sched_date = parse_date(sdate)
        sched_time = (stime or "").strip()
        location = (location or "").strip()
        notes = (notes or "").strip()

        # Check for existing matching schedule to avoid duplicates
        existing = db.session.execute(
            text(
                """
                SELECT id FROM schedule
                WHERE application_id = :aid
                  AND COALESCE(schedule_time,'') = :stime
                  AND COALESCE(location,'') = :loc
                  AND COALESCE(notes,'') = :notes
                  AND created_at = :cat
                LIMIT 1
                """
            ),
            {
                "aid": application_id,
                "stime": sched_time,
                "loc": location,
                "notes": notes,
                "cat": created_dt,
            },
        ).fetchone()
        if existing:
            skipped += 1
            continue

        # Insert via ORM
        new_sched = Schedule(
            application_id=application_id,
            provider_id=provider_id,
            user_id=user_id,
            schedule_date=sched_date,
            schedule_time=sched_time,
            location=location,
            notes=notes,
            created_at=created_dt,
        )
        db.session.add(new_sched)
        migrated += 1

        if migrated % 100 == 0:
            db.session.commit()
            print(f"Committed {migrated} migrated schedules so far...")

    db.session.commit()
    print(f"Done. Migrated: {migrated}, Skipped (duplicates or missing refs): {skipped}")

    if drop_legacy:
        print("Dropping legacy table scholarship_application_schedules ...")
        db.session.execute(text("DROP TABLE IF EXISTS scholarship_application_schedules"))
        db.session.commit()
        print("Legacy table dropped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate legacy schedules to new schedule table")
    parser.add_argument("--drop-legacy", action="store_true", help="Drop the legacy scholarship_application_schedules table after migration")
    args = parser.parse_args()

    with app.app_context():
        backfill_from_legacy(drop_legacy=args.drop_legacy)
