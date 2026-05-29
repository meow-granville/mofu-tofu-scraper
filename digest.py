"""Daily digest: top 10 posts from the last 24 hours by engagement score."""

import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional

from db import get_conn


def get_top_posts(limit: int = 10) -> list[dict]:
    conn = get_conn()
    cursor = conn.cursor()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()

    cursor.execute("""
        SELECT
            uri,
            author_handle,
            text,
            tags,
            keyword,
            likes,
            replies,
            reposts,
            created_at,
            (likes * 2 + replies + reposts) AS score
        FROM posts
        WHERE created_at >= ?
        ORDER BY score DESC
        LIMIT ?
    """, (cutoff, limit))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def print_digest(title: str = "🍡 Mofu Tofu — 24h Top Posts") -> None:
    posts = get_top_posts(10)
    if not posts:
        print("[*] No posts in the last 24 hours")
        return

    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"  Generated: {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")

    for i, post in enumerate(posts, 1):
        score = post["score"]
        text = post["text"][:120] + ("..." if len(post["text"]) > 120 else "")
        author = post["author_handle"] or post["uri"].split("/")[-1][:20]
        tags = post["tags"] or ""

        print(f"  {i:2}. [{score:4.0f}] {tags}")
        print(f"       @{author}")
        print(f"       {text}")
        print(f"       ♥{post['likes']}  💬{post['replies']}  🔁{post['reposts']}")
        print()


def run_digest() -> int:
    """Print digest to stdout. Returns count of posts shown."""
    posts = get_top_posts(10)
    print_digest()
    return len(posts)


if __name__ == "__main__":
    import sys
    count = run_digest()
    sys.exit(0)