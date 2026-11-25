import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "knowledge.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():

    with get_connection() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                chunks INTEGER NOT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        legacy_history_exists = conn.execute("""
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = 'chat_history'
        """).fetchone()

        legacy_chats = []
        if legacy_history_exists:
            legacy_chats = conn.execute("""
                SELECT id, question, answer, mode,
                       COALESCE(created_at, CURRENT_TIMESTAMP) AS created_at
                FROM chat_history
                ORDER BY id
            """).fetchall()

    mysql_conn = get_mysql_connection()
    cursor = mysql_conn.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                sqlite_id BIGINT NULL UNIQUE,
                question TEXT NOT NULL,
                answer LONGTEXT NOT NULL,
                mode VARCHAR(32) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        if legacy_chats:
            cursor.executemany("""
                INSERT INTO chat_history
                    (sqlite_id, question, answer, mode, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE sqlite_id = VALUES(sqlite_id)
            """, [
                (
                    row["id"],
                    row["question"],
                    row["answer"],
                    row["mode"],
                    row["created_at"]
                )
                for row in legacy_chats
            ])

        mysql_conn.commit()
    except Exception:
        mysql_conn.rollback()
        raise
    finally:
        cursor.close()
        mysql_conn.close()


def get_mysql_connection():

    required_settings = ("MYSQL_USER", "MYSQL_DATABASE")
    missing_settings = [
        setting
        for setting in required_settings
        if not os.getenv(setting)
    ]

    if missing_settings:
        raise RuntimeError(
            "Missing MySQL configuration: "
            + ", ".join(missing_settings)
        )

    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.environ["MYSQL_USER"],
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.environ["MYSQL_DATABASE"]
    )


def save_document(doc_id, filename, chunks):

    with get_connection() as conn:

        conn.execute("""
            INSERT INTO documents (id, filename, chunks)
            VALUES (?, ?, ?)
        """, (doc_id, filename, chunks))


def list_documents():

    with get_connection() as conn:

        rows = conn.execute("""
            SELECT * FROM documents
            ORDER BY uploaded_at DESC
        """).fetchall()

        return [dict(row) for row in rows]


def save_chat(question, answer, mode):

    conn = get_mysql_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO chat_history
            (question, answer, mode)
            VALUES (%s, %s, %s)
        """, (question, answer, mode))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def get_chat_history():

    conn = get_mysql_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, question, answer, mode, created_at
            FROM chat_history
            ORDER BY id DESC
        """)

        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()