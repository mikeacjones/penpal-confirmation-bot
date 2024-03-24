# from mock_bot import Bot
from mock_redditor import Redditor
import main
from helpers_flair import increment_flair, get_flair_template
from betamax_helpers import BOT, RECORDER

main.BOT = BOT


def test_get_flair_template_nonmod_good():
    with RECORDER.use_cassette("test_get_flair_template_nonmod_good"):
        redditor = BOT.get_redditor("thisisreallytricky")
        c_template = BOT.get_current_flair(redditor)
        template = get_flair_template(10, redditor, c_template)
        assert template["id"] == "2693db3e-dd90-11ee-99a0-e66a03397746"


def test_get_flair_template_nonmod_none():
    with RECORDER.use_cassette("test_get_flair_template_nonmod_none"):
        redditor = BOT.get_redditor("thisisreallytricky")
        c_template = BOT.get_current_flair(redditor)
        template = get_flair_template(9999, redditor, c_template)
        assert template == None


def test_get_flair_template_mod_good():
    with RECORDER.use_cassette("test_get_flair_template_mod_good"):
        redditor = BOT.get_redditor("PenPalConfirmationBo")
        c_template = BOT.get_current_flair(redditor)
        template = get_flair_template(20, redditor, c_template)
        assert template["id"] == "270a4e5c-dd92-11ee-b79f-fab5961d9741"


def test_get_flair_template_nonmod_fixed_good():
    with RECORDER.use_cassette("test_get_flair_template_nonmod_fixed_good"):
        redditor = BOT.get_redditor("digitalmayhap")
        c_template = BOT.get_current_flair(redditor)
        template = get_flair_template(10, redditor, c_template)
        assert template["id"] == "846bff86-dfc8-11ee-9926-2ef1a20f02fd"


def test_increment_flair_special():
    with RECORDER.use_cassette("test_increment_flair_special"):
        redditor = BOT.get_redditor("digitalmayhap")
        current_flair = BOT.get_current_flair(redditor)
        (current_flair_text, new_flair_text) = increment_flair(redditor, 5, 5)

        assert current_flair_text == current_flair["flair_text"]
        assert new_flair_text == "Snail Mail Volunteer - 📧 Emails: 6 | 📬 Letters: 6"


def test_increment_flair_ranged():
    with RECORDER.use_cassette("test_increment_flair_ranged"):
        redditor = BOT.get_redditor("thisisreallytricky")
        current_flair = BOT.get_current_flair(redditor)
        (current_flair_text, new_flair_text) = increment_flair(redditor, 5, 5)

        assert current_flair_text == current_flair["flair_text"]
        assert new_flair_text == "📧 Emails: 6 | 📬 Letters: 6"


def test_increment_flair_new_user():
    with RECORDER.use_cassette("test_increment_flair_new_user"):
        redditor = BOT.get_redditor("YarnSwapper")
        (current_flair_text, new_flair_text) = increment_flair(redditor, 5, 5)
        assert current_flair_text == "No Flair"
        assert new_flair_text == "📧 Emails: 5 | 📬 Letters: 5"


"""def test_increment_flair_moderator_ranged():
    with RECORDER.use_cassette("test_flairfuncs"):
        main.BOT = BOT
        current_flair = BOT.get_current_flair(Redditor("othermod"))
        (current_flair_text, new_flair_text) = increment_flair(
            Redditor("othermod"), 5, 5
        )

        assert current_flair_text == current_flair["flair_text"]
        assert new_flair_text == "Moderator Ranged - 📧 Emails: 6 | 📬 Letters: 6"


def test_increment_flair_new_moderator_ranged():
    with RECORDER.use_cassette("test_flairfuncs"):
        main.BOT = BOT
        (current_flair_text, new_flair_text) = increment_flair(Redditor("newmod"), 5, 5)
        assert current_flair_text == "No Flair"
        assert new_flair_text == "Moderator Ranged - 📧 Emails: 5 | 📬 Letters: 5"
        """
