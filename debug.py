# -*- coding: utf-8 -*-
import os
import sqlite3
from optparse import OptionParser
from datetime import datetime

db_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'db')


def main():
    parser = OptionParser()
    parser.add_option('-y', '--year',
                      type='string',
                      default=str(datetime.now().year),
                      help='Target year')
    opts, _ = parser.parse_args()

    db_file = os.path.join(db_folder, '{}.db'.format(opts.year))
    connection = sqlite3.connect(db_file)

    with connection:
        cursor = connection.cursor()

        cursor.execute('SELECT COUNT(*) from logs;')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) from logs where is_processed = 1;')
        processed = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) from logs where was_error = 1;')
        with_errors = cursor.fetchone()[0]

        print('Total: {}'.format(total))
        print('Processed: {}'.format(processed))
        print('With errors: {}'.format(with_errors))

if __name__ == '__main__':
    main()
