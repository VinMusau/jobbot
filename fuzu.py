import httpx
from selectolax.parser import HTMLParser

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/1.0)"}

def fuzu():
    """Fuzu Kenya — HTML scrape, no API key needed."""
    url = "https://www.fuzu.com/kenya/jobs?query=software"
    r = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
    r.raise_for_status()
    tree = HTMLParser(r.text)
    out = []
    for card in tree.css("a[href*='/jobs/']"):
        title = card.text(strip=True)
        href = card.attributes.get("href", "")
        if not title or len(title) < 5 or "/jobs/" not in href:
            continue
        if not href.startswith("http"):
            href = "https://www.fuzu.com" + href
        out.append({
            "title": title,
            "company": "",
            "url": href,
            "location": "Kenya",
            "description": card.parent.text(separator=" ", strip=True) if card.parent else "",
            "source": "fuzu",
            "posted_at": None,
        })
    return out