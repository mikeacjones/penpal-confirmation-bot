import prawcore
from praw import models, Reddit


def get_redditor(bot: Reddit, name: str) -> models.Redditor | None:
    try:
        redditor = bot.redditor(name)
        if redditor.id:
            return redditor
    except prawcore.exceptions.NotFound:
        return None
