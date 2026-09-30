import os
from dotenv import load_dotenv
load_dotenv()

import db, sources, ai_filter, emailer

def run():
    db.init()

    raw = sources.fetch_all()
    print(f"Fetched {len(raw)} raw listings")

    fresh = []
    for j in raw:
        if not j["url"] or not j["title"]:
            continue
        j["id"] = db.jid(j["url"])
        if db.exists(j["id"]):
            continue
        db.insert(j)
        fresh.append(j)

    print(f"{len(fresh)} new (after dedupe)")
    if not fresh:
        return

    candidates = [j for j in fresh if ai_filter.prefilter(j)]
    print(f"{len(candidates)} passed keyword pre-filter")

    scores = ai_filter.score_batch(candidates)
    for j, (score, reason) in zip(candidates, scores):
        db.set_score(j["id"], score, reason)
    # keyword-rejected jobs stay at score 0 / NULL and are never emailed

    min_score = int(os.environ.get("MIN_SCORE", "7"))
    to_send = db.pending(min_score)
    print(f"{len(to_send)} jobs above score {min_score}")

    if not to_send:
        return

    subject = f"Job digest — {len(to_send)} new match{'es' if len(to_send)!=1 else ''}"
    emailer.send(
        subject,
        emailer.render_html(to_send),
        emailer.render_text(to_send),
    )
    db.mark_emailed([j["id"] for j in to_send])

if __name__ == "__main__":
    run()