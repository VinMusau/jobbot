import httpx
from selectolax.parser import HTMLParser

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}

TAG_URLS = [
    "https://jobwebkenya.com/job-tag/software-developer/",
    "https://jobwebkenya.com/job-tag/software-engineer/",
    "https://jobwebkenya.com/job-tag/web-developer/",
    "https://jobwebkenya.com/job-tag/programming-2/",
    "https://jobwebkenya.com/job-tag/developer/",
]


def fetch_jobwebkenya():
    out = []
    seen = set()
    for tag_url in TAG_URLS:
        try:
            r = httpx.get(tag_url, headers=HEADERS, timeout=30, follow_redirects=True)
            if r.status_code != 200:
                print(f"  [jobwebkenya] {tag_url} -> {r.status_code}")
                continue
            tree = HTMLParser(r.text)
            for a in tree.css('a[href*="/jobs/"]'):
                href = a.attributes.get("href", "")
                title = a.text(strip=True)
                if not title or len(title) < 5:
                    continue
                if not href.startswith("http"):
                    href = "https://jobwebkenya.com" + href
                if href in seen:
                    continue
                seen.add(href)
                out.append({
                    "title": title,
                    "company": "",
                    "url": href,
                    "location": "Kenya",
                    "description": "",
                    "source": "jobwebkenya",
                    "posted_at": None,
                })
        except Exception as e:
            print(f"  [jobwebkenya] {tag_url} FAILED: {e}")
    return out