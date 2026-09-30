import sqlite3, hashlib
from contextlib import contextmanager

DB = "jobs.db"

@contextmanager
def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()

def init():
    with conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            title TEXT, company TEXT, url TEXT, location TEXT,
            description TEXT, source TEXT, posted_at TEXT,
            score INTEGER, reason TEXT,
            emailed INTEGER DEFAULT 0,
            seen_at TEXT DEFAULT CURRENT_TIMESTAMP
        )""")
        c.execute("CREATE INDEX IF NOT EXISTS idx_score ON jobs(emailed, score)")

def jid(url: str) -> str:
    return hashlib.sha256(url.strip().encode()).hexdigest()[:16]

def exists(jid_: str) -> bool:
    with conn() as c:
        return c.execute("SELECT 1 FROM jobs WHERE id=?", (jid_,)).fetchone() is not None

def insert(job: dict):
    with conn() as c:
        c.execute("""INSERT OR IGNORE INTO jobs
            (id,title,company,url,location,description,source,posted_at)
            VALUES (?,?,?,?,?,?,?,?)""",
            (job["id"], job["title"], job["company"], job["url"],
             job["location"], job["description"], job["source"], job.get("posted_at")))

def set_score(jid_: str, score: int, reason: str):
    with conn() as c:
        c.execute("UPDATE jobs SET score=?, reason=? WHERE id=?", (score, reason, jid_))

def pending(min_score: int):
    with conn() as c:
        return c.execute(
            "SELECT * FROM jobs WHERE emailed=0 AND score>=? ORDER BY score DESC, seen_at DESC",
            (min_score,)).fetchall()

def mark_emailed(ids: list[str]):
    with conn() as c:
        c.executemany("UPDATE jobs SET emailed=1 WHERE id=?", [(i,) for i in ids])