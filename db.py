import os, hashlib
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]


def conn():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init():
    """No-op — schema is managed in Supabase Studio."""
    pass


def jid(url: str) -> str:
    return hashlib.sha256(url.strip().encode()).hexdigest()[:16]


def exists(jid_: str) -> bool:
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT 1 FROM jobs WHERE id = %s", (jid_,))
        return cur.fetchone() is not None


def insert(job: dict):
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """INSERT INTO jobs
               (id, title, company, url, location, description, source, posted_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            (job["id"], job["title"], job["company"], job["url"],
             job["location"], job["description"], job["source"], job.get("posted_at")),
        )


def set_score(jid_: str, score: int, reason: str):
    with conn() as c, c.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET score = %s, reason = %s WHERE id = %s",
            (score, reason, jid_),
        )


def pending(min_score: int):
    with conn() as c, c.cursor() as cur:
        cur.execute(
            """SELECT * FROM jobs
               WHERE emailed = FALSE AND dismissed = FALSE AND score >= %s
               ORDER BY score DESC, seen_at DESC""",
            (min_score,),
        )
        return cur.fetchall()


def mark_emailed(ids: list[str]):
    if not ids:
        return
    with conn() as c, c.cursor() as cur:
        cur.executemany(
            "UPDATE jobs SET emailed = TRUE WHERE id = %s",
            [(i,) for i in ids],
        )