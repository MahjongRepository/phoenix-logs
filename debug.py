# -*- coding: utf-8 -*-
import os
import sqlite3
from optparse import OptionParser
from datetime import datetime

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

    with connection:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) from logs;")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) from logs where is_processed = 1;")
        processed = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) from logs where was_error = 1;")
        with_errors = cursor.fetchone()[0]

        print("Total: {}".format(total))
        print("Processed: {}".format(processed))
        print("With errors: {}".format(with_errors))

        was_errors = False

        if with_errors > 0:
            was_errors = True
            print("")
            print("WARNING!")
            print("There are {} records with errors".format(with_errors))
            print("It means that they weren't downloaded properly")
            cursor.execute(
                'UPDATE logs set is_processed = 0, was_error = 0, log_hash="", log_content="" where was_error = 1'
            )
            print("{} records were added to the download queue again".format(with_errors))
            print("")

        cursor.execute(
            "SELECT COUNT(log_hash) AS count, log_hash FROM logs GROUP BY log_hash ORDER BY count DESC;"
        )
        not_unique_hashes = [x for x in cursor.fetchall() if x[0] > 1 and x[1]]
        not_unique_hashes = [x[1] for x in not_unique_hashes]
        count_of_not_unique = len(not_unique_hashes)

        if count_of_not_unique:
            was_errors = True
            print("")
            print("WARNING!")
            print("There are {} not unique hashes in the DB".format(count_of_not_unique))
            print("It is happens because sometimes tenhou return content that belongs to other log")
            s = ",".join(["'{}'".format(x) for x in not_unique_hashes])
            cursor.execute(
                'UPDATE logs set is_processed = 0, was_error = 0, log_hash="", log_content="" where log_hash in ({});'.format(
                    s
                )
            )
            print("{} records were added to the download queue again".format(count_of_not_unique))
            print("")

        if not was_errors:
            print("")
            print("Everything is fine")
            print("")


if __name__ == "__main__":
    main()
