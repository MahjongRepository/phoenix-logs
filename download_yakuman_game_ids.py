import json
import os
from optparse import OptionParser

import requests

from download_game_ids import DownloadGameId

current_directory = os.path.dirname(os.path.realpath(__file__))
db_folder = os.path.join(current_directory, "db")


def main():
    """
    The first date for available yakuman logs is 2006-10
    """
    parser = OptionParser()
    parser.add_option("-y", "--year", type="string")
    parser.add_option("-m", "--month", type="string")
    opts, _ = parser.parse_args()

    if len(opts.month) != 2:
        print("Month should be 2 digits")
        return

    yakuman_folder = os.path.join(db_folder, "yakuman")
    if not os.path.exists(yakuman_folder):
        os.makedirs(yakuman_folder)

    yakuman_year_folder = os.path.join(yakuman_folder, opts.year)
    if not os.path.exists(yakuman_year_folder):
        os.makedirs(yakuman_year_folder)

    db_file = os.path.join(yakuman_year_folder, f"{opts.month}.db")

    downloader = DownloadGameId(None, db_file, None, None, False)
    if not os.path.exists(db_file):
        downloader.set_up_database()

    download_ids_for_date(downloader, opts.year, opts.month)


def download_ids_for_date(downloader, year: str, month: str):
    url = f"https://tenhou.net/sc/{year}/{month}/ykm.js"
    print(url)

    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
        },
    ).content.decode("utf-8")

    if "ykm=['" in response:
        data = parse_new_format(response)
    else:
        data = parse_old_format(response)

    results = []
    added_log_ids = []
    for x in data:
        date = format_date(year, month, x[0])
        log_id = clean_up_log_id(x[1])

        if log_id not in added_log_ids:
            added_log_ids.append(log_id)
            results.append(
                {
                    "log_id": log_id,
                    "game_date": date,
                    "is_tonpusen": 0,
                    "is_sanma": 0,
                }
            )

    downloader.add_logs_to_database(results)
    print(f"Added {len(results)} logs")


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
