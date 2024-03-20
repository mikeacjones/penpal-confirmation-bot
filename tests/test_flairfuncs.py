from mock_bot import Bot
from mock_redditor import Redditor
import main
from main import get_new_flair_text
from main import increment_flair
from main import get_flair_template


def test_get_flair_template_nonmod_good(BOT):
    main.BOT = BOT
    template = get_flair_template(10, Redditor("thisisreallytricky"))
    assert template["id"] == "8c84163a-e078-11ee-a1a5-1e44362b6d8e"


def test_get_flair_template_nonmod_none(BOT):
    main.BOT = BOT
    template = get_flair_template(9999, Redditor("thisisreallytricky"))
    assert template == None


def test_get_flair_template_mod_good(BOT):
    main.BOT = BOT
    template = get_flair_template(20, Redditor("newmod"))
    assert template["id"] == "8c84163a-e078-11ee-a1a5-1e44362b6d8e"


def test_get_new_flair_text_special(BOT):
    template = "Snail Mail Volunteer - 📧 Emails: {E} | 📬 Letters: {L}"
    match = BOT.SPECIAL_FLAIR_TEMPLATE_PATTERN.search(template)

    assert (
        get_new_flair_text([match.span(1), match.span(2)], 5, 5, template)
        == "Snail Mail Volunteer - 📧 Emails: 5 | 📬 Letters: 5"
    )


def test_get_new_flair_text_ranged(BOT):
    template = "0-49:📧 Emails: {E} | 📬 Letters: {L}"
    match = BOT.FLAIR_TEMPLATE_PATTERN.search(template)

    assert (
        get_new_flair_text(
            [match.span(1), match.span(4), match.span(5)], 5, 5, template
        )
        == "📧 Emails: 5 | 📬 Letters: 5"
    )


def test_increment_flair_special(BOT):
    main.BOT = BOT
    current_flair = BOT.get_current_flair(Redditor("digitalmayhap"))
    (current_flair_text, new_flair_text) = increment_flair("digitalmayhap", 5, 5)

    assert current_flair_text == current_flair["flair_text"]
    assert new_flair_text == "Moderator - 📧 Emails: 6 | 📬 Letters: 6"


def test_increment_flair_ranged(BOT):
    main.BOT = BOT
    current_flair = BOT.get_current_flair(Redditor("thisisreallytricky"))
    (current_flair_text, new_flair_text) = increment_flair("thisisreallytricky", 5, 5)

    assert current_flair_text == current_flair["flair_text"]
    assert new_flair_text == "📧 Emails: 6 | 📬 Letters: 6"


def test_increment_flair_new_user(BOT):
    main.BOT = BOT
    (current_flair_text, new_flair_text) = increment_flair("newuser", 5, 5)
    assert current_flair_text == "No Flair"
    assert new_flair_text == "📧 Emails: 5 | 📬 Letters: 5"


def test_increment_flair_moderator_ranged(BOT):
    main.BOT = BOT
    current_flair = BOT.get_current_flair(Redditor("othermod"))
    (current_flair_text, new_flair_text) = increment_flair(Redditor("othermod"), 5, 5)

    assert current_flair_text == current_flair["flair_text"]
    assert new_flair_text == "Moderator Ranged - 📧 Emails: 6 | 📬 Letters: 6"


def test_increment_flair_new_moderator_ranged(BOT):
    main.BOT = BOT
    (current_flair_text, new_flair_text) = increment_flair(Redditor("newmod"), 5, 5)
    assert current_flair_text == "No Flair"
    assert new_flair_text == "Moderator Ranged - 📧 Emails: 5 | 📬 Letters: 5"
