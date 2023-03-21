import json
import logging
import os
import re
import threading
from time import sleep

import requests

from live_games.db import create_new_database, get_db_name, insert_log_record
from live_games.watcher import GameWatcher

logger = logging.getLogger("watcher")


class Watcher:
    TENHOU_WG_URL = "https://mjv.jp/0/wg/0.js"

    def __init__(self, db_folder):
        self.db_folder = db_folder

    def watch_games(self):
        added_game_ids = None

        while True:
            games = self.get_current_games(only_tokujou_games=True)
            loaded_game_ids = [x["game_id"] for x in games]

            # let's skip games that already in progress when we start the script
            # there are too many of them and tenhou closes so many connections
            if added_game_ids is None:
                added_game_ids = loaded_game_ids

            new_games = list(set(loaded_game_ids) - set(added_game_ids))
            added_game_ids = loaded_game_ids
            logger.debug(f"New games: {', '.join(new_games)}")

            for game_id in new_games:
                game = [x for x in games if x["game_id"] == game_id][0]

                db_path = self.init_db_and_get_db_path()
                threading.Thread(
                    target=lambda _game, _db_path: Watcher.run_one_game_watcher_and_save_results(
                        _game, _db_path
                    ),
                    args=([game, db_path]),
                ).start()

            sleep(60)

    @staticmethod
    def run_one_game_watcher_and_save_results(game, db_path):
        watcher = GameWatcher()
        game_id = game["game_id"]

        log_content, game_started = watcher.watch_one_game(game_id)
        if not log_content:
            return False

        insert_log_record(db_path, game, log_content, game_started)

        return True

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
            logger.error("Can't load current games", exc_info=e)

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
