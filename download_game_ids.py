# -*- coding: utf-8 -*-
"""
Script to download phoenix games and store their IDs in the database
It can be run once a day or so, to get latest games IDs.
Or it can be run to get data from previous years from .zip file.
"""

import calendar
import gzip
import os
import shutil
import sqlite3
import sys
import zipfile
from datetime import datetime

import requests


class DownloadGameId(object):
    logs_directory = ""
    db_file = ""
    historical_download = None
    from_start = False

    def __init__(self, logs_directory, db_file, year, from_start, extract_from_archive):
        """
        :param logs_directory: directory where to store downloaded logs
        :param db_file: to save log ids
        :param year: year for what we need to download data
        :param from_start: download logs from the start of the year
        """
        self.logs_directory = logs_directory
        self.db_file = db_file
        self.year = year
        self.from_start = from_start
        self.extract_from_archive = extract_from_archive

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
        }

    def process(self):
        # for the initial set up
        if not os.path.exists(self.db_file):
            self.set_up_database()

        if self.extract_from_archive:
            records_was_added = self.process_year_archive(self.year)
        else:
            records_was_added = self.download_latest_games_id()

        if records_was_added:
            results = self.process_local_files()
            if results:
                self.add_logs_to_database(results)

    def download_latest_games_id(self):
        """
        Download latest phoenix games from tenhou.net
        """
        connection = sqlite3.connect(self.db_file)

        last_name = ""
        with connection:
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM last_downloads ORDER BY date DESC LIMIT 1;")
            data = cursor.fetchone()
            if data:
                last_name = data[0]
                print("Latest downloaded archive: {}".format(last_name))

        download_url = "https://tenhou.net/sc/raw/dat/"
        if self.from_start:
            url = "https://tenhou.net/sc/raw/list.cgi?old"
        else:
            url = "https://tenhou.net/sc/raw/list.cgi"

        response = requests.get(url, headers=self.headers)
        response = response.text.replace("list(", "").replace(");", "")
        response = response.split(",\r\n")

        records_was_added = False
        for archive_name in response:
            if "scc" in archive_name:
                archive_name = archive_name.split("',")[0].replace("{file:'", "")

                file_name = archive_name
                if "/" in file_name:
                    file_name = file_name.split("/")[1]

                if file_name > last_name:
                    last_name = file_name
                    records_was_added = True

                    archive_path = os.path.join(self.logs_directory, file_name)
                    if not os.path.exists(archive_path):
                        print("Downloading... {}".format(archive_name))

                        url = "{}{}".format(download_url, archive_name)
                        page = requests.get(url, headers=self.headers)
                        with open(archive_path, "wb") as f:
                            f.write(page.content)

        if records_was_added:
            unix_time = calendar.timegm(datetime.utcnow().utctimetuple())
            with connection:
                cursor = connection.cursor()
                cursor.execute("INSERT INTO last_downloads VALUES (?, ?);", [last_name, unix_time])
        else:
            print("There is no new logs")

        return records_was_added

    def process_year_archive(self, year):
        archive_name = "scraw{}.zip".format(year)

        archive_path = os.path.join(self.logs_directory, archive_name)

        print("Extracting archive...")
        with zipfile.ZipFile(archive_path) as zip_file:
            for member in zip_file.namelist():
                filename = os.path.basename(member)
                # skip directories
                if not filename:
                    continue

                # copy file (taken from zipfile's extract)
                source = zip_file.open(member)
                target = open(os.path.join(self.logs_directory, filename), "wb")
                with source, target:
                    shutil.copyfileobj(source, target)
        print("Extracted")

        return True

    def process_local_files(self):
        """
        Function to process scc*.html files that can be obtained
        from the annual archives with logs or from latest phoenix games api
        """
        print("Preparing the list of games...")

        results = []
        for file_name in os.listdir(self.logs_directory):
            if "scc" not in file_name:
                continue

            # after 2013 tenhou produced compressed logs
            if ".gz" in file_name:
                with gzip.open(os.path.join(self.logs_directory, file_name), "r") as f:
                    for line in f:
                        line = str(line, "utf-8")
                        result = self._process_log_line(line)
                        if result:
                            results.append(result)
            else:
                with open(os.path.join(self.logs_directory, file_name)) as f:
                    for line in f:
                        result = self._process_log_line(line)
                        if result:
                            results.append(result)

        results = [x for x in results if x["game_date"][:4] == str(self.year)]

        print("Found {} games".format(len(results)))
        shutil.rmtree(self.logs_directory)
        print("Temp folder was removed")
        return results

    def set_up_database(self):
        """
        Init logs table and add basic indices
        :return:
        """
        print("Set up new database {}".format(self.db_file))
        connection = sqlite3.connect(self.db_file)

        with connection:
            cursor = connection.cursor()
            cursor.execute(
                """
            CREATE TABLE logs(
                log_id text primary key,
                date text,
                is_tonpusen int,
                is_sanma int,
                is_processed int,
                was_error int,
                log_content text
            );
            """
            )

            cursor.execute(
                """
                CREATE TABLE last_downloads(name text, date int);
            """
            )

    def add_logs_to_database(self, results):
        """
        Store logs to the sqllite3 database
        """
        print("Inserting new ids to the database...")
        connection = sqlite3.connect(self.db_file)
        with connection:
            cursor = connection.cursor()

            for item in results:
                cursor.execute(
                    "INSERT INTO logs (log_id, date, is_tonpusen, is_sanma, is_processed, was_error, log_content)"
                    'VALUES (?, ?, ?, ?, 0, 0, "");',
                    [
                        item["log_id"],
                        item["game_date"],
                        item["is_tonpusen"] and 1 or 0,
                        item["is_sanma"] and 1 or 0,
                    ],
                )
        print("Done")

    def _process_log_line(self, line):
        line = line.strip()
        # sometimes there is empty lines in the file
        if not line:
            return None

        result = line.split("|")
        game_type = result[2].strip()

        is_sanma = game_type.startswith("三")

        # example: <a href="https://tenhou.net/0/?log=2009022023gm-00e1-0000-c603794d">牌譜</a>
        log_id = result[3].split("log=")[1].split('"')[0]

        # example: 四鳳東喰赤
        is_tonpusen = game_type[2] == "東"

        # parse date from log id and convert it to sqlite date format
        game_date = datetime.strptime(
            log_id.split("gm-")[0][0:8] + result[0].strip(), "%Y%m%d%H:%M"
        ).strftime("%Y-%m-%d %H:%M")

        return {"log_id": log_id, "is_tonpusen": is_tonpusen, "is_sanma": is_sanma, "game_date": game_date}
