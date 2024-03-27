from helpers_submission import post_monthly_submission, lock_previous_submissions
from betamax import Betamax
from settings import Settings


def test_monthly_submission(recorder: Betamax, settings: Settings):
    with recorder.use_cassette("test_monthly_submission"):
        new_submission = post_monthly_submission(settings)
        assert new_submission != None


def test_monthly_submission_exists(recorder: Betamax, settings: Settings):
    with recorder.use_cassette("test_monthly_submission_exists"):
        new_submission = post_monthly_submission(settings)
        assert new_submission == None


def test_lock_monthly_submissions(recorder: Betamax, settings: Settings):
    with recorder.use_cassette("test_lock_monthly_submissions"):
        lock_previous_submissions(settings)
