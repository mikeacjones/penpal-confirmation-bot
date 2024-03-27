from settings import Settings
from betamax import Betamax
from betamax_helpers import use_recorder
from helpers_flair import get_current_flair, increment_flair


@use_recorder
def test_get_current_flair(recorder: Betamax, settings: Settings):
    current_flair = get_current_flair(settings, "digitalmayhap")
    assert (
        current_flair["flair_text"]
        == "Snail Mail Volunteer - 📧 Emails: 6 | 📬 Letters: 6"
    )
    assert current_flair["flair_css_class"] == "846bff86-dfc8-11ee-9926-2ef1a20f02fd"


@use_recorder
def test_increment_flair_nonranged_good(recorder: Betamax, settings: Settings):
    (current_flair, new_flair) = increment_flair(settings, "digitalmayhap", 1, 1)
    assert current_flair == "Snail Mail Volunteer - 📧 Emails: 6 | 📬 Letters: 6"
    assert new_flair == "Snail Mail Volunteer - 📧 Emails: 7 | 📬 Letters: 7"


@use_recorder
def test_increment_flair_ranged_newuser(recorder: Betamax, settings: Settings):
    (current_flair, new_flair) = increment_flair(settings, "YarnSwapper", 1, 1)
    assert current_flair == "No Flair"
    assert new_flair == "📧 Emails: 1 | 📬 Letters: 1"


@use_recorder
def test_increment_flair_ranged_good(recorder: Betamax, settings: Settings):
    (current_flair, new_flair) = increment_flair(settings, "YarnSwapper", 1, 1)
    assert current_flair == "📧 Emails: 1 | 📬 Letters: 1"
    assert new_flair == "📧 Emails: 2 | 📬 Letters: 2"
