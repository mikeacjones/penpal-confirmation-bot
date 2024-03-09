import os
import sys
import logging
import re
from datetime import datetime, timedelta
import http.client
import urllib
import json
import praw
from openai import OpenAIError
from openai import OpenAI
import prawcore.exceptions
import boto3


SUBREDDIT_NAME = os.environ["SUBREDDIT_NAME"]
SECRETS_MANAGER = boto3.client("secretsmanager")
SECRETS = SECRETS_MANAGER.get_secret_value(SecretId=f"penpal-confirmation-bot/{SUBREDDIT_NAME}")
SECRETS = json.loads(SECRETS["SecretString"])
FLAIR_PATTERN = re.compile(r" 📧 Emails: (\d+) | 📬 Letters: (\d+)")
FLAIR_TEMPLATE_PATTERN = re.compile(r"(\d+)-(\d+):📧 Emails: ({E}) | 📬 Letters: ({L})")
MONTHLY_POST_FLAIR_ID = os.getenv("MONTHLY_POST_FLAIR_ID", None)

def setup_custom_logger(name):
    """Set up the logger."""
    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler = logging.FileHandler("log.txt", mode="w")
    handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    loggr = logging.getLogger(name)
    loggr.setLevel(logging.INFO)
    loggr.addHandler(handler)
    loggr.addHandler(screen_handler)
    return loggr


LOGGER = setup_custom_logger("penpal-confirmation-bot")

REDDIT = praw.Reddit(
    client_id=SECRETS["REDDIT_CLIENT_ID"],
    client_secret=SECRETS["REDDIT_CLIENT_SECRET"],
    user_agent=SECRETS["REDDIT_USER_AGENT"],
    username=SECRETS["REDDIT_USERNAME"],
    password=SECRETS["REDDIT_PASSWORD"],
)

BOT = REDDIT.user.me()
BOT_NAME = BOT.name
SUBREDDIT = REDDIT.subreddit(SUBREDDIT_NAME)

def send_pushover_message(message):
    """Sends a pushover notification."""
    conn = http.client.HTTPSConnection("api.pushover.net:443")
    conn.request(
        "POST",
        "/1/messages.json",
        urllib.parse.urlencode(
            {
                "token": SECRETS["PUSHOVER_APP_TOKEN"],
                "user": SECRETS["PUSHOVER_USER_TOKEN"],
                "message": message,
            }
        ),
        {"Content-type": "application/x-www-form-urlencoded"},
    )
    conn.getresponse()

def load_template(template):
    """Loads a template either from local file or Reddit Wiki, returned as a string."""
    try:
        wiki = SUBREDDIT.wiki[f"trade-confirmation-bot/{template}"]
        LOGGER.info("Loaded template %s from wiki", template)
        return wiki.content_md
    except (prawcore.exceptions.NotFound, prawcore.exceptions.Forbidden):
        with open(f"src/mdtemplates/{template}.md", "r", encoding="utf-8") as file:
            LOGGER.info("Loading template %s from src/mdtemplates/%s.md", template, template)
            return file.read()


def post_monthly_submission():
    """Creates the monthly confirmation thread."""
    previous_submission = next(BOT.submissions.new(limit=1))
    submission_datetime = datetime.utcfromtimestamp(previous_submission.created_utc)
    now = datetime.utcnow()
    is_same_month_year = submission_datetime.year == now.year and submission_datetime.month == now.month
    if is_same_month_year:
        LOGGER.info("Post monthly confirmation called and skipped; monthly post already exists")
        return

    monthly_post_template = load_template("monthly_post")
    monthly_post_title_template = load_template("monthly_post_title")
    send_pushover_message(f"Creating monthly post for r/{SUBREDDIT_NAME}")

    if previous_submission.stickied:
        previous_submission.mod.sticky(state=False)

    new_submission = SUBREDDIT.submit(
        title=now.strftime(monthly_post_title_template),
        selftext=monthly_post_template.format(
            bot_name=BOT_NAME,
            subreddit_name=SUBREDDIT_NAME,
            previous_month_submission=previous_submission,
            now=now,
        ),
        flair_id=MONTHLY_POST_FLAIR_ID,
        send_replies=False,
    )
    new_submission.mod.sticky(bottom=False)
    new_submission.mod.suggested_sort(sort="new")
    LOGGER.info("Created new monthly confirmation post: https://reddit.com%s", new_submission.permalink)

def lock_previous_submissions():
    """Locks previous month posts."""
    LOGGER.info("Locking previous submissions")
    for submission in BOT.submissions.new(limit=10):
        if submission.stickied:
            continue
        if not submission.locked:
            LOGGER.info("Locking https://reddit.com%s", submission.permalink)
            submission.mod.lock()

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "create-monthly":
                post_monthly_submission()
                send_pushover_message(f"Locking previous month's posts for r/{SUBREDDIT_NAME}")
                lock_previous_submissions()
        else:
            LOGGER.info("Bot start up")
            send_pushover_message(f"Bot startup for r/{SUBREDDIT_NAME}")

            TRADE_CONFIRMATION_TEMPLATE = load_template("trade_confirmation")
            ALREADY_CONFIRMED_TEMPLATE = load_template("already_confirmed")
            CANT_CONFIRM_USERNAME_TEMPLATE = load_template("cant_confirm_username")
            NO_HISTORY_TEMPLATE = load_template("no_history")
            OLD_CONFIRMATION_THREAD = load_template("old_confirmation_thread")
            FLAIR_TEMPLATES = load_flair_templates()
            CURRENT_MODS = [str(mod) for mod in SUBREDDIT.moderator()]
            OPENAI_CLIENT = OpenAI(api_key=SECRETS["OPENAI_API_KEY"])
            handle_catch_up()
            monitor_comments()
    except Exception as main_exception:
        LOGGER.exception("Main crashed")
        send_pushover_message(f"Bot error for r/{SUBREDDIT_NAME}")
        send_pushover_message(str(main_exception))
        raise