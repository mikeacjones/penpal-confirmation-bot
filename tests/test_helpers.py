from helpers import sint
from helpers import deEmojify


def test_sint_good():
    assert sint("5", 0) == 5


def test_sint_default():
    assert sint("blah", 0) == 0


def test_deEmojify():
    assert deEmojify("📧 Emails: 1 | 📬 Letters: 1") == " Emails: 1 |  Letters: 1"
