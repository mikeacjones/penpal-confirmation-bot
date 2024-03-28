import main
from helpers import load_secrets
from settings import Settings
from betamax import Betamax
from betamax_helpers import use_recorder
from pushover import Pushover
from main import handle_catchup, _should_process_comment
from praw import Reddit
from datetime import datetime, timezone


@use_recorder
def test_handle_catchup(recorder: Betamax, settings: Settings, bot: Reddit):
    main.SETTINGS = settings
    main.BOT = bot
    handle_catchup()


@use_recorder
def test_handle_catchup_with_outage(recorder: Betamax, settings: Settings, bot: Reddit):
    main.SETTINGS = settings
    main.BOT = bot
    secrets = load_secrets("penpalbotdev")
    pushover = Pushover(secrets["PUSHOVER_APP_TOKEN"], secrets["PUSHOVER_USER_TOKEN"])
    betamax = Betamax(pushover.SESSION)
    main.PUSHOVER = pushover
    with betamax.use_cassette("test_send_pushover_message_outage"):
        handle_catchup(datetime.now(timezone.utc))


@use_recorder
def test_should_process_comment_wrong_subreddit(recorder: Betamax, bot: Reddit):
    comment = bot.comment("kwu47cc")
    assert not _should_process_comment(comment)


@use_recorder
def test_should_process_comment_already_processed(recorder: Betamax, bot: Reddit):
    comment = bot.comment("kwv73qk")
    assert not _should_process_comment(comment)


@use_recorder
def test_should_process_comment_should_process(recorder: Betamax, bot: Reddit):
    comment = bot.comment("kwvw3r0")
    comment.link_author = comment.submission.author
    assert _should_process_comment(comment)
