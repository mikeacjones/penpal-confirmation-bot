from praw import Reddit
from betamax import Betamax
from betamax_helpers import use_recorder
from helpers_redditor import get_redditor


@use_recorder
def test_get_redditor_good(recorder: Betamax, bot: Reddit):
    redditor = get_redditor(bot, "digitalmayhap")
    assert redditor != None


@use_recorder
def test_get_redditor_bad(recorder: Betamax, bot: Reddit):
    redditor = get_redditor(bot, "klasjflkajslkfjaklsjflkasklfdj")
    assert redditor == None
