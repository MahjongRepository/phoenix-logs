import logging
import re
import socket
from time import sleep
from typing import List, Optional

from live_games.db import get_current_time

logger = logging.getLogger("watcher")


class GameWatcher:
    TENHOU_HOST = "160.16.213.80"
    TENHOU_PORT = 10080

    def watch_one_game(self, game_id):
        logger.debug(f"{game_id} Start watching")
        game_started = get_current_time()

        socket_obj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_obj.settimeout(1)
        socket_obj.connect((self.TENHOU_HOST, self.TENHOU_PORT))

        self._send_socket_message(socket_obj, '<HELO name="NoName" />')
        self._read_socket_messages(socket_obj)
        self._send_socket_message(socket_obj, f'<CHAT text="%2Fwg%20{game_id}" />')
        sleep(2)

        continue_watch = True
        game_log = []
        while continue_watch:
            messages = self._read_socket_messages(socket_obj)
            game_log.extend(messages)

            for message in messages:
                if "<GO type=" in message:
                    self._send_socket_message(socket_obj, "<GOK />")

                # we started to watch the game not from the start
                # in that case we don't want to save this log
                if "INITBYLOG" in message:
                    continue_watch = False
                    game_log = []
                    logger.debug(f"{game_id} Stop watching. Game started not from the beginning.")

                # game was ended
                if "owari=" in message:
                    continue_watch = False
                    logger.debug(f"{game_id} Stop watching. Game was finished.")

            sleep(15)
            self._send_socket_message(socket_obj, "<Z />")

        try:
            socket_obj.shutdown(socket.SHUT_RDWR)
            socket_obj.close()
        except Exception:
            pass

        log_content = self.strip_log_content(game_log)
        return log_content, game_started

    def strip_log_content(self, original_log: List[str]) -> str:
        """
        We want to squash log content as much as possible, to be able store more logs.
        For that we will remove not needed tags, and we will remove not needed tag's attributes.
        """
        if not original_log:
            return ""

        result = ""
        for message in original_log:
            if message.startswith("<LN ") or message.startswith("<KANSEN "):
                continue

            if message.startswith("<GO "):
                game_type = self._get_attribute_content(message, "type")
                result += f'<GO type="{game_type}">'
                continue

            if message.startswith("<UN"):
                n0 = self._get_attribute_content(message, "n0")
                n1 = self._get_attribute_content(message, "n1")
                n2 = self._get_attribute_content(message, "n2")
                n3 = self._get_attribute_content(message, "n3")
                dan = self._get_attribute_content(message, "dan")
                rate = self._get_attribute_content(message, "rate")
                result += f'<UN n0="{n0}" n1="{n1}" n2="{n2}" n3="{n3}" dan="{dan}" rate="{rate}">'
                continue

            if message.startswith("<WGC"):
                regex = r"<WGC>(.*?)<\/WGC>"
                result += re.findall(regex, message)[0]
                continue

            # unhandled message
            result += message

        # remove delays indicators from log contnent
        regex = r">(.\d*?)<"
        result = re.sub(regex, "><", result)

        return result

    def _send_socket_message(self, socket_obj, message: str) -> None:
        message += "\0"
        socket_obj.sendall(message.encode())

    def _read_socket_messages(self, socket_obj) -> List[str]:
        try:
            result = socket_obj.recv(2048).decode("utf-8").split("\x00")[0:-1]
        except:
            result = []
        return result

    def _get_attribute_content(self, message: str, attribute_name: str) -> Optional[str]:
        result = re.findall(r'{}="([^"]*)"'.format(attribute_name), message)
        return result and result[0] or None
