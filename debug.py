import os
import sqlite3
from datetime import datetime
from optparse import OptionParser

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

        if with_errors > 0:
            print("")
            print("WARNING!")
            print("There are {} records with errors".format(with_errors))
            print("It means that they weren't downloaded properly")
            cursor.execute(
                'UPDATE logs set is_processed = 0, was_error = 0, log_content="" where was_error = 1'
            )
            print("{} records were added to the download queue again".format(with_errors))
        else:
            print("")
            print("Everything is fine")


if __name__ == "__main__":
    main()
