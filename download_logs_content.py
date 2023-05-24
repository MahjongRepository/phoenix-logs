"""
Script will load log ids from the database and will download log content
"""
import gzip
import re
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
    db_file = ""
    limit = 0
    threads = 0
    strip_logs = False

    shuffle_regex = rb"<SHUFFLE[^>]*>"

    def __init__(self, db_file, limit, threads, strip_logs):
        """
        :param db_file: db with loaded log ids
        """
        self.db_file = db_file
        self.limit = limit
        self.threads = threads
        self.strip_logs = strip_logs

    def process(self):
        start_time = datetime.now()
        print(f"Loading {self.limit} records")
        results = self.load_not_processed_logs()
        if not results:
            print("Nothing to download")
            return

        total_results = len(results)
        if total_results < self.limit:
            print("We have only {} records to download".format(total_results))
            self.limit = total_results

        # separate array to parts and download them simultaneously
        threads = []
        part = int(self.limit / self.threads)
        for x in range(0, self.threads):
            start = x * part
            if (x + 1) != self.threads:
                end = (x + 1) * part
            else:
                # we had to add all remaining items to the last thread
                # for example with limit=81, threads=4 results will be distributed:
                # 20 20 20 21
                end = self.limit

            threads.append(DownloadThread(self, results[start:end]))

        # let's start all threads
        for t in threads:
            t.start()

        # let's wait while all threads will be finished
        for t in threads:
            t.join()

        print("Worked time: {} seconds".format((datetime.now() - start_time).seconds))

    def download_logs(self, results):
        for log_id in results:
            print("Process {}".format(log_id))
            self.download_log_content(log_id)

    def download_log_content(self, log_id):
        """
        Download log content and store compressed version in the db
        """
        url = f"https://tenhou.net/0/log/?{log_id}"

        binary_content = None
        was_error = False
        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
                },
            )
            binary_content = response.content
            # it can be an error page
            if "mjlog" not in response.text:
                print("There is no log content in response")
                was_error = True
        except Exception as e:
            print(e)
            was_error = True

        if self.strip_logs:
            binary_content = self.strip_log_tags(binary_content)

        connection = sqlite3.connect(self.db_file)

        with connection:
            cursor = connection.cursor()

            compressed_content = ""
            if not was_error:
                try:
                    compressed_content = gzip.compress(binary_content)
                except Exception as e:
                    print(e)
                    print("Cant compress log content")
                    was_error = True

            cursor.execute(
                "UPDATE logs SET is_processed = ?, was_error = ?, log_content = ? WHERE log_id = ?;",
                [1, was_error and 1 or 0, compressed_content, log_id],
            )

    def strip_log_tags(self, log_content):
        # for now only strip shuffle seed
        return re.sub(self.shuffle_regex, b"", log_content)

    def load_not_processed_logs(self):
        connection = sqlite3.connect(self.db_file)

        with connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT log_id FROM logs where is_processed = 0 and was_error = 0 ORDER BY log_id LIMIT ?;",
                [self.limit],
            )
            data = cursor.fetchall()
            results = [x[0] for x in data]

        return results
