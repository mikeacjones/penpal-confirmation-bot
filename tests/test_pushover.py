import os
from pushover import Pushover


def test_send_message():
    pushover = Pushover(
        os.getenv("PUSHOVER_APP_TOKEN", None), os.getenv("PUSHOVER_USER_TOKEN", None)
    )
    result = pushover.send_message(
        "Pushover unit test for reddit-penpal-confirmation-bot"
    )

    assert result.status == 200
