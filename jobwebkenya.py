import httpx
from selectolax.parser import HTMLParser

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}

def fetch_jobwebkenya():
    url = "https://www.jobwebkenya.com/category/software-development-jobs"
    r = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
    r.raise_for_status()
    tree = HTMLParser(r.text)
    out = []
    for a in tree.css("h2 a, h3 a"):
        title = a.text(strip=True)
        href = a.attributes.get("href", "")
        if not title or "jobwebkenya.com" not in href:
            continue
        out.append({
            "title": title, "company": "", "url": href,
            "location": "Kenya", "description": "",
            "source": "jobwebkenya", "posted_at": None,
        })
    return out