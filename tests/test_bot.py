from settings import Settings
from betamax import Betamax
from betamax_helpers import use_recorder
import main
from main import handle_catchup
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
    handle_catchup(datetime.now(timezone.utc))
