import os
import json
import boto3
import praw_bot_wrapper
import praw
from helpers_flair import increment_flair
from helpers import sint, deEmojify
from settings import Settings
from logger import LOGGER


def load_secrets(subreddit_name):
    if os.getenv("DEV"):
        secrets = os.getenv("SECRETS")
    else:
        secrets_manager = boto3.client("secretsmanager")
        secrets_response = secrets_manager.get_secret_value(
            SecretId=f"penpal-confirmation-bot/{subreddit_name}"
        )
        secrets = secrets_response["SecretString"]
    return json.loads(secrets)


SUBREDDIT_NAME = os.environ["SUBREDDIT_NAME"]
SECRETS = load_secrets(SUBREDDIT_NAME)
BOT = praw_bot_wrapper.bot(
    SECRETS["REDDIT_CLIENT_ID"],
    SECRETS["REDDIT_CLIENT_SECRET"],
    SECRETS["REDDIT_USER_AGENT"],
    SECRETS["REDDIT_USERNAME"],
    SECRETS["REDDIT_PASSWORD"],
    outage_threshold=10,
)
SETTINGS = Settings(BOT, SUBREDDIT_NAME)


@praw_bot_wrapper.stream_handler(SETTINGS.SUBREDDIT.stream.comments)
def handle_confirmation_thread_comment(comment):
    """Handles a comment left on the confirmation thread."""
    if not (
        not comment.saved
        and not comment.removed
        and comment.link_author == SETTINGS.BOT_NAME
        and hasattr(comment, "author_fullname")
        and comment.author_fullname != SETTINGS.FULLNAME
        and comment.is_root
        and comment.banned_by is None
    ):
        return

    LOGGER.info("Processing new comment https://reddit.com%s", comment.permalink)
    all_matches = SETTINGS.CONFIRMATION_PATTERN.findall(comment.body)
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

    old_flair, new_flair = increment_flair(SETTINGS, mentioned_user, emails, letters)
    if not old_flair or not new_flair:
        return SETTINGS.FLAIR_UPDATE_FAILED.format(mentioned_name=mentioned_name)

    LOGGER.info("Updated %s to %s for %s", old_flair, new_flair, mentioned_name)
    return deEmojify(
        SETTINGS.CONFIRMATION_TEMPLATE.format(
            mentioned_name=mentioned_name, old_flair=old_flair, new_flair=new_flair
        )
    )


@praw_bot_wrapper.stream_handler(BOT.inbox.stream)
def handle_new_mail(message):
    """Monitors messages sent to the bot"""
    message.mark_read()
    if (
        not isinstance(message, praw.models.Message)
        or message.author not in SETTINGS.CURRENT_MODS
    ):
        return
    if "reload" in message.body.lower():
        LOGGER.info("Mod requested settings reload")
        SETTINGS.reload()
        message.reply("Successfully reloaded bot settings")
    message.mark_read()


@praw_bot_wrapper.outage_recovery_handler
def notify_mods_of_outage_recovery(started_at):
    # changed how we send the modmail so that it because an archivable message
    # mod discussions can't be archived which is annoying
    message = SETTINGS.SUBREDDIT.modmail.create(
        subject="Bot Recovered from Extended Outage",
        body=SETTINGS.OUTAGE_MESSAGE.format(
            started_at=started_at, subreddit_name=SUBREDDIT_NAME
        ),
        recipient=SETTINGS.ME,
    )


if __name__ == "__main__":
    praw_bot_wrapper.run()
