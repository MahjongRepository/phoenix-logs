import gzip
import os
import re
import sqlite3
from datetime import datetime
from optparse import OptionParser
from typing import List

db_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "db")


def main():
    parser = OptionParser()
    parser.add_option("-y", "--year", type="string", default=str(datetime.now().year), help="Target year")
    parser.add_option("-p", "--db_path", type="string")
    opts, _ = parser.parse_args()

    if opts.db_path:
        db_file = opts.db_path
    else:
        db_file = os.path.join(db_folder, f"{opts.year}.db")

    connection = sqlite3.connect(db_file)

    were_errors = False

    with connection:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) from logs;")
        total = cursor.fetchone()[0]

        print("Fetching logs...")
        cursor.execute("SELECT log_id, log_content FROM logs where is_processed = 1;")
        data = cursor.fetchall()

        print("Decompressing and checking logs content...")
        parser = LogParser()
        valid_logs = 0
        for x in data:
            was_error = False
            log_id = x[0]
            try:
                log_content = gzip.decompress(x[1]).decode("utf-8")
                if not log_content:
                    was_error = True

                if log_content:
                    parsed_rounds = parser.split_log_to_game_rounds(log_content)
                    if not parsed_rounds:
                        was_error = True
                    else:
                        valid_logs += 1
            except Exception:
                was_error = True

            if was_error:
                were_errors = True
                print("Found wrong log content, adding it back to download queue")
                cursor.execute(
                    f'UPDATE logs set is_processed = 0, was_error = 0, log_content="" where log_id = "{log_id}"'
                )

    if not were_errors:
        print(f"Everything is fine, checked {valid_logs}/{total}")


class LogParser:
    def split_log_to_game_rounds(self, log_content: str) -> List[List[str]]:
        tag_start = 0
        rounds = []
        tag = None

        current_round_tags = []
        for x in range(0, len(log_content)):
            if log_content[x] == ">":
                tag = log_content[tag_start : x + 1]
                tag_start = x + 1

            # not useful tags
            skip_tags = ["SHUFFLE", "TAIKYOKU", "mjloggm", "GO"]
            if tag and any([x in tag for x in skip_tags]):
                tag = None

            # new hand was started
            if self.is_init_tag(tag) and current_round_tags:
                rounds.append(current_round_tags)
                current_round_tags = []

            # the end of the game
            if tag and "owari" in tag:
                rounds.append(current_round_tags)

            if tag:
                if self.is_init_tag(tag):
                    # we dont need seed information
                    # it appears in old logs format
                    find = re.compile(r'shuffle="[^"]*"')
                    tag = find.sub("", tag)

                # add processed tag to the round
                current_round_tags.append(tag)
                tag = None

        return rounds

    def is_init_tag(self, tag):
        return tag and "INIT" in tag


if __name__ == "__main__":
    main()
