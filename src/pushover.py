import http.client
import urllib


class Pushover:
    _instance = None

    def __new__(cls, APP_TOKEN, USER_TOKEN):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialize(APP_TOKEN, USER_TOKEN)
        return cls._instance

    def initialize(self, APP_TOKEN, USER_TOKEN):
        self.APP_TOKEN = APP_TOKEN
        self.USER_TOKEN = USER_TOKEN

    def send_message(self, message):
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
        conn.getresponse()
