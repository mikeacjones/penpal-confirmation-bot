from datetime import datetime, timezone
from logger import LOGGER
from types import SimpleNamespace


def get_current_confirmation_post(settings):
    for submission in settings.ME.submissions.new(limit=5):
        if submission.subreddit.id == settings.SUBREDDIT.id:
            if submission.stickied:
                return submission
    return None


def post_monthly_submission(settings):
    """Creates the monthly confirmation thread."""
    previous_submission = get_current_confirmation_post(settings)
    now = datetime.now(timezone.utc)
    if previous_submission:
        submission_datetime = datetime.fromtimestamp(
            previous_submission.created_utc, timezone.utc
        )
        is_same_month_year = (
            submission_datetime.year == now.year
            and submission_datetime.month == now.month
        )
        if is_same_month_year:
            LOGGER.info(
                "Post monthly confirmation called and skipped; monthly post already exists"
            )
            return

    monthly_post_flair_id = settings.load_template("monthly_post_flair_id")
    monthly_post_template = settings.load_template("monthly_post")
    monthly_post_title_template = settings.load_template("monthly_post_title")

    if previous_submission and previous_submission.stickied:
        previous_submission.mod.sticky(state=False)

    new_submission = settings.SUBREDDIT.submit(
        title=now.strftime(monthly_post_title_template),
        selftext=monthly_post_template.format(
            bot_name=settings.BOT_NAME,
            subreddit_name=settings.SUBREDDIT_NAME,
            previous_month_submission=previous_submission
            or SimpleNamespace(
                **{"title": "No Previous Confirmation Thread", "permalink": ""}
            ),
            now=now,
        ),
        flair_id=monthly_post_flair_id,
        send_replies=False,
    )
    new_submission.mod.sticky(bottom=False)
    new_submission.stickied = True
    new_submission.mod.suggested_sort(sort="new")
    return new_submission


def lock_previous_submissions(settings, exempt_submission):
    """Locks previous month posts."""
    LOGGER.info("Locking previous submissions")
    for submission in settings.ME.submissions.new(limit=10):
        if submission.subreddit_id != settings.SUBREDDIT.name:
            continue
        if submission == exempt_submission:
            continue
        if not submission.locked:
            LOGGER.info("Locking https://reddit.com%s", submission.permalink)
            submission.mod.lock()
