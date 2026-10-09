import os, io, json
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def extract_text(filename: str, content: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(p.extract_text() or "" for p in reader.pages).strip()
    if name.endswith((".docx", ".doc")):
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs).strip()
    if name.endswith((".txt", ".md")):
        return content.decode("utf-8", errors="replace").strip()
    raise ValueError("Unsupported file type — use PDF, DOCX, TXT, or MD")


SYSTEM = (
    "You evaluate a software engineering job posting against a candidate's CV. "
    "Be honest and specific. Respond with ONLY a JSON object, no prose."
)

PROMPT = """CV:
---
{cv}
---

Job:
Title: {title}
Company: {company}
Location: {location}
Description:
{description}

Evaluate fit. Return JSON:
{{
  "score": 0-10,
  "verdict": "strong" | "medium" | "weak",
  "matched": ["skill1", "skill2"],
  "missing": ["skill1", "skill2"],
  "summary": "one short paragraph, max 30 words"
}}

Score guide:
- 8-10: strong match, would likely get an interview
- 5-7: plausible stretch
- 0-4: poor fit or seniority mismatch
List at most 8 items in matched/missing.
"""


def score_cv_match(cv_text: str, job: dict) -> dict:
    prompt = PROMPT.format(
        cv=cv_text[:8000],
        title=job["title"],
        company=job.get("company") or "",
        location=job.get("location") or "",
        description=(job.get("description") or "")[:3000],
    )
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_tokens=1000,
        extra_body={"reasoning_effort": "low"},
    )
    data = json.loads(resp.choices[0].message.content)
    return {
        "score": int(data.get("score", 0)),
        "verdict": str(data.get("verdict", "weak"))[:20],
        "matched": data.get("matched", [])[:8],
        "missing": data.get("missing", [])[:8],
        "summary": str(data.get("summary", ""))[:300],
    }