import os, secrets, json
from contextlib import contextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials

import db
import cv as cv_module

app = FastAPI(title="JobBot")
templates = Jinja2Templates(directory="templates")
security = HTTPBasic()


def auth(creds: HTTPBasicCredentials = Depends(security)):
    ok_user = secrets.compare_digest(creds.username, os.environ["APP_USER"])
    ok_pass = secrets.compare_digest(creds.password, os.environ["APP_PASSWORD"])
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return creds.username


@contextmanager
def cursor():
    with db.conn() as c, c.cursor() as cur:
        yield cur


def active_resume():
    with cursor() as cur:
        cur.execute("SELECT * FROM resumes WHERE is_active = TRUE LIMIT 1")
        return cur.fetchone()


# ---------- Jobs list ----------

@app.get("/", response_class=HTMLResponse)
def jobs_list(
    request: Request,
    source: str = "",
    min_score: int = 0,
    status: str = "all",
    q: str = "",
    user: str = Depends(auth),
):
    resume = active_resume()
    resume_id = resume["id"] if resume else None

    where = []
    params = []
    if status != "dismissed":
        where.append("j.dismissed = FALSE")
    else:
        where.append("j.dismissed = TRUE")

    if source:
        where.append("j.source = %s")
        params.append(source)
    if min_score:
        where.append("j.score >= %s")
        params.append(min_score)
    if q:
        where.append("(j.title ILIKE %s OR j.company ILIKE %s)")
        params.extend([f"%{q}%", f"%{q}%"])
    if status == "applied":
        where.append("EXISTS (SELECT 1 FROM applications a WHERE a.job_id = j.id)")
    elif status == "not_applied":
        where.append("NOT EXISTS (SELECT 1 FROM applications a WHERE a.job_id = j.id)")

    where_sql = " AND ".join(where) if where else "TRUE"

    sql = f"""
        SELECT j.*,
               (SELECT status FROM applications a
                WHERE a.job_id = j.id
                ORDER BY occurred_at DESC LIMIT 1) AS current_status,
               cm.score AS cv_score
        FROM jobs j
        LEFT JOIN cv_matches cm
          ON cm.job_id = j.id AND cm.resume_id = %s
        WHERE {where_sql}
        ORDER BY cm.score DESC NULLS LAST, j.score DESC, j.seen_at DESC
        LIMIT 200
    """
    with cursor() as cur:
        cur.execute(sql, [resume_id] + params)
        jobs = cur.fetchall()
        cur.execute("SELECT DISTINCT source FROM jobs ORDER BY source")
        sources = [r["source"] for r in cur.fetchall()]

    return templates.TemplateResponse(
        request=request,
        name="jobs.html",
        context={
            "jobs": jobs,
            "sources": sources,
            "filters": {"source": source, "min_score": min_score, "status": status, "q": q},
            "active_resume": resume,
        },
    )


# ---------- Job detail ----------

@app.get("/job/{job_id}", response_class=HTMLResponse)
def job_detail(request: Request, job_id: str, user: str = Depends(auth)):
    with cursor() as cur:
        cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
        job = cur.fetchone()
        if not job:
            raise HTTPException(404)

        cur.execute(
            "SELECT * FROM applications WHERE job_id = %s ORDER BY occurred_at DESC",
            (job_id,),
        )
        events = cur.fetchall()

    resume = active_resume()
    match = None
    if resume:
        with cursor() as cur:
            cur.execute(
                "SELECT * FROM cv_matches WHERE job_id = %s AND resume_id = %s",
                (job_id, resume["id"]),
            )
            match = cur.fetchone()

    return templates.TemplateResponse(
        request=request,
        name="job_detail.html",
        context={
            "job": job,
            "events": events,
            "match": match,
            "active_resume": resume,
        },
    )


@app.post("/job/{job_id}/score")
def score_job(job_id: str, user: str = Depends(auth)):
    resume = active_resume()
    if not resume:
        raise HTTPException(400, "Upload a CV first")

    with cursor() as cur:
        cur.execute("SELECT * FROM jobs WHERE id = %s", (job_id,))
        job = cur.fetchone()

    result = cv_module.score_cv_match(resume["raw_text"], job)

    with cursor() as cur:
        cur.execute(
            """INSERT INTO cv_matches
               (job_id, resume_id, score, verdict, matched, missing, summary)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (job_id, resume_id) DO UPDATE SET
                 score = EXCLUDED.score,
                 verdict = EXCLUDED.verdict,
                 matched = EXCLUDED.matched,
                 missing = EXCLUDED.missing,
                 summary = EXCLUDED.summary,
                 scored_at = NOW()""",
            (job_id, resume["id"], result["score"], result["verdict"],
             json.dumps(result["matched"]), json.dumps(result["missing"]),
             result["summary"]),
        )
    return RedirectResponse(f"/job/{job_id}", status_code=303)


# ---------- Actions ----------

@app.post("/job/{job_id}/status")
def update_status(
    job_id: str,
    status: str = Form(...),
    note: str = Form(""),
    user: str = Depends(auth),
):
    with cursor() as cur:
        cur.execute(
            "INSERT INTO applications (job_id, status, note) VALUES (%s, %s, %s)",
            (job_id, status, note or None),
        )
    return RedirectResponse(f"/job/{job_id}", status_code=303)


@app.post("/job/{job_id}/dismiss")
def dismiss_job(job_id: str, undo: str = Form(""), user: str = Depends(auth)):
    new_val = False if undo == "1" else True
    with cursor() as cur:
        cur.execute("UPDATE jobs SET dismissed = %s WHERE id = %s", (new_val, job_id))
    return RedirectResponse("/", status_code=303)


# ---------- Applications funnel ----------

@app.get("/applications", response_class=HTMLResponse)
def applications_view(request: Request, user: str = Depends(auth)):
    with cursor() as cur:
        cur.execute("""
            SELECT j.id, j.title, j.company, j.url, j.source,
                   (SELECT status FROM applications a
                    WHERE a.job_id = j.id
                    ORDER BY occurred_at DESC LIMIT 1) AS current_status,
                   (SELECT MIN(occurred_at) FROM applications a
                    WHERE a.job_id = j.id AND a.status = 'applied') AS applied_at,
                   (SELECT MAX(occurred_at) FROM applications a WHERE a.job_id = j.id) AS last_event_at
            FROM jobs j
            WHERE EXISTS (SELECT 1 FROM applications a WHERE a.job_id = j.id)
            ORDER BY last_event_at DESC
        """)
        rows = cur.fetchall()

        cur.execute("""
            SELECT
              COUNT(DISTINCT job_id) FILTER (WHERE status = 'applied') AS applied,
              COUNT(DISTINCT job_id) FILTER (WHERE status IN
                ('screening','interview_scheduled','interviewed','offer')) AS progressed,
              COUNT(DISTINCT job_id) FILTER (WHERE status IN
                ('interviewed','offer')) AS interviewed,
              COUNT(DISTINCT job_id) FILTER (WHERE status = 'offer') AS offers
            FROM applications
        """)
        stats = cur.fetchone()

    return templates.TemplateResponse(
        request=request,
        name="applications.html",
        context={
            "rows": rows,
            "stats": stats,
        },
    )


# ---------- Resume management ----------

@app.get("/resume", response_class=HTMLResponse)
def resume_page(request: Request, user: str = Depends(auth)):
    with cursor() as cur:
        cur.execute("SELECT id, name, is_active, uploaded_at FROM resumes ORDER BY uploaded_at DESC")
        resumes = cur.fetchall()
    return templates.TemplateResponse(
        request=request,
        name="resume.html",
        context={
            "resumes": resumes,
        },
    )


@app.post("/resume")
async def upload_resume(
    name: str = Form(...),
    file: UploadFile = File(...),
    user: str = Depends(auth),
):
    content = await file.read()
    text = cv_module.extract_text(file.filename, content)
    if len(text) < 100:
        raise HTTPException(400, "Couldn't extract text from that file. Try a plain text version.")

    with cursor() as cur:
        cur.execute("UPDATE resumes SET is_active = FALSE")
        cur.execute(
            "INSERT INTO resumes (name, raw_text, is_active) VALUES (%s, %s, TRUE)",
            (name, text),
        )
    return RedirectResponse("/resume", status_code=303)


@app.post("/resume/{resume_id}/activate")
def activate_resume(resume_id: int, user: str = Depends(auth)):
    with cursor() as cur:
        cur.execute("UPDATE resumes SET is_active = FALSE")
        cur.execute("UPDATE resumes SET is_active = TRUE WHERE id = %s", (resume_id,))
    return RedirectResponse("/resume", status_code=303)