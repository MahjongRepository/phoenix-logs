import os
from distutils.dir_util import mkpath

from optparse import OptionParser

from datetime import datetime

from download_game_ids import DownloadGameId
from download_logs_content import DownloadLogContent

current_directory = os.path.dirname(os.path.realpath(__file__))
logs_directory = os.path.join(current_directory, "temp")
db_folder = os.path.join(current_directory, "db")

current_year = str(datetime.now().year)


def set_up_folders():
    if not os.path.exists(logs_directory):
        mkpath(logs_directory)

    if not os.path.exists(db_folder):
        mkpath(db_folder)


def parse_command_line_arguments():
    parser = OptionParser()

    parser.add_option(
        "-y", "--year", type="string", default=None, help="Target year to download logs"
    )
    parser.add_option("-p", "--db_path", type="string")
    parser.add_option("-a", "--action", type="string", default="id", help="id or content")
    parser.add_option("-l", "--limit", type="int", default=0, help="To download content script")
    parser.add_option("-t", "--threads", type="int", default=3, help="Count of threads")

    parser.add_option(
        "-s", action="store_true", dest="start", help="Download log ids from the start of the year"
    )

    opts, _ = parser.parse_args()
    return opts


def main():
    set_up_folders()

    opts = parse_command_line_arguments()

    if opts.db_path:
        db_file = opts.db_path
    else:
        db_file = os.path.join(db_folder, f"{opts.year}.db")

    # special condition to download historical data from previous years
    historical_download = None
    if not opts.year == current_year:
        historical_download = opts.year

    if opts.action == "id":
        DownloadGameId(logs_directory, db_file, historical_download, opts.start).process()
    elif opts.action == "content":
        DownloadLogContent(db_file, opts.limit, opts.threads).process()
    else:
        print("Unknown action")


if __name__ == "__main__":
    main()
