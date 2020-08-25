import bz2
import logging
import sqlite3
from datetime import datetime

import pytz

logger = logging.getLogger("watcher")


def get_db_name():
    current_time = get_current_time()
    db_name = f"live_{current_time.year}_{current_time.month:02d}.db"
    return db_name


def create_new_database(db_path):
    logger.debug(f"Set up new database {db_path}")

    connection = sqlite3.connect(db_path)

    with connection:
        cursor = connection.cursor()
        cursor.execute(
            """
                CREATE TABLE live_logs (
                    log_id text primary key,
                    game_date text,
                    is_tonpusen int,
                    compressed_log_content text
                );
            """
        )
        cursor.execute("CREATE INDEX is_tonpusen_index ON live_logs (is_tonpusen);")


def insert_log_record(db_path, game, log_content, game_started):
    game_id = game["game_id"]
    logger.debug(f"{game_id} Insert to DB")

    connection = sqlite3.connect(db_path)
    with connection:
        cursor = connection.cursor()
        compressed_log_content = bz2.compress(log_content.encode("utf-8"))
        new_game_id = f"{game_id}_{int(datetime.timestamp(game_started))}"
        cursor.execute(
            """
                INSERT INTO live_logs (log_id, game_date, is_tonpusen, compressed_log_content) 
                VALUES (?, ?, ?, ?);
            """,
            [
                new_game_id,
                game_started.strftime("%Y-%m-%d %H:%M:%S"),
                game["is_tonpusen"] and 1 or 0,
                compressed_log_content,
            ],
        )


def get_games_count(db_path):
    connection = sqlite3.connect(db_path)
    with connection:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) AS count FROM live_logs")
        return cursor.fetchall()[0][0]


def get_current_time():
    tz = pytz.timezone("Asia/Tokyo")
    return datetime.now(tz)
