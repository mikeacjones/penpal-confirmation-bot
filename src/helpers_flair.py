from praw_bot_wrapper import handle_praw_errors
from helpers import sint
from logger import LOGGER
from settings import Settings


def get_current_flair(settings, redditor):
    """Uses an API call to ensure we have the latest flair text"""
    return next(settings.SUBREDDIT.flair(redditor))


def get_flair_template(settings, total_count, user, current_flair):
    """Retrieves the appropriate flair template, returned as an object."""
    if (
        current_flair
        and current_flair["flair_css_class"] in settings["SPECIAL_FLAIR_TEMPLATES"]
    ):
        return settings["SPECIAL_FLAIR_TEMPLATES"][current_flair["flair_css_class"]]
    for (min_count, max_count), template in settings["FLAIR_TEMPLATES"].items():
        if min_count <= total_count <= max_count:
            # if a flair template was marked mod only, enforce that. Allows flairs like "Moderator | Trades min-max"
            if template["mod_only"] == (user in settings["CURRENT_MODS"]):
                return template

    return None


def increment_flair(settings, redditor, new_emails, new_letters):
    current_flair = get_current_flair(settings, redditor)
    current_flair_text = current_flair["flair_text"] if current_flair else None
    if current_flair_text is None or current_flair_text == "":
        current_flair_text = "No Flair"
        new_total = new_emails + new_letters
    else:
        match = settings.FLAIR_PATTERN.search(current_flair_text)
        if not match:
            return (None, None)

        current_emails, current_letters = match.groups()
        new_emails += sint(current_emails, 0)
        new_letters += sint(current_letters, 0)
        new_total = new_emails + new_letters

    new_flair_template = get_flair_template(
        settings, new_total, redditor, current_flair
    )
    if not new_flair_template:
        return (None, None)

    new_flair_text = new_flair_template["text"].format(E=new_emails, L=new_letters)
    set_redditor_flair(settings, redditor, new_flair_text, new_flair_template)
    return (current_flair_text, new_flair_text)


def set_redditor_flair(settings, redditor, new_flair_text, flair_template):
    settings.SUBREDDIT.flair.set(
        redditor, text=new_flair_text, flair_template_id=flair_template["id"]
    )
