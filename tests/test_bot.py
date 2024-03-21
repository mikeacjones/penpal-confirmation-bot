import os
from bot import Bot
import main
from main import load_secrets
from main import handle_catch_up
from betamax import Betamax
import betamax_helpers

secrets = load_secrets()
BOT = Bot(secrets, os.environ["SUBREDDIT_NAME"])
recorder = Betamax(BOT.REDDIT._core._requestor._http)


def test_load_settings():
    with recorder.use_cassette("test_load_settings"):
        BOT.load_settings()


def test_post_monthly_submission():
    with recorder.use_cassette("test_post_monthly_submission"):
        BOT.post_monthly_submission()
    with recorder.use_cassette("test_lock_previous_submissions"):
        BOT.lock_previous_submissions()


def test_send_message_to_mods():
    with recorder.use_cassette("test_send_message_to_mods"):
        BOT.send_message_to_mods("Test", "This is a test!")


def test_hande_catch_up():
    main.BOT = BOT
    with recorder.use_cassette("test_handle_catchup"):
        main.handle_catch_up()


def test_monitor_comments():
    main.BOT = BOT
    with recorder.use_cassette("monitor_comments"):
        main.monitor_comments()


def test_monitor_mail():
    main.BOT = BOT
    with recorder.use_cassette("monitor_mail"):
        main.monitor_mail()
