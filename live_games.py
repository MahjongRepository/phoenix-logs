import json
import os
import re
import socket
import sqlite3
from distutils.dir_util import mkpath
from time import sleep

import pytz
from datetime import datetime

import requests

TENHOU_WG_URL = "https://mjv.jp/0/wg/0.js"


current_directory = os.path.dirname(os.path.realpath(__file__))
db_folder = os.path.join(current_directory, "db")


def main():
    if not os.path.exists(db_folder):
        mkpath(db_folder)




if __name__ == "__main__":
    main()
