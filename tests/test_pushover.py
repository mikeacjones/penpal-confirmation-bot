from betamax import Betamax
from pushover import Pushover
from helpers import load_secrets


def test_send_pushover_message():
    secrets = load_secrets("penpalbotdev")
    pushover = Pushover(secrets["PUSHOVER_APP_TOKEN"], secrets["PUSHOVER_USER_TOKEN"])
    recorder = Betamax(pushover.SESSION)
    with recorder.use_cassette("test_send_pushover_message"):
        result = pushover.send_message(
            "Pushover unit test for reddit-penpal-confirmation-bot"
        )

    assert result.status_code == 200
