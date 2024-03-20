import sys
import pytest
from mock_bot import Bot

sys.path.append("src")


@pytest.fixture
def BOT():
    BOT = Bot("penpalbotdev")
    BOT.load_settings()
    return BOT
