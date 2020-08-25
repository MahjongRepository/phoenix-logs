import sqlite3
from datetime import datetime

import pytz


def get_db_name():
    current_time = get_current_time()
    db_name = f"live_{current_time.year}_{current_time.month:02d}.db"
    return db_name


def create_new_database(db_path):
    print("Set up new database {}".format(db_path))
    connection = sqlite3.connect(db_path)

    with connection:
        cursor = connection.cursor()
        cursor.execute(
            """
                CREATE TABLE live_logs(
                    log_id text primary key,
                    date text,
                    is_tonpusen int,
                    is_completed int,
                    log_content text
                );
            """
        )
        cursor.execute("CREATE INDEX date ON live_logs (date);")
        cursor.execute("CREATE INDEX is_tonpusen_index ON live_logs (is_tonpusen);")
        cursor.execute("CREATE INDEX is_completed_index ON live_logs (is_completed);")


def get_current_time():
    tz = pytz.timezone("Asia/Tokyo")
    return datetime.now(tz)
