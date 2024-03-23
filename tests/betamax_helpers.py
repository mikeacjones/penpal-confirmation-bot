from betamax.cassette import cassette
from betamax import Betamax
from main import load_secrets
from bot import Bot
import base64
import json
import urllib.parse
import os


def sanitize_cassette(interaction, current_cassette):
    # Exit early if the request did not return 200 OK because that's the
    # only time we want to look for Authorization-Token headers
    if interaction.data["response"]["status"]["code"] != 200:
        return

    body = interaction.data["response"]["body"]["string"]
    if "access_token" in body:
        body = json.loads(body)
        current_cassette.placeholders.append(
            cassette.Placeholder(
                placeholder=f"<ACCESS-TOKEN>", replace=body["access_token"]
            )
        )

    for headers in [
        interaction.data["request"]["headers"],
        interaction.data["response"]["headers"],
    ]:
        for restricted_header in ["Authorization", "Cookie", "Set-Cookie"]:
            header = headers.get(restricted_header)
            # If there was no token header in the response, exit
            if header is None:
                continue

            # Otherwise, create a new placeholder so that when cassette is saved,
            # Betamax will replace the token with our placeholder.
            for value in header:
                current_cassette.placeholders.append(
                    cassette.Placeholder(
                        placeholder=f"<{restricted_header}>", replace=value
                    )
                )


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

BOT = Bot(secrets, os.environ["SUBREDDIT_NAME"])
http = BOT.REDDIT._core._requestor._http
http.headers["Accept-Encoding"] = "identity"
RECORDER = Betamax(http)
