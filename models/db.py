import pymysql
from flask import g, current_app

# ── CONNECTION ────────────────────────────────────────────
def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host="localhost",
            user="azureuser",
            password="pass123",   # 🔴 CHANGE THIS
            database="cloudbridge",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
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
        result = rows
    return result[0] if one and result else (None if one else result)


def execute(sql, params=(), get_id=False):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, params)
        db.commit()
        return cur.lastrowid if get_id else cur.rowcount


# ── INIT DB ───────────────────────────────────────────────
def init_db():
    # Tables already created in MariaDB → no need to recreate
    pass
