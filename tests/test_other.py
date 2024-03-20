from main import load_secrets


def test_load_secrets():
    secrets = load_secrets()

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
