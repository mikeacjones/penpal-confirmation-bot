import http.client
import urllib
from logger import LOGGER


class Pushover:
    def __init__(self, APP_TOKEN, USER_TOKEN):
        self.APP_TOKEN = APP_TOKEN
        self.USER_TOKEN = USER_TOKEN

    def send_message(self, message):
        try:
            """Sends a pushover notification."""
            conn = http.client.HTTPSConnection("api.pushover.net:443")
            conn.request(
                "POST",
                "/1/messages.json",
                urllib.parse.urlencode(
                    {
                        "token": self.APP_TOKEN,
                        "user": self.USER_TOKEN,
                        "message": message,
                    }
                ),
                {"Content-type": "application/x-www-form-urlencoded"},
            )
            return conn.getresponse()
        except Exception as error:
            LOGGER.exception(error)
            return None
