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
TENHOU_HOST = "160.16.213.80"
TENHOU_PORT = 10080

current_directory = os.path.dirname(os.path.realpath(__file__))
db_folder = os.path.join(current_directory, "db")


def main():
    if not os.path.exists(db_folder):
        mkpath(db_folder)

    db_path = os.path.join(db_folder, get_db_name())
    if not os.path.exists(db_path):
        set_up_database(db_path)

    games = get_current_games(only_tokujou_games=True)

    for game in reversed(games):
        # if not game["is_tonpusen"]:
        #     continue

        if game["game_id"] != "F91AC637":
            continue

        print(game["game_id"])
        watch_one_game(game["game_id"])

        break


def watch_one_game(game_id):
    socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socket_obj.connect((TENHOU_HOST, TENHOU_PORT))

    auth_token = ""
    _send_socket_message(socket_obj, '<HELO name="NoName" tid="f0" sx="M" />')
    messages = _read_socket_messages(socket_obj)
    for message in messages:
        if "HELO" in message:
            auth_token = _get_attribute_content(message, "auth")

    if not auth_token:
        print("Can't authenticate")
        return

    _send_socket_message(socket_obj, f'<AUTH val="{auth_token}"/>')
    _send_socket_message(socket_obj, "<Z />")
    _send_socket_message(socket_obj, '<PXR V="1" />')
    sleep(2)

    _send_socket_message(socket_obj, f'<CHAT text="%2Fwg%20{game_id}" />')
    sleep(1)

    continue_watch = True
    game_log = []
    print(get_current_time())
    while continue_watch:
        _send_socket_message(socket_obj, "<Z />")

        messages = _read_socket_messages(socket_obj)
        game_log.extend(messages)
        print(messages)

        for message in messages:
            if "<GO type=" in message:
                _send_socket_message(socket_obj, "<GOK />")

            # we started to watch the game not from the start
            # in that case we don't want to save this log
            if "INITBYLOG" in message:
                continue_watch = False
                game_log = []

            # game was ended
            if "owari=" in message:
                continue_watch = False

        print(get_current_time())
        sleep(15)

    socket_obj.shutdown(socket.SHUT_RDWR)
    socket_obj.close()

    print(json.dumps({"logs": game_log}))


def get_current_games(only_tokujou_games):
    games = []

    try:
        text = requests.get(TENHOU_WG_URL).text
        text = text.replace("\r\n", "")
        data = json.loads(re.match("sw\\((.*)\\);", text).group(1))

        for game in data:
            game_id, _, _, game_type, *_ = game.split(",")

            is_tokujou, is_tonpusen, is_sanma = parse_game_type(game_type)

            # skip it for now
            if is_sanma:
                continue

            if only_tokujou_games and not is_tokujou:
                continue

            games.append({"is_tonpusen": is_tonpusen, "game_id": game_id})

    except Exception as e:
        print(e)

    return games


def parse_game_type(game_type):
    # need to find a better way to do it
    rules = bin(int(game_type)).replace("0b", "")
    # add leading zeros
    if len(rules) < 8:
        while len(rules) != 8:
            rules = "0" + rules

    is_tonpusen = rules[4] == "0"
    is_sanma = rules[3] == "1"
    is_tokujou = rules[0] == "0" and rules[2] == "1"

    return is_tokujou, is_tonpusen, is_sanma


def get_db_name():
    current_time = get_current_time()
    db_name = f"live_{current_time.year}_{current_time.month:02d}.db"
    return db_name


def get_current_time():
    tz = pytz.timezone("Asia/Tokyo")
    return datetime.now(tz)


def set_up_database(db_path):
    print("Set up new database {}".format(db_path))
    connection = sqlite3.connect(db_path)

    with connection:
        cursor = connection.cursor()
        cursor.execute(
            """
                CREATE TABLE live_logs(
                    log_id text primary key,
                    date text,
                    is_tonpusen int,
                    is_completed int,
                    log_content text
                );
            """
        )
        cursor.execute("CREATE INDEX date ON live_logs (date);")
        cursor.execute("CREATE INDEX is_tonpusen_index ON live_logs (is_tonpusen);")
        cursor.execute("CREATE INDEX is_completed_index ON live_logs (is_completed);")


def _send_socket_message(socket_obj, message):
    message += "\0"
    socket_obj.sendall(message.encode())


def _read_socket_messages(socket_obj):
    return socket_obj.recv(2048).decode("utf-8").split("\x00")[0:-1]


def _get_attribute_content(message, attribute_name):
    result = re.findall(r'{}="([^"]*)"'.format(attribute_name), message)
    return result and result[0] or None


if __name__ == "__main__":
    main()
