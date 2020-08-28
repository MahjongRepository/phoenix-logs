import json
import os

import requests

from download_game_ids import DownloadGameId
from live_games.db import get_current_time


current_directory = os.path.dirname(os.path.realpath(__file__))
db_folder = os.path.join(current_directory, "db")


def main():
    start_year = 2006

    current_date = get_current_time()
    stop_year = current_date.year

    db_file = os.path.join(db_folder, "yakuman.db")
    downloader = DownloadGameId(None, db_file, None, None)
    if not os.path.exists(db_file):
        downloader.set_up_database()

    added_log_ids = []

    for year in range(start_year, stop_year + 1):
        months = ["{:02}".format(x) for x in range(1, 13)]

        # for 2006 year we have statistics only for three months
        if year == start_year:
            months = ["10", "11", "12"]

        # we don't need to load data from the future
        if stop_year == year:
            months = ["{:02}".format(x) for x in range(1, current_date.month)]

        for month in months:
            url = "http://tenhou.net/sc/{}/{}/ykm.js".format(year, month)
            print(url)

            response = requests.get(url).content.decode("utf-8")

            if "ykm=['" in response:
                data = parse_new_format(response)
            else:
                data = parse_old_format(response)

            results = []
            for x in data:
                date = format_date(year, month, x[0])
                log_id = clean_up_log_id(x[1])

                if log_id not in added_log_ids:
                    added_log_ids.append(log_id)
                    results.append(
                        {"log_id": log_id, "game_date": date, "is_tonpusen": 0, "is_sanma": 0,}
                    )

            downloader.add_logs_to_database(results)


def parse_new_format(data: str):
    # new format
    if "\r\n" in data:
        data = data.split("\r\n")[2].strip()
        data = data[4:-1].replace('"', '\\"').replace("'", '"')
        data = json.loads(data)
    # old format
    else:
        data = data.split(";\n")[2].strip()
        data = data[4:].replace('"', '\\"').replace("'", '"').replace("\n", "")
        data = json.loads(data)

    results = []
    for x in range(0, len(data), 5):
        date = data[x]
        log_id = data[x + 4]
        results.append([date, log_id])

    return results


def parse_old_format(data: str):
    """
    Tenhou sends these data as JS array that had to be run with eval.
    I don't want to do it, so because of that there all these .split() functions.
    """
    results = []
    lines = data.replace("['", ",['").replace("\n", "").split(",['")
    for line in lines:
        if "gm-" not in line:
            continue

        temp = line.split("','")
        date = temp[0]
        log_id = "200" + temp[1].split("'200")[1].split("',")[0]

        results.append([date, log_id])

    return results


def clean_up_log_id(log_id: str):
    return log_id.split("&")[0].strip()


def format_date(year, month, date):
    day = date.split("/")[1].split(" ")[0].strip()
    hours_and_minutes = date.split(" ")[1].strip()
    return f"{year}-{month}-{day} {hours_and_minutes}"


if __name__ == "__main__":
    main()
