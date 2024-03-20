import os
import sys
import json
import praw
import prawcore.exceptions
import boto3
import time
from types import SimpleNamespace
from datetime import datetime
from helpers import sint, deEmojify
from logger import LOGGER
from bot import Bot
from pushover import Pushover


def load_secrets():
    if os.getenv("DEV"):
        secrets = os.getenv("SECRETS")
    else:
        secrets_manager = boto3.client("secretsmanager")
        secrets_response = secrets_manager.get_secret_value(
            SecretId=f"penpal-confirmation-bot/{SUBREDDIT_NAME}"
        )
        secrets = secrets_response["SecretString"]
    return json.loads(secrets)


def post_monthly_submission():
    """Creates the monthly confirmation thread."""
    previous_submission = get_current_confirmation_post()
    now = datetime.utcnow()
    if previous_submission:
        submission_datetime = datetime.utcfromtimestamp(previous_submission.created_utc)
        is_same_month_year = (
            submission_datetime.year == now.year
            and submission_datetime.month == now.month
        )
        if is_same_month_year:
            LOGGER.info(
                "Post monthly confirmation called and skipped; monthly post already exists"
            )
            return

    monthly_post_flair_id = BOT.load_template("monthly_post_flair_id")
    monthly_post_template = BOT.load_template("monthly_post")
    monthly_post_title_template = BOT.load_template("monthly_post_title")
    PUSHOVER.send_message(f"Creating monthly post for r/{SUBREDDIT_NAME}")

    if previous_submission and previous_submission.stickied:
        previous_submission.mod.sticky(state=False)

    new_submission = BOT.SUBREDDIT.submit(
        title=now.strftime(monthly_post_title_template),
        selftext=monthly_post_template.format(
            bot_name=BOT.BOT_NAME,
            subreddit_name=SUBREDDIT_NAME,
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
    new_submission.mod.suggested_sort(sort="new")
    LOGGER.info(
        "Created new monthly confirmation post: https://reddit.com%s",
        new_submission.permalink,
    )


def lock_previous_submissions():
    """Locks previous month posts."""
    LOGGER.info("Locking previous submissions")
    PUSHOVER.send_message(f"Locking previous month's posts for r/{SUBREDDIT_NAME}")
    for submission in BOT.me.submissions.new(limit=10):
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
        and comment.author_fullname != BOT.fullname
        and comment.link_author == BOT.BOT_NAME
        and comment.is_root
        and comment.banned_by is None
    )


def get_flair_template(total_count, user):
    """Retrieves the appropriate flair template, returned as an object."""
    for (min_count, max_count), template in BOT.FLAIR_TEMPLATES.items():
        if min_count <= total_count <= max_count:
            # if a flair template was marked mod only, enforce that. Allows flairs like "Moderator | Trades min-max"
            if template["mod_only"] == (user in BOT.CURRENT_MODS):
                return template

    return None


def get_current_confirmation_post():
    for submission in BOT.me.submissions.new(limit=5):
        if submission.subreddit.id == BOT.SUBREDDIT.id:
            if submission.stickied:
                return submission
    return None


def increment_flair(redditor, new_emails, new_letters):
    current_flair = BOT.get_current_flair(redditor)
    current_flair_text = current_flair["flair_text"] if current_flair else None
    if current_flair_text is None or current_flair_text == "":
        current_flair_text = "No Flair"
        new_total = new_emails + new_letters
    else:
        match = BOT.FLAIR_PATTERN.search(current_flair_text)
        if not match:
            return (None, None)

        current_emails, current_letters = match.groups()
        new_emails += sint(current_emails, 0)
        new_letters += sint(current_letters, 0)
        new_total = new_emails + new_letters

    new_flair_text = ""
    if (
        current_flair
        and current_flair["flair_css_class"] in BOT.SPECIAL_FLAIR_TEMPLATES
    ):
        flair_template_obj = BOT.SPECIAL_FLAIR_TEMPLATES[
            current_flair["flair_css_class"]
        ]
        match = BOT.SPECIAL_FLAIR_TEMPLATE_PATTERN.search(flair_template_obj["text"])
        if not match:
            return (None, None)
        new_flair_text = get_new_flair_text(
            [match.span(1), match.span(2)],
            new_emails,
            new_letters,
            flair_template_obj["text"],
        )
    else:
        flair_template_obj = get_flair_template(new_total, redditor)
        if not flair_template_obj:
            return (None, None)
        match = BOT.FLAIR_TEMPLATE_PATTERN.search(flair_template_obj["text"])
        if not match:
            return (None, None)
        new_flair_text = get_new_flair_text(
            [match.span(1), match.span(4), match.span(5)],
            new_emails,
            new_letters,
            flair_template_obj["text"],
        )

    if new_flair_text == "":
        return (current_flair_text, None)

    BOT.set_redditor_flair(redditor, new_flair_text, flair_template_obj)
    return (
        current_flair_text,
        new_flair_text,
    )


def get_new_flair_text(ranges, emails, letters, flair_template_text):
    if len(ranges) < 3:
        ranges.insert(0, [0, 0])
    (start_range, end_range), (start_email, end_email), (start_letters, end_letters) = (
        ranges
    )

    new_flair_text = (
        flair_template_text[:start_range]
        + flair_template_text[end_range:start_email]
        + str(emails)
        + flair_template_text[end_email:start_letters]
        + str(letters)
        + flair_template_text[end_letters:]
    )
    return new_flair_text


def handle_catch_up():
    current_submission = get_current_confirmation_post()
    current_submission.comment_sort = "new"
    current_submission.comments.replace_more(limit=None)
    LOGGER.info("Starting catch-up process")
    for comment in current_submission.comments.list():
        if not comment.saved:
            handle_confirmation_thread_comment(comment)
    LOGGER.info("Catch-up process finished")


def handle_confirmation_thread_comment(comment):
    """Handles a comment left on the confirmation thread."""
    all_matches = BOT.CONFIRMATION_PATTERN.findall(comment.body)
    if not len(all_matches):
        comment.save()
        return

    reply_body = ""
    for match in all_matches:
        try:
            reply_body += "\n\n" + handle_confirmation(comment, match)
        except Exception as ex:
            LOGGER.info("Exception occurred while handling confirmation")
            LOGGER.info(ex)

    comment.save()
    if reply_body != "":
        comment.reply(reply_body)
    return reply_body


def handle_confirmation(comment, match):
    mentioned_name, emails, letters = match
    emails, letters = sint(emails, 0), sint(letters, 0)
    mentioned_user = BOT.get_redditor(mentioned_name)

    if not mentioned_user:
        return BOT.USER_DOESNT_EXIST.format(
            comment=comment, mentioned_name=mentioned_name
        )

    if mentioned_user.fullname == comment.author_fullname:
        return BOT.CANT_UPDATE_YOURSELF

    old_flair, new_flair = increment_flair(mentioned_user, emails, letters)
    if not old_flair or not new_flair:
        return BOT.FLAIR_UPDATE_FAILED.format(mentioned_name=mentioned_name)

    LOGGER.info("Updated %s to %s for %s", old_flair, new_flair, mentioned_name)
    return deEmojify(
        BOT.CONFIRMATION_TEMPLATE.format(
            mentioned_name=mentioned_name, old_flair=old_flair, new_flair=new_flair
        )
    )


def monitor_comments():
    """Comment monitoring function"""
    for comment in BOT.comment_stream:
        if comment is None:
            break

        if not should_process_comment(comment):
            continue

        LOGGER.info("Processing new comment https://reddit.com%s", comment.permalink)
        handle_confirmation_thread_comment(comment)


def monitor_mail():
    """Monitors messages sent to the bot"""
    for message in BOT.inbox_stream:
        if message is None:
            break
        if not isinstance(message, praw.models.Message):
            message.mark_read()
            continue
        if message.author not in BOT.CURRENT_MODS:
            message.mark_read()
            continue
        LOGGER.info("Received a private message from a mod")
        if not message.body or message.body == "":
            LOGGER.info("Mod message was empty")
            continue
        if "reload" in message.body.lower():
            LOGGER.info("Mod requested settings reload")
            BOT.load_settings()
            message.reply("Successfully reloaded bot settings")
        message.mark_read()
    return


if __name__ == "__main__":
    SUBREDDIT_NAME = os.getenv("SUBREDDIT_NAME")
    SECRETS = load_secrets()
    PUSHOVER = Pushover(SECRETS["PUSHOVER_APP_TOKEN"], SECRETS["PUSHOVER_USER_TOKEN"])
    BOT = Bot(SECRETS, SUBREDDIT_NAME)

    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "create-monthly":
                post_monthly_submission()
                lock_previous_submissions()
        else:
            LOGGER.info("Bot start up")
            BOT.load_settings()
            PUSHOVER.send_message(f"Bot startup for r/{SUBREDDIT_NAME}")

            handle_catch_up()

            # infinite loop checks each stream for new items
            error_count = 0
            while True:
                try:
                    monitor_comments()
                    monitor_mail()
                    error_count = 0
                except prawcore.exceptions.ServerError:
                    # when the reddit apis start misbehaving, we don't need to just crash the app
                    PUSHOVER.send_message(
                        f"Bot error for r/{os.getenv('SUBREDDIT_NAME', 'unknown')} - Server Error from Reddit APIs. Sleeping for 1 minute before trying again."
                    )
                    error_count += 1
                    time.sleep(
                        60 * min(error_count, 60)
                    )  # sleep for at most 1 hour if the errors keep repeating

    except Exception as main_exception:
        LOGGER.exception("Main crashed")
        PUSHOVER.send_message(
            f"Bot error for r/{os.getenv('SUBREDDIT_NAME', 'unknown')}"
        )
        PUSHOVER.send_message(str(main_exception))
        raise