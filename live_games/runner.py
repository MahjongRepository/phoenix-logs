import json
import os
import re

import requests

from live_games.db import get_db_name, create_new_database
from live_games.watcher import GameWatcher


class WatcherRunner:
    TENHOU_WG_URL = "https://mjv.jp/0/wg/0.js"

    def __init__(self, db_folder):
        self.db_folder = db_folder

    def watch(self):
        watcher = GameWatcher()
        games = self.get_current_games(only_tokujou_games=True)

        for game in reversed(games):
            db_path = self.init_db_and_get_db_path()

            if game["game_id"] != "6453ADEB":
                continue

            result = watcher.watch_one_game(game["game_id"])

            break

    def init_db_and_get_db_path(self) -> str:
        db_path = os.path.join(self.db_folder, get_db_name())
        if not os.path.exists(db_path):
            create_new_database(db_path)
        return db_path

    def get_current_games(self, only_tokujou_games):
        games = []

        try:
            text = requests.get(self.TENHOU_WG_URL).text
            text = text.replace("\r\n", "")
            data = json.loads(re.match("sw\\((.*)\\);", text).group(1))

            for game in data:
                game_id, _, _, game_type, *_ = game.split(",")

                is_tokujou, is_tonpusen, is_sanma = self.parse_game_type(game_type)

                # skip it for now
                if is_sanma:
                    continue

                if only_tokujou_games and not is_tokujou:
                    continue

                games.append({"is_tonpusen": is_tonpusen, "game_id": game_id})

        except Exception as e:
            print(e)

        return games

    def parse_game_type(self, game_type):
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
