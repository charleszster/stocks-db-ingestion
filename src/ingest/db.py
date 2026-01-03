# src/ingest/db.py

import psycopg2
import os


def get_conn():
    return psycopg2.connect(
        host=os.environ["PGHOST"],
        port=os.environ.get("PGPORT", 5432),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
    )
