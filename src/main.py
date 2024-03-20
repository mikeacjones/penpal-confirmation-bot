import os
import sys
import json
import praw
import prawcore
import praw.exceptions
import boto3
import time
from datetime import datetime, timezone
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


def should_process_comment(comment):
    """Checks if a comment should be processed, returns a boolean."""
    # Checks if we should actually process a comment in our stream loop
    # fmt: off
    return (
        not comment.saved
        and not comment.removed
        and comment.link_author == BOT.BOT_NAME
        and hasattr(comment, "author_fullname")
        and comment.author_fullname != BOT.fullname
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
    current_submission = BOT.get_current_confirmation_post()
    if not current_submission:
        return
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


def bot_loop():
    # infinite loop checks each stream for new items
    error_count = 0
    error_started = None

    while True:
        try:
            monitor_comments()
            monitor_mail()

            if error_count >= 10:
                PUSHOVER.send_message(
                    f"Bot recovered from extended outage that lasted for an hour or more for r/{os.getenv('SUBREDDIT_NAME', 'unknown')}\n\nOutage started at: `{error_started}`"
                )
                BOT.send_message_to_mods(
                    "Bot Recovered from Extended Outage",
                    f"Bot has recovered from extended outage that lasted for an hour or more for r/{os.getenv('SUBREDDIT_NAME', 'unknown')}\n\nOutage started at: `{error_started}`",
                )
            error_count = 0  # no exceptions, reset error count
            error_started = None
        except (
            praw.exceptions.PRAWException,
            prawcore.exceptions.PrawcoreException,
        ) as praw_error:
            # when the reddit apis start misbehaving, we don't need to just crash the app
            error_count += 1
            if error_count == 1:
                error_started = datetime.now(timezone.utc)
            if error_count % 2 == 0:
                BOT.reset_streams()  # the stream has to be reset when we're hitting exceptions because the listinggenerator has
                # internal exceptions that will cause it to stop trying to yield without throwing any issues. In testing have
                # found this happens after two exceptions on the two streams, so reset every 2 errors with the stream

            LOGGER.exception(praw_error)
            PUSHOVER.send_message(
                f"Bot error for r/{os.getenv('SUBREDDIT_NAME', 'unknown')} - Server Error from Reddit APIs. Sleeping for {60 * min(error_count, 60)} minute before trying again."
            )

        time.sleep(
            1 + (60 * min(error_count, 10))
        )  # sleep for at most 1 hour if the errors keep repeating
        # always sleep for at least 1 seconds between loops


if __name__ == "__main__":
    SUBREDDIT_NAME = os.getenv("SUBREDDIT_NAME", "Unknown")
    SECRETS = load_secrets()
    PUSHOVER = Pushover(SECRETS["PUSHOVER_APP_TOKEN"], SECRETS["PUSHOVER_USER_TOKEN"])
    BOT = Bot(SECRETS, SUBREDDIT_NAME)
    BOT.init()

    try:
        if len(sys.argv) > 1:
            if sys.argv[1] == "create-monthly":
                new_submission = BOT.post_monthly_submission()
                BOT.lock_previous_submissions(new_submission)

                LOGGER.info(f"New post: https://reddit.com{new_submission.permalink}")
                PUSHOVER.send_message(f"Created monthly post for r/{SUBREDDIT_NAME}")
        else:
            LOGGER.info("Bot start up")
            PUSHOVER.send_message(f"Bot startup for r/{SUBREDDIT_NAME}")

            BOT.load_settings()
            handle_catch_up()
            bot_loop()

    except Exception as main_exception:
        LOGGER.exception("Main crashed")
        PUSHOVER.send_message(f"Main Crash for r/{SUBREDDIT_NAME}")
        PUSHOVER.send_message(str(main_exception))
        raise
