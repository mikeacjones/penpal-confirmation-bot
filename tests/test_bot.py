import main
from betamax_helpers import BOT, RECORDER


def test_init():
    with RECORDER.use_cassette("test_init"):
        BOT.init()


def test_load_settings():
    with RECORDER.use_cassette("test_load_settings"):
        BOT.load_settings()


def test_post_monthly_submission():
    with RECORDER.use_cassette("test_post_monthly_submission"):
        new_submission = BOT.post_monthly_submission()
    with RECORDER.use_cassette("test_lock_previous_submissions"):
        BOT.lock_previous_submissions(new_submission)


def test_send_message_to_mods():
    with RECORDER.use_cassette("test_send_message_to_mods"):
        BOT.send_message_to_mods("Test", "This is a test!")


def test_hande_catch_up():
    main.BOT = BOT
    with RECORDER.use_cassette("test_handle_catchup"):
        main.handle_catch_up()


def test_monitor_comments():
    main.BOT = BOT
    with RECORDER.use_cassette("monitor_comments"):
        main.monitor_comments()


def test_monitor_mail():
    main.BOT = BOT
    with RECORDER.use_cassette("monitor_mail"):
        main.monitor_mail()
