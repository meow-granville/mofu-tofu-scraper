"""SQLite database init and helpers for Mofu Tofu scraper."""

import sqlite3
import os
from datetime import datetime, timezone
from typing import Optional

DB_PATH = os.environ.get("MOFU_DB", "mofu_tofu.db")

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init() -> None:
    """Create tables: posts and accounts."""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            uri TEXT PRIMARY KEY,
            cid TEXT NOT NULL,
            author_did TEXT NOT NULL,
            author_handle TEXT,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            indexed_at TEXT NOT NULL,
            likes INTEGER DEFAULT 0,
            replies INTEGER DEFAULT 0,
            reposts INTEGER DEFAULT 0,
            tags TEXT,
            keyword TEXT,
            relevance_score REAL DEFAULT 0.0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            did TEXT PRIMARY KEY,
            handle TEXT,
            display_name TEXT,
            description TEXT,
            follower_count INTEGER DEFAULT 0,
            post_count INTEGER DEFAULT 0,
            relevance_score REAL DEFAULT 0.0,
            top_tags TEXT,
            last_seen TEXT,
            why_relevant TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS engagement_cache (
            uri TEXT PRIMARY KEY,
            likes INTEGER DEFAULT 0,
            replies INTEGER DEFAULT 0,
            reposts INTEGER DEFAULT 0,
            updated_at TEXT,
            FOREIGN KEY (uri) REFERENCES posts(uri)
        )
    """)

    conn.commit()
    conn.close()

def reset() -> None:
    """Drop all tables and re-init — useful for testing."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS engagement_cache")
    cursor.execute("DROP TABLE IF EXISTS posts")
    cursor.execute("DROP TABLE IF EXISTS accounts")
    conn.commit()
    conn.close()
    init()