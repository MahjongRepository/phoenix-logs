# -*- coding: utf-8 -*-
"""
Script to download phoenix games and store their ids in the database
It can be run once a day or so, to get latest replays data.
Or it can be run to get data from previous years.
"""

import shutil
import zipfile
from datetime import datetime
import calendar
import gzip
import os

import sqlite3

import requests
import sys


class DownloadGameId(object):
    logs_directory = ''
    db_file = ''
    historical_download = None
    from_start = False

    def __init__(self, logs_directory, db_file, historical_download, from_start):
        """
        :param logs_directory: directory where to store downloaded logs
        :param db_file: to save log ids
        :param historical_download: year or None
        :param from_start: download logs from the start of the year
        """
        self.logs_directory = logs_directory
        self.db_file = db_file
        self.historical_download = historical_download
        self.from_start = from_start

    def process(self):
        # for the initial set up
        if not os.path.exists(self.db_file):
            self.set_up_database()

        if self.historical_download:
            records_was_added = self.download_year_archive(self.historical_download)
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

        last_name = ''
        with connection:
            cursor = connection.cursor()
            cursor.execute('SELECT * FROM last_downloads ORDER BY date DESC LIMIT 1;')
            data = cursor.fetchone()
            if data:
                last_name = data[0]
                print('Latest downloaded archive: {}'.format(last_name))

        download_url = 'http://tenhou.net/sc/raw/dat/'
        if self.from_start:
            url = 'http://tenhou.net/sc/raw/list.cgi?old'
        else:
            url = 'http://tenhou.net/sc/raw/list.cgi'

        response = requests.get(url)
        response = response.text.replace('list(', '').replace(');', '')
        response = response.split(',\r\n')

        records_was_added = False
        for archive_name in response:
            if 'scc' in archive_name:
                archive_name = archive_name.split("',")[0].replace("{file:'", '')

                file_name = archive_name
                if '/' in file_name:
                    file_name = file_name.split('/')[1]

                if file_name > last_name:
                    last_name = file_name
                    records_was_added = True

                    archive_path = os.path.join(self.logs_directory, file_name)
                    if not os.path.exists(archive_path):
                        print('Downloading... {}'.format(archive_name))

                        url = '{}{}'.format(download_url, archive_name)
                        page = requests.get(url)
                        with open(archive_path, 'wb') as f:
                            f.write(page.content)

        if records_was_added:
            unix_time = calendar.timegm(datetime.utcnow().utctimetuple())
            with connection:
                cursor = connection.cursor()
                cursor.execute('INSERT INTO last_downloads VALUES (?, ?);', [last_name, unix_time])
        else:
            print("There is no new logs")

        return records_was_added

    def download_year_archive(self, year):
        archive_name = 'scraw{}.zip'.format(year)
        download_url = 'http://tenhou.net/sc/raw/{}'.format(archive_name)

        archive_path = os.path.join(self.logs_directory, archive_name)
        if not os.path.exists(archive_path):
            print('Downloading... {}'.format(archive_name))

            response = requests.get(download_url, stream=True)
            total_length = response.headers.get('content-length')

            with open(archive_path, 'wb') as f:
                # no content length header
                if total_length is None:
                    f.write(response.content)
                else:
                    downloaded = 0
                    total_length = int(total_length)
                    total_length_in_kb = int(total_length / 1024)
                    for data in response.iter_content(chunk_size=40960):
                        downloaded += len(data)
                        f.write(data)

                        # simple progress bar
                        done = int(50 * downloaded / total_length)
                        downloaded_in_kb = int(downloaded / 1024)
                        sys.stdout.write('\t{}/{}'.format(downloaded_in_kb, total_length_in_kb))
                        sys.stdout.write("\r[%s%s]" % ('=' * done, ' ' * (50 - done)))
                        sys.stdout.flush()
            print('')
            print('Downloaded')
        else:
            print('{} already exists'.format(archive_name))

        print('Extracting archive...')
        with zipfile.ZipFile(archive_path) as zip_file:
            for member in zip_file.namelist():
                filename = os.path.basename(member)
                # skip directories
                if not filename:
                    continue

                # copy file (taken from zipfile's extract)
                source = zip_file.open(member)
                target = open(os.path.join(self.logs_directory, filename), 'wb')
                with source, target:
                    shutil.copyfileobj(source, target)
        print('Extracted')

        return True

    def process_local_files(self):
        """
        Function to process scc*.html files that can be obtained
        from the annual archives with logs or from latest phoenix games api
        """
        print('Preparing the list of games...')

        results = []
        for file_name in os.listdir(self.logs_directory):
            if 'scc' not in file_name:
                continue

            # after 2013 tenhou produced compressed logs
            if '.gz' in file_name:
                with gzip.open(os.path.join(self.logs_directory, file_name), 'r') as f:
                    for line in f:
                        line = str(line, 'utf-8')
                        self._process_log_line(line, results)
            else:
                with open(os.path.join(self.logs_directory, file_name)) as f:
                    for line in f:
                        self._process_log_line(line, results)

        print('Found {} games'.format(len(results)))
        shutil.rmtree(self.logs_directory)
        print('Temp folder was removed')
        return results

    def set_up_database(self):
        """
        Init logs table and add basic indices
        :return:
        """
        print('Set up new database {}'.format(self.db_file))
        connection = sqlite3.connect(self.db_file)

        with connection:
            cursor = connection.cursor()
            cursor.execute("""
            CREATE TABLE logs(log_id text primary key,
                              is_tonpusen int,
                              is_hirosima int,
                              is_processed int,
                              was_error int,
                              log_content text,
                              log_hash text);
            """)
            cursor.execute("CREATE INDEX is_tonpusen_index ON logs (is_tonpusen);")
            cursor.execute("CREATE INDEX is_hirosima ON logs (is_hirosima);")
            cursor.execute("CREATE INDEX is_processed_index ON logs (is_processed);")
            cursor.execute("CREATE INDEX was_error_index ON logs (was_error);")
            cursor.execute("CREATE INDEX log_hash ON logs (log_hash);")

            cursor.execute("""
            CREATE TABLE last_downloads(name text,
                                        date int);
            """)

    def add_logs_to_database(self, results):
        """
        Store logs to the sqllite3 database
        """
        print('Inserting new ids to the database...')
        connection = sqlite3.connect(self.db_file)
        with connection:
            cursor = connection.cursor()

            for item in results:
                cursor.execute('INSERT INTO logs VALUES (?, ?, ?, 0, 0, "", "");',
                               [item[0], item[1], item[2] and 1 or 0])
        print('Done')

    def _process_log_line(self, line, results):
        line = line.strip()
        # sometimes there is empty lines in the file
        if not line:
            return None

        result = line.split('|')
        game_type = result[2].strip()

        is_hirosima = game_type.startswith('三')

        # example: <a href="http://tenhou.net/0/?log=2009022023gm-00e1-0000-c603794d">牌譜</a>
        game_id = result[3].split('log=')[1].split('"')[0]

        # example: 四鳳東喰赤
        is_tonpusen = game_type[2] == '東'

        results.append([game_id, is_tonpusen, is_hirosima])
