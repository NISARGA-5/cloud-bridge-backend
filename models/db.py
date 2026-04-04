import pymysql
from flask import g

# ── CONNECTION ────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host="10.142.240.2",              # ✅ Cloud SQL private IP
            user="appuser",                   # ✅ your GCP DB user
            password="Strongpassword-1",      # ✅ SAME as Cloud SQL
            database="cloudbridge",           # ✅ your DB name
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True                  # ✅ IMPORTANT
        )
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db:
        db.close()


# ── QUERY HELPERS ─────────────────────────────────────────
def query(sql, params=(), one=False):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return rows[0] if one and rows else (None if one else rows)


def execute(sql, params=(), get_id=False):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid if get_id else cur.rowcount


# ── INIT DB ───────────────────────────────────────────────
def init_db():
    # Tables already exist → no action needed
    pass
