from settings import Settings
from betamax import Betamax
from betamax_helpers import use_recorder
import main
from main import handle_catchup
from praw import Reddit


@use_recorder
def test_handle_catchup(recorder: Betamax, settings: Settings, bot: Reddit):
    main.SETTINGS = settings
    main.BOT = bot
    handle_catchup()
