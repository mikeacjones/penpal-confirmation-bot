import prawcore


def get_redditor(bot, name):
    try:
        redditor = bot.redditor(name)
        if redditor.id:
            return redditor
    except prawcore.exceptions.NotFound:
        return None
    return None
