import sys
import pytest
import praw_bot_wrapper
import os
import base64
import urllib
from betamax import Betamax
from betamax_helpers import sanitize_cassette
from main import load_secrets

sys.path.append("src")
from settings import Settings

with Betamax.configure() as config:
    secrets = load_secrets()
    # Tell Betamax where to find the cassettes (recorded requests and responses)
    config.cassette_library_dir = "tests/cassettes"
    # Hide the OAuth2 credentials in recorded interactions
    config.before_record(callback=sanitize_cassette)
    config.define_cassette_placeholder(
        "<REDDIT-AUTH>",
        base64.b64encode(
            "{0}:{1}".format(
                secrets["REDDIT_USERNAME"], secrets["REDDIT_PASSWORD"]
            ).encode("utf-8")
        ).decode("utf-8"),
    )
    config.define_cassette_placeholder("<REDDIT-USERNAME>", secrets["REDDIT_USERNAME"])
    config.define_cassette_placeholder(
        "<REDDIT-PASSWORD>", urllib.parse.quote(secrets["REDDIT_PASSWORD"])
    )
    config.define_cassette_placeholder(
        "<REDDIT-CLIENT-ID>", secrets["REDDIT_CLIENT_ID"]
    )
    config.define_cassette_placeholder(
        "<REDDIT-CLIENT-SECRET>", secrets["REDDIT_CLIENT_SECRET"]
    )

secrets = load_secrets()
SUBREDDIT_NAME = os.environ["SUBREDDIT_NAME"]
BOT = praw_bot_wrapper.Bot(secrets, SUBREDDIT_NAME)
http = BOT.REDDIT._core._requestor._http
http.headers["Accept-Encoding"] = "identity"
RECORDER = Betamax(http)

with RECORDER.use_cassette("load_settings"):
    SETTINGS = Settings(BOT, SUBREDDIT_NAME)


@pytest.fixture
def SETTINGS():
    return SETTINGS
