import os
from pushover import Pushover
from helpers import load_secrets


def test_send_message():
    secrets = load_secrets("penpalbotdev")
    pushover = Pushover(secrets["PUSHOVER_APP_TOKEN"], secrets["PUSHOVER_USER_TOKEN"])
    result = pushover.send_message(
        "Pushover unit test for reddit-penpal-confirmation-bot"
    )

    assert result.status == 200
