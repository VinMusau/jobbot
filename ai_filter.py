import os, json, re
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])

# ---- Stage 1: keyword pre-filter (free) ----
SOFTWARE_HINTS = re.compile(
    r"\b(software|developer|engineer|programmer|full[- ]?stack|back[- ]?end|"
    r"front[- ]?end|web dev|mobile dev|android|ios|flutter|react|node|python|"
    r"django|java\b|golang|devops|qa engineer|sdet|data engineer)\b", re.I)

SENIOR_BLOCK = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|head of|director|vp|manager|"
    r"architect|10\+ years|8\+ years|7\+ years)\b", re.I)

def prefilter(job: dict) -> bool:
    blob = f"{job['title']} {job['description'][:1500]}"
    if not SOFTWARE_HINTS.search(job["title"]):
        return False
    if SENIOR_BLOCK.search(job["title"]):
        return False
    return True

# ---- Stage 2: LLM scoring (batched) ----
SYSTEM = (
    "You classify job listings for a junior/mid software engineer based in Kenya. "
    "They want: entry or mid level software development/engineering roles, full-time "
    "or hybrid, located in Kenya OR fully remote and open to candidates in Africa/worldwide. "
    "Respond with ONLY a JSON object, no prose."
)

PROMPT_TMPL = """Score each listing 0-10 for how well it matches the candidate.

Criteria (all must hold for a high score):
- Role is software development/engineering (backend, frontend, fullstack, mobile, devops, data eng, QA automation)
- Level is entry (0-2 yrs) or mid (2-5 yrs) — NOT senior/staff/principal/lead/manager
- Full-time or hybrid (not contract/internship/part-time)
- Located in Kenya, OR fully remote and open to Africa/Kenya/worldwide

Listings:
{listings}

Return JSON exactly like:
{{"results":[{{"i":0,"score":8,"level":"mid","location_ok":true,"reason":"Remote fullstack, 3 yrs exp, open worldwide"}}]}}
Score 0 for anything that fails a hard criterion. Keep reason under 15 words.
"""

def _blob(jobs, start=0):
    return "\n\n".join(
        f"[{start+i}] Title: {j['title']}\nCompany: {j['company']}\n"
        f"Location: {j['location']}\nSource: {j['source']}\n"
        f"Description: {j['description'][:1200]}"
        for i, j in enumerate(jobs)
    )

def score_batch(jobs: list[dict], batch_size=8) -> list[tuple[int, str]]:
    """Returns list of (score, reason) aligned with `jobs`."""
    out = [(0, "unscored")] * len(jobs)
    for start in range(0, len(jobs), batch_size):
        chunk = jobs[start:start + batch_size]
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": PROMPT_TMPL.format(listings=_blob(chunk, start))},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1200,
            )
            data = json.loads(resp.choices[0].message.content)
            for r in data.get("results", []):
                idx = int(r["i"]) - start
                if 0 <= idx < len(chunk):
                    out[start + idx] = (int(r.get("score", 0)), str(r.get("reason", ""))[:200])
        except Exception as e:
            print(f"[ai] batch {start} failed: {e}")
    return out