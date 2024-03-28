import http.client
import urllib
from logger import LOGGER
from requests import Session


class Pushover:
    def __init__(self, APP_TOKEN, USER_TOKEN):
        self.APP_TOKEN = APP_TOKEN
        self.USER_TOKEN = USER_TOKEN
        self.SESSION = Session()
        self.SESSION.headers.update(
            {"Content-type": "application/x-www-form-urlencoded"}
        )

    def send_message(self, message):
        try:
            """Sends a pushover notification."""
            response = self.SESSION.post(
                "https://api.pushover.net/1/messages.json",
                data={
                    "token": self.APP_TOKEN,
                    "user": self.USER_TOKEN,
                    "message": message,
                },
            )
            return response
        except Exception as error:
            LOGGER.exception(error)
            return None
