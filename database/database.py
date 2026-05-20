from flask import g
import sqlite3
import os

DATABASE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "app.db")

def get_db() -> sqlite3.Connection:
    if not "db" in g:
        g.db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(_=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()