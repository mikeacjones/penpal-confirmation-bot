import os
import sys
import logging
import re
from datetime import datetime, timedelta
import http.client
import urllib
import json
import praw
import prawcore.exceptions
import boto3
from types import SimpleNamespace



def load_secrets():
    if "DEV" not in os.environ:
        secrets_manager = boto3.client("secretsmanager")
        secrets = secrets_manager.get_secret_value(SecretId=f"penpal-confirmation-bot/{SUBREDDIT_NAME}")
        return json.loads(secrets["SecretString"])
    else:
        secrets = os.environ["SECRETS"]
        return json.loads(secrets)

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

def sint(str, default):
    try:
        return int(str)
    except ValueError:
        return default

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

SUBREDDIT_NAME = os.environ["SUBREDDIT_NAME"]
SECRETS = load_secrets()
FLAIR_PATTERN = re.compile(r"📧 Emails: (\d+|{E}) \| 📬 Letters: (\d+|{L})")
FLAIR_TEMPLATE_PATTERN = re.compile(r"((\d+)-(\d+):)📧 Emails: ({E}) \| 📬 Letters: ({L})")
SPECIAL_FLAIR_TEMPLATE_PATTERN = re.compile(r"📧 Emails: ({E}) \| 📬 Letters: ({L})")
CONFIRMATION_PATTERN = re.compile(r"u/([a-zA-Z0-9_-]{3,})\s+\\?-?\s*(\d+)(?:\s+|\s*-\s*)(\d+)")
MONTHLY_POST_FLAIR_ID = os.getenv("MONTHLY_POST_FLAIR_ID", None)
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

def load_template(template):
    """Loads a template either from local file or Reddit Wiki, returned as a string."""
    try:
        wiki = SUBREDDIT.wiki[f"confirmation-bot/{template}"]
        LOGGER.info("Loaded template %s from wiki", template)
        return wiki.content_md
    except (prawcore.exceptions.NotFound, prawcore.exceptions.Forbidden):
        with open(f"src/mdtemplates/{template}.md", "r", encoding="utf-8") as file:
            LOGGER.info("Loading template %s from src/mdtemplates/%s.md", template, template)
            return file.read()

def load_flair_templates():
    """Loads flair templates from Reddit, returned as a list."""
    templates = SUBREDDIT.flair.templates
    LOGGER.info("Loading flair templates")
    flair_templates = {}
    special_templates = []

    for template in templates:
        match = FLAIR_TEMPLATE_PATTERN.search(template["text"])
        if match:
            flair_templates[(sint(match.group(2), 0), sint(match.group(3), 0))] = {
                "id": template["id"],
                "template": template["text"],
                "mod_only": template["mod_only"],
            }
            LOGGER.info(
                "Loaded flair template with minimum of %s and maximum of %s",
                match.group(2),
                match.group(3),
            )
        else:
            special_match = SPECIAL_FLAIR_TEMPLATE_PATTERN.search(template["text"])
            if special_match:
                special_templates.append({ "id": template["id"], "template": template["text"] })
    return (flair_templates, special_templates)

def post_monthly_submission():
    """Creates the monthly confirmation thread."""
    previous_submission = get_current_confirmation_post()
    now = datetime.utcnow()
    if (previous_submission):
        submission_datetime = datetime.utcfromtimestamp(previous_submission.created_utc)
        is_same_month_year = submission_datetime.year == now.year and submission_datetime.month == now.month
        if is_same_month_year:
            LOGGER.info("Post monthly confirmation called and skipped; monthly post already exists")
            return

    monthly_post_template = load_template("monthly_post")
    monthly_post_title_template = load_template("monthly_post_title")
    send_pushover_message(f"Creating monthly post for r/{SUBREDDIT_NAME}")

    if previous_submission and previous_submission.stickied:
        previous_submission.mod.sticky(state=False)

    new_submission = SUBREDDIT.submit(
        title=now.strftime(monthly_post_title_template),
        selftext=monthly_post_template.format(
            bot_name=BOT_NAME,
            subreddit_name=SUBREDDIT_NAME,
            previous_month_submission=previous_submission or SimpleNamespace(**{ "title": "No Previous Confirmation Thread", "permalink": "" }),
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
    send_pushover_message(f"Locking previous month's posts for r/{SUBREDDIT_NAME}")
    for submission in BOT.submissions.new(limit=10):
        if submission.stickied:
            continue
        if not submission.locked:
            LOGGER.info("Locking https://reddit.com%s", submission.permalink)
            submission.mod.lock()

def should_process_comment(comment):
    """Checks if a comment should be processed, returns a boolean."""
    # Checks if we should actually process a comment in our stream loop
    # fmt: off
    return (
        not comment.saved
        and comment.is_root
        and comment.banned_by is None
        and comment.submission
        and should_process_redditor(comment.author)
    )

def should_process_redditor(redditor):
    """Checks if this is an author where we should process their comment/submission"""
    try:
        if redditor is None:
            return False

        if not hasattr(redditor, "id"):
            return False

        if redditor.id == BOT.id:
            return False

        if hasattr(redditor, "is_suspended"):
            return not redditor.is_suspended
        return True
    except prawcore.exceptions.NotFound:
        return False

def get_current_flair(redditor):
    """Uses an API call to ensure we have the latest flair text"""
    return next(SUBREDDIT.flair(redditor))

def get_flair_template(total_count, user):
    """Retrieves the appropriate flair template, returned as an object."""
    for (min_count, max_count), template in FLAIR_TEMPLATES.items():
        if min_count <= total_count <= max_count:
            # if a flair template was marked mod only, enforce that. Allows flairs like "Moderator | Trades min-max"
            if template["mod_only"] == (user in CURRENT_MODS):
                return template

    return None

def get_special_flair(current_flair_text, current_emails, current_letters):
    for template in SPECIAL_FLAIR_TEMPLATES:
        flair_text = template["template"].replace("{E}", current_emails).replace("{L}", current_letters)
        if flair_text == current_flair_text:
            return template
    return None

def get_current_confirmation_post():
    for submission in BOT.submissions.new(limit=5):
        if submission.subreddit.id == SUBREDDIT.id:
            if submission.stickied:
                return submission
    return None

def get_redditor(name):
    try:
        redditor = REDDIT.redditor(name)
        if redditor.id:
            return redditor
    except prawcore.exceptions.NotFound:
        return None
    return None

def increment_flair(redditor, new_emails, new_letters):
    current_flair = get_current_flair(redditor)
    current_flair_text = current_flair["flair_text"]
    if current_flair_text is None or current_flair_text == "":
        new_flair_obj = get_flair_template(new_emails + new_letters, redditor)
        return ("No Flair", set_flair(redditor, new_emails, new_letters, new_flair_obj))

    match = FLAIR_PATTERN.search(current_flair_text)
    if not match:
        return (None, None)
    
    current_emails = match.group(1)
    current_letters = match.group(2)
    new_emails += sint(current_emails, 0)
    new_letters += sint(current_letters, 0)
    new_total = new_emails + new_letters

    special_flair_obj = get_special_flair(current_flair_text, current_emails, current_letters)
    if special_flair_obj:
        return (current_flair_text, set_special_flair(redditor, new_emails, new_letters, special_flair_obj))
    new_flair_obj = get_flair_template(new_total, redditor)
    return (current_flair_text, set_flair(redditor,  new_emails,  new_letters, new_flair_obj))

def set_special_flair(redditor, emails, letters, flair_template_obj):
    flair_template = flair_template_obj["template"]
    if not flair_template:
        return
    
    match = SPECIAL_FLAIR_TEMPLATE_PATTERN.search(flair_template)
    if not match:
        return
    
    start_email, end_email = match.span(1)
    start_letters, end_letters = match.span(2)
    new_flair_text = flair_template[:start_email] + str(emails) + flair_template[end_email:start_letters] + str(letters) + flair_template[end_letters:]
    SUBREDDIT.flair.set(redditor, text=new_flair_text, flair_template_id=flair_template_obj["id"])
    return new_flair_text

def set_flair(redditor, emails, letters, flair_template_obj):
    flair_template = flair_template_obj["template"]
    if not flair_template:
        return
    
    match = FLAIR_TEMPLATE_PATTERN.search(flair_template)
    if not match:
        return

    start_range, end_range = match.span(1)
    start_email, end_email = match.span(4)
    start_letters, end_letters = match.span(5)
    new_flair_text = flair_template[:start_range] + flair_template[end_range:start_email] + str(emails) + flair_template[end_email:start_letters] + str(letters) + flair_template[end_letters:]
    SUBREDDIT.flair.set(redditor, text=new_flair_text, flair_template_id=flair_template_obj["id"])
    return new_flair_text

def handle_catch_up():
    current_submission = get_current_confirmation_post()
    current_submission.comment_sort = "new"
    current_submission.comments.replace_more(limit=None)
    LOGGER.info("Starting catch-up process")
    for comment in current_submission.comments.list():
        if comment.saved:
            continue
        handle_confirmation_thread_comment(comment)
    LOGGER.info("Catch-up process finished")

def handle_confirmation_thread_comment(comment):
    """Handles a comment left on the confirmation thread."""
    if not comment.is_root:
        comment.save()
        return

    all_matches = CONFIRMATION_PATTERN.findall(comment.body)
    if (not len(all_matches)):
        comment.save()
        return
    for match in all_matches:
        try:
            handle_confirmation(comment, match)
        except Exception as ex:
            LOGGER.info("Exception occurred while handling confirmation")
            LOGGER.info(ex)
    comment.save()

def handle_confirmation(comment, match):
    mentioned_name = match[0]
    emails = sint(match[1], 0)
    letters = sint(match[2], 0)
    mentioned_user = get_redditor(mentioned_name)

    if not mentioned_user:
        comment.reply(USER_DOESNT_EXIST.format(comment=comment, mentioned_name=mentioned_name))
        return
    
    if mentioned_user.id == comment.author.id:
        comment.reply(CANT_UPDATE_YOURSELF)
        return

    old_flair, new_flair = increment_flair(mentioned_user, emails, letters)
    if not old_flair or not new_flair:
        return
    
    comment.reply(CONFIRMATION_TEMPLATE.format(mentioned_name=mentioned_name, old_flair=old_flair, new_flair=new_flair))

def handle_non_confirmation_thread_comment(comment):
    """Handles a comment left outside the confirmation thread."""
    return

def monitor_comments():
    """Comment monitoring function; loops infinitely."""
    for comment in SUBREDDIT.stream.comments():
        if not should_process_comment(comment):
            continue

        LOGGER.info("Processing new comment https://reddit.com%s", comment.permalink)

        if comment.author.name.lower() == "automoderator":
            continue

        if comment.submission.author != BOT:
            handle_non_confirmation_thread_comment(comment)
            continue

        if comment.submission.author == BOT:
            handle_confirmation_thread_comment(comment)
            continue

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "create-monthly":
                post_monthly_submission()
                lock_previous_submissions()
        else:
            LOGGER.info("Bot start up")
            send_pushover_message(f"Bot startup for r/{SUBREDDIT_NAME}")

            CONFIRMATION_TEMPLATE = load_template("confirmation_message")
            OLD_CONFIRMATION_THREAD = load_template("old_confirmation_thread")
            USER_DOESNT_EXIST = load_template("user_doesnt_exist")
            CANT_UPDATE_YOURSELF = load_template("cant_update_yourself")
            FLAIR_TEMPLATES, SPECIAL_FLAIR_TEMPLATES = load_flair_templates()
            CURRENT_MODS = [str(mod) for mod in SUBREDDIT.moderator()]
            handle_catch_up()
            monitor_comments()
    except Exception as main_exception:
        LOGGER.exception("Main crashed")
        send_pushover_message(f"Bot error for r/{SUBREDDIT_NAME}")
        send_pushover_message(str(main_exception))
        raise