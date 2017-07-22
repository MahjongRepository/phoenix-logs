# -*- coding: utf-8 -*-
"""
Script will load log ids from the database and will download log content
"""
import bz2
import hashlib
import sqlite3
import threading
from datetime import datetime

import requests


class DownloadThread(threading.Thread):

    def __init__(self, downloader, results, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.downloader = downloader
        self.results = results

    def run(self):
        self.downloader.download_logs(self.results)


class DownloadLogContent(object):
    db_file = ''
    limit = 0
    redownload = False

    def __init__(self, db_file, limit, redownload):
        """
        :param db_file: db with loaded log ids
        """
        self.db_file = db_file
        self.limit = limit
        self.redownload = redownload

    def process(self):
        start_time = datetime.now()
        print('Load {} records'.format(self.limit))
        results = self.load_not_processed_logs()
        if not results:
            print('Nothing to download')

        # separate array to the 3 parts and download them simultaneously
        third = int(self.limit / 3)
        second_limit = third * 2

        first_thread = DownloadThread(self, results[0:third])
        second_thread = DownloadThread(self, results[third:second_limit])
        third_thread = DownloadThread(self, results[second_limit:])

        first_thread.start()
        second_thread.start()
        third_thread.start()

        first_thread.join()
        second_thread.join()
        third_thread.join()

        print('Worked time: {} seconds'.format((datetime.now() - start_time).seconds))

    def download_logs(self, results):
        for log_id in results:
            print('Process {}'.format(log_id))
            self.download_log_content(log_id)

    def download_log_content(self, log_id):
        """
        Download log content and store compressed version in the db
        """
        url = 'http://e.mjv.jp/0/log/?{0}'.format(log_id)

        binary_content = None
        was_error = False
        try:
            response = requests.get(url)
            binary_content = response.content
            # it can be an error page
            if 'mjlog' not in response.text:
                was_error = True
        except Exception as e:
            print(e)
            was_error = True

        connection = sqlite3.connect(self.db_file)

        with connection:
            cursor = connection.cursor()

            compressed_content = ''
            log_hash = ''
            if not was_error:
                    try:
                        compressed_content = bz2.compress(binary_content)
                        log_hash = hashlib.sha256(compressed_content).hexdigest()
                    except:
                        was_error = True

            cursor.execute('UPDATE logs SET is_processed = ?, was_error = ?, log_content = ?, log_hash = ? WHERE log_id = ?;',
                           [1, was_error and 1 or 0, compressed_content, log_hash, log_id])

    def load_not_processed_logs(self):
        connection = sqlite3.connect(self.db_file)

        with connection:
            cursor = connection.cursor()
            if self.redownload:
                cursor.execute('SELECT log_id FROM logs where was_error = 1 LIMIT ?;', [self.limit])
            else:
                cursor.execute('SELECT log_id FROM logs where is_processed = 0 and was_error = 0 LIMIT ?;', [self.limit])
            data = cursor.fetchall()
            results = [x[0] for x in data]

        return results
