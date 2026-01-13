# src/ingest/run.py

import argparse
import uuid
from datetime import datetime, timezone
from psycopg2.extras import Json

from .db import get_conn
from .jobs.prices_daily import run as run_prices_daily
from .jobs.adjustment_factors import run as run_adjustment_factors

from .util import get_git_commit, get_host_name, get_user_name
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

JOB_REGISTRY = {
    "prices_daily": run_prices_daily,
    "adjustment_factors": run_adjustment_factors,
}


def start_run(conn, notes=None):
    run_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion.ingestion_run (
                run_id,
                status,
                git_commit,
                invoked_by,
                host_name,
                notes
            )
            VALUES (%s, 'running', %s, %s, %s, %s)
            """,
            (
                run_id,
                get_git_commit(),
                get_user_name(),
                get_host_name(),
                notes,
            ),
        )

    conn.commit()
    return run_id


def finish_run(conn, run_id, status):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ingestion.ingestion_run
            SET status = %s,
                finished_at = now()
            WHERE run_id = %s
            """,
            (status, run_id),
        )
    conn.commit()


def start_job(conn, run_id, job_name, params):
    job_id = str(uuid.uuid4())

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ingestion.ingestion_job (
                job_id,
                run_id,
                job_name,
                params_json,
                status
            )
            VALUES (%s, %s, %s, %s, 'running')
            """,
            (job_id, run_id, job_name, Json(params)),
        )

    conn.commit()
    return job_id


def finish_job(
    conn,
    job_id,
    status,
    rows_upserted=0,
    rows_deleted=0,
    api_calls=0,
    error_count=0,
    last_checkpoint=None,
    error_message=None,
):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE ingestion.ingestion_job
            SET status = %s,
                finished_at = now(),
                rows_upserted = %s,
                rows_deleted = %s,
                api_calls = %s,
                error_count = %s,
                last_checkpoint = %s,
                error_message = %s
            WHERE job_id = %s
            """,
            (
                status,
                rows_upserted,
                rows_deleted,
                api_calls,
                error_count,
                last_checkpoint,
                error_message,
                job_id,
            ),
        )
    conn.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True)
    parser.add_argument("--notes")
    args = parser.parse_args()

    conn = get_conn()

    run_id = start_run(conn, notes=args.notes)

    overall_status = "success"

    job_id = None
    try:
        job_id = start_job(
            conn,
            run_id,
            job_name=args.job,
            params={"invoked_at": datetime.now(timezone.utc).isoformat()},
        )

        job_fn = JOB_REGISTRY[args.job]
        result = job_fn(conn, job_id)

        finish_job(
            conn,
            job_id,
            status="success",
            rows_upserted=result.get("rows_upserted", 0),
            api_calls=result.get("api_calls", 0),
        )

    except Exception as e:
        overall_status = "failed"
        if job_id is not None:
            finish_job(
                conn,
                job_id,
                status="failed",
                error_count=1,
                error_message=str(e),
            )
        else:
            raise

    finally:
        finish_run(conn, run_id, status=overall_status)
        conn.close()


if __name__ == "__main__":
    main()
