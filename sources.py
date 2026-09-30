import fuzu
import os, httpx
import jobwebkenya
import myjobmag_kenya
from selectolax.parser import HTMLParser

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0; +mailto:you@example.com)"}
TIMEOUT = 30

def _job(title, company, url, location, desc, source, posted=None):
    return {"title": (title or "").strip(), "company": (company or "").strip(),
            "url": url, "location": (location or "").strip(),
            "description": (desc or "")[:5000], "source": source, "posted_at": posted}

# ---------- REMOTE APIs ----------

def remotive():
    r = httpx.get("https://remotive.com/api/remote-jobs",
                  params={"category": "software-dev"}, timeout=TIMEOUT)
    r.raise_for_status()
    return [_job(j["title"], j["company_name"], j["url"],
                 j.get("candidate_required_location", "Remote"),
                 j.get("description", ""), "remotive", j.get("publication_date"))
            for j in r.json().get("jobs", [])]

def remoteok():
    r = httpx.get("https://remoteok.com/api", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if data and "legal" in str(data[0]).lower():
        data = data[1:]
    out = []
    for j in data:
        tags = [t.lower() for t in (j.get("tags") or [])]
        if not any(t in tags for t in ("dev", "engineer", "software", "backend",
                                       "frontend", "fullstack", "python", "javascript")):
            continue
        out.append(_job(j.get("position"), j.get("company"), j.get("url"),
                        j.get("location") or "Remote", j.get("description", ""),
                        "remoteok", j.get("date")))
    return out

def jobicy():
    r = httpx.get("https://jobicy.com/api/v2/remote-jobs",
                  params={"count": 50, "industry": "engineering"}, timeout=TIMEOUT)
    r.raise_for_status()
    return [_job(j["jobTitle"], j["companyName"], j["url"],
                 j.get("jobGeo", "Remote"), j.get("jobExcerpt", ""), "jobicy",
                 j.get("pubDate"))
            for j in r.json().get("jobs", [])]

# ---------- KENYA ----------

def adzuna_kenya():
    """Free tier: ~1000 calls/month. Register at developer.adzuna.com"""
    app_id, app_key = os.environ["ADZUNA_APP_ID"], os.environ["ADZUNA_APP_KEY"]
    out = []
    for what in ("software developer", "software engineer", "web developer"):
        r = httpx.get(f"https://api.adzuna.com/v1/api/jobs/ke/search/1",
                      params={"app_id": app_id, "app_key": app_key,
                              "results_per_page": 30, "what": what,
                              "content-type": "application/json"},
                      timeout=TIMEOUT)
        if r.status_code != 200:
            continue
        for j in r.json().get("results", []):
            out.append(_job(j.get("title"), (j.get("company") or {}).get("display_name"),
                            j.get("redirect_url"),
                            (j.get("location") or {}).get("display_name", "Kenya"),
                            j.get("description", ""), "adzuna-ke", j.get("created")))
    return out

def brightermonday():
    """HTML scrape. Selectors WILL break occasionally — check when count drops to 0."""
    url = "https://www.brightermonday.co.ke/jobs/software-data"
    r = httpx.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
    r.raise_for_status()
    tree = HTMLParser(r.text)
    out = []
    for a in tree.css("a[href*='/listings/']"):
        title = a.text(strip=True)
        href = a.attributes.get("href", "")
        if not title or "/listings/" not in href:
            continue
        if not href.startswith("http"):
            href = "https://www.brightermonday.co.ke" + href
        parent = a.parent
        text = parent.text(separator=" ", strip=True) if parent else ""
        out.append(_job(title, "", href, "Kenya", text, "brightermonday"))
    return out

ALL_SOURCES = [
        remotive, 
        remoteok, 
        jobicy, 
        adzuna_kenya, 
        brightermonday,
        jobwebkenya,
        fuzu,
        myjobmag_kenya,
    ]

def fetch_all():
    jobs = []
    for fn in ALL_SOURCES:
        try:
            got = fn()
            print(f"[{fn.__name__}] {len(got)} jobs")
            jobs.extend(got)
        except Exception as e:
            print(f"[{fn.__name__}] FAILED: {e}")
    return jobs