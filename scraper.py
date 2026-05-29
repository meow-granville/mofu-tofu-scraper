"""atproto search-based post scraper for Mofu Tofu."""

import time
import sqlite3
from datetime import datetime
from typing import Optional
from atproto import Client as AtprotoClient

from db import get_conn, init as db_init

# Keyword groups
KEYWORDS = {
    "food":      ["tofu", "tempeh", "vegetarian cooking", "plant-based", "mapo tofu", "tofu scramble", "vegan food"],
    "labor":     ["quiet quit", "sabbatical", "sick leave", "burnout", "i quit my job", "constructive dismissal"],
    "gear":      ["trail running shoe", "Decathlon tent", "Arc'teryx", "Quechua", "ultralight backpack", "thru hike gear"],
    "community": ["neurodivergent", "ADHD cook", "skate", "bad at skating", "mostly vegetarian"],
}

# Category emoji for tagging
CATEGORY_EMOJI = {
    "food":      "🍽️",
    "labor":     "⚠️",
    "gear":      "🎒",
    "community": "🌱",
}


def get_seen_uris() -> set[str]:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT uri FROM posts")
    rows = cursor.fetchall()
    conn.close()
    return {r["uri"] for r in rows}


def insert_post(conn: sqlite3.Connection, cursor, post, keyword: str, category: str) -> bool:
    """Insert a post (post is an atproto model object, not a dict)."""
    emoji = CATEGORY_EMOJI.get(category, "🏷️")
    tags = f"{emoji} {category}"
    now = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT OR IGNORE INTO posts
        (uri, cid, author_did, author_handle, text, created_at, indexed_at, tags, keyword, relevance_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        post.uri,
        post.cid,
        post.author.did,
        getattr(post.author, 'handle', ''),
        post.record.text if hasattr(post.record, 'text') else '',
        getattr(post.record, 'created_at', now) if hasattr(post.record, 'created_at') else now,
        now,
        tags,
        keyword,
        1.0,  # base relevance
    ))
    return cursor.rowcount > 0


def search_keyword(client: AtprotoClient, keyword: str, category: str, seen_uris: set[str]) -> list:
    """Search Bluesky for a keyword and return post objects not yet in DB."""
    results = []
    cursor_param = None

    for page in range(3):  # up to 3 pages per keyword
        try:
            response = client.app.bsky.feed.search_posts(
                {'q': keyword, 'limit': 25, 'cursor': cursor_param}
            )
        except Exception as e:
            print(f"  [!] search_posts failed for '{keyword}': {e}")
            break

        posts = getattr(response, "posts", [])
        if not posts:
            break

        for post in posts:
            if post.uri in seen_uris:
                continue
            results.append(post)

        cursor_param = getattr(response, "cursor", None)
        if not cursor_param:
            break

        time.sleep(0.5)  # be gentle with rate limits

    return results


def run_scraper(bluesky_handle: Optional[str] = None, bluesky_password: Optional[str] = None) -> int:
    """
    Main scrape entry point.
    Returns number of new posts inserted.
    """
    db_init()

    client = AtprotoClient()
    if bluesky_handle and bluesky_password:
        client.login(bluesky_handle, bluesky_password)
        print("[*] Logged into Bluesky")
    else:
        print("[*] Running unauthenticated (public feed only)")

    seen_uris = get_seen_uris()
    conn = get_conn()
    cursor = conn.cursor()
    new_count = 0

    for category, keywords in KEYWORDS.items():
        for keyword in keywords:
            print(f"[*] Searching [{category}] '{keyword}'...")
            posts = search_keyword(client, keyword, category, seen_uris)
            inserted = 0
            for post in posts:
                if insert_post(conn, cursor, post, keyword, category):
                    inserted += 1
                    new_count += 1
            print(f"    → {inserted} new posts (total collected: {len(posts)})")
            time.sleep(1)

    conn.close()
    print(f"[✓] Scraping complete — {new_count} new posts inserted")
    return new_count


if __name__ == "__main__":
    import os, sys
    handle = os.environ.get("BSKY_HANDLE", "")
    password = os.environ.get("BSKY_PASSWORD", "")
    count = run_scraper(handle or None, password or None)
    sys.exit(0)