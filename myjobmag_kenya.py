def myjobmag():
    url = "https://www.myjobmag.co.ke/search/jobs?q=software"
    r = httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True)
    r.raise_for_status()
    tree = HTMLParser(r.text)
    out = []
    for a in tree.css("h2 a, .job-list-li a"):
        title = a.text(strip=True)
        href = a.attributes.get("href", "")
        if not title or len(title) < 5:
            continue
        if not href.startswith("http"):
            href = "https://www.myjobmag.co.ke" + href
        out.append({"title": title, "company": "", "url": href,
                    "location": "Kenya", "description": "",
                    "source": "myjobmag", "posted_at": None})
    return out