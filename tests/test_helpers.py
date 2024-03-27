from helpers import sint, deEmojify, load_secrets


def test_sint_good():
    assert sint("5", 0) == 5


def test_sint_default():
    assert sint("blah", 0) == 0


def test_deEmojify():
    assert deEmojify("📧 Emails: 1 | 📬 Letters: 1") == " Emails: 1 |  Letters: 1"


def test_load_secrets():
    secrets = load_secrets("penpalbotdev")

    for secret in [
        "PUSHOVER_APP_TOKEN",
        "PUSHOVER_USER_TOKEN",
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USER_AGENT",
    ]:
        assert secret in secrets
