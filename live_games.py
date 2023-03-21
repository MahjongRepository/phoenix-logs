import logging
import os
from distutils.dir_util import mkpath
from optparse import OptionParser

from live_games.db import get_db_name, get_games_count
from live_games.runner import Watcher

current_directory = os.path.dirname(os.path.realpath(__file__))
db_folder = os.path.join(current_directory, "db")

logger = logging.getLogger("watcher")


def main():
    # set_up_logging()

    if not os.path.exists(db_folder):
        mkpath(db_folder)

    parser = OptionParser()
    parser.add_option("-d", "--debug", action="store_true")
    opts, _ = parser.parse_args()

    if opts.debug:
        db_path = os.path.join(db_folder, get_db_name())
        count = get_games_count(db_path)
        print(db_path)
        print(f"Games in DB: {count}")
    else:
        watcher = Watcher(db_folder)
        watcher.watch_games()


def set_up_logging():
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    ch.setFormatter(formatter)
    logger.addHandler(ch)


if __name__ == "__main__":
    main()
