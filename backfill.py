"""Engagement backfill: fetch like/reply/repost counts for posts that need them."""

import time
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Optional
from atproto import Client as AtprotoClient

from db import get_conn


def needs_engagement(cursor) -> list[str]:
    """Return URIs of posts from last 24h that have zero engagement cached."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    cursor.execute("""
        SELECT uri FROM posts
        WHERE created_at >= ?
          AND (likes = 0 AND replies = 0 AND reposts = 0)
    """, (cutoff,))
    return [row["uri"] for row in cursor.fetchall()]


def fetch_engagement(client: AtprotoClient, uri: str) -> dict:
    """Fetch like/reply/repost counts for a single post URI via atproto."""
    try:
        # atproto client can get a post via get_post
        post_record = client.get_post(uri)
        post = post_record.post
        # engagement counts live in post.like_count, reply_count, repost_count
        return {
            "likes": getattr(post, "like_count", 0) or 0,
            "replies": getattr(post, "reply_count", 0) or 0,
            "reposts": getattr(post, "repost_count", 0) or 0,
        }
    except Exception as e:
        return {"likes": 0, "replies": 0, "reposts": 0}


def upsert_engagement(conn: sqlite3.Connection, cursor, uri: str, data: dict) -> None:
    now = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO engagement_cache (uri, likes, replies, reposts, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(uri) DO UPDATE SET
            likes = excluded.likes,
            replies = excluded.replies,
            reposts = excluded.reposts,
            updated_at = excluded.updated_at
    """, (uri, data["likes"], data["replies"], data["reposts"], now))
    # Also update posts table
    cursor.execute("""
        UPDATE posts SET likes = ?, replies = ?, reposts = ?
        WHERE uri = ?
    """, (data["likes"], data["replies"], data["reposts"], uri))


def run_engagement_backfill() -> int:
    """
    Fetch engagement metrics for posts that don't have them yet.
    Returns number of posts updated.
    """
    conn = get_conn()
    cursor = conn.cursor()

    uris = needs_engagement(cursor)
    if not uris:
        print("[*] No posts need engagement backfill")
        conn.close()
        return 0

    print(f"[*] Backfilling engagement for {len(uris)} posts...")

    client = AtprotoClient()
    updated = 0

    for uri in uris:
        data = fetch_engagement(client, uri)
        upsert_engagement(conn, cursor, uri, data)
        updated += 1
        if updated % 10 == 0:
            conn.commit()
        time.sleep(0.3)  # rate limit

    conn.commit()
    conn.close()
    print(f"[✓] Engagement backfill complete — {updated} posts updated")
    return updated


if __name__ == "__main__":
    import sys
    count = run_engagement_backfill()
    sys.exit(0)