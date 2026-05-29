"""Score and export notable accounts from scraped posts."""

import json
import sqlite3
from collections import defaultdict
from typing import Optional
from atproto import Client as AtprotoClient

from db import get_conn


def compute_accounts() -> list[dict]:
    """
    Aggregate posts by author DIDs, score them,
    and return a list of account dicts sorted by relevance_score desc.
    """
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            p.author_did,
            p.author_handle,
            a.display_name,
            a.description,
            a.follower_count,
            COUNT(p.uri)                         AS post_count,
            SUM(p.likes)                         AS total_likes,
            SUM(p.replies)                       AS total_replies,
            SUM(p.reposts)                       AS total_reposts,
 GROUP_CONCAT(DISTINCT p.tags) AS top_tags,
            GROUP_CONCAT(DISTINCT p.keyword) AS keywords
        FROM posts p
        LEFT JOIN accounts a ON p.author_did = a.did
        GROUP BY p.author_did
        ORDER BY post_count DESC, total_likes DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    accounts = []
    for row in rows:
        did = row["author_did"]
        handle = row["author_handle"] or ""
        post_count = row["post_count"] or 0
        total_likes = row["total_likes"] or 0
        total_replies = row["total_replies"] or 0
        total_reposts = row["total_reposts"] or 0

        # Simple relevance scoring
        relevance_score = (post_count * 1.0) + (total_likes * 0.1) + (total_replies * 0.5) + (total_reposts * 0.3)

        keywords_str = row["keywords"] or ""
        top_tags = row["top_tags"] or ""

        # Generate why_relevant
        why = []
        if post_count >= 5:
            why.append(f"active contributor ({post_count} posts)")
        if total_likes >= 20:
            why.append(f"highly liked ({total_likes} total likes)")
        if any(k in keywords_str.lower() for k in ["tofu", "tempeh", "vegan food"]):
            why.append("food/fitness category")
        if any(k in keywords_str.lower() for k in ["burnout", "quit my job", "sick leave"]):
            why.append("labor/work category")
        if any(k in keywords_str.lower() for k in ["trail", "ultralight", "thru hike"]):
            why.append("gear/trail category")
        if any(k in keywords_str.lower() for k in ["neurodivergent", "adhd", "skate"]):
            why.append("community/identity category")

        why_relevant = "; ".join(why) if why else "matched keyword patterns"

        accounts.append({
            "did": did,
            "handle": handle,
            "display_name": row["display_name"] or handle.split(".bsky.social")[0] if handle else did,
            "description": row["description"] or "",
            "follower_count": row["follower_count"] or 0,
            "post_count": post_count,
            "relevance_score": round(relevance_score, 3),
            "top_tags": top_tags,
            "why_relevant": why_relevant,
        })

    accounts.sort(key=lambda x: x["relevance_score"], reverse=True)
    return accounts


def export_accounts_json(path: str = "accounts.json") -> None:
    """Write top accounts to a JSON file."""
    accounts = compute_accounts()
    with open(path, "w") as f:
        json.dump(accounts, f, indent=2)
    print(f"[✓] Exported {len(accounts)} accounts to {path}")


def run_account_discovery() -> int:
    """Called periodically to refresh accounts.json."""
    export_accounts_json()
    return len(compute_accounts())


if __name__ == "__main__":
    import sys
    count = run_account_discovery()
    sys.exit(0)