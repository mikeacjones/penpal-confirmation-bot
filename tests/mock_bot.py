import re
from mock_redditor import Redditor
import mock_redditor


class Bot:
    _instance = None

    def __new__(cls, SUBREDDIT_NAME):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialize(SUBREDDIT_NAME)
        return cls._instance

    def initialize(self, SUBREDDIT_NAME):
        self.configure_reddit(SUBREDDIT_NAME)

    def configure_reddit(self, SUBREDDIT_NAME):
        self.BOT_NAME = "bot"
        self.fullname = "bot"

    def load_settings(self):
        self.CONFIRMATION_PATTERN = re.compile(
            r"u/([a-zA-Z0-9_-]{3,})\s+\\?-?\s*(\d+)(?:\s+|\s*-\s*)(\d+)"
        )
        self.FLAIR_PATTERN = re.compile(
            r"📧 Emails: (\d+|{E}) \| 📬 Letters: (\d+|{L})"
        )
        self.FLAIR_TEMPLATE_PATTERN = re.compile(
            r"((\d+)-(\d+):)📧 Emails: {E} \| 📬 Letters: {L}"
        )
        self.SPECIAL_FLAIR_TEMPLATE_PATTERN = re.compile(
            r"📧 Emails: {E} \| 📬 Letters: {L}"
        )
        self.CONFIRMATION_TEMPLATE = (
            "> `u/{mentioned_name}` updated from `{old_flair}` to `{new_flair}`"
        )
        self.USER_DOESNT_EXIST = "> `u/{mentioned_name}` does not exist"
        self.CANT_UPDATE_YOURSELF = "> You can not update your own flair count!"
        self.FLAIR_UPDATE_FAILED = "> Unable to update flair for `u/{mentioned_name}` - please contact moderators."
        self.FLAIR_TEMPLATES = {
            (50, 99): {
                "text": "📧 Emails: {E} | 📬 Letters: {L}",
                "flair_css_class": "",
                "id": "98cfeab8-e078-11ee-ba66-4644512330f4",
                "mod_only": False,
            },
            (0, 49): {
                "text": "📧 Emails: {E} | 📬 Letters: {L}",
                "flair_css_class": "",
                "id": "8c84163a-e078-11ee-a1a5-1e44362b6d8e",
                "mod_only": False,
            },
            (0, 999999): {
                "text": "Moderator Ranged - 📧 Emails: {E} | 📬 Letters: {L}",
                "flair_css_class": "",
                "id": "8c84163a-e078-11ee-a1a5-1e44362b6d8e",
                "mod_only": True,
            },
        }
        self.SPECIAL_FLAIR_TEMPLATES = {
            "5c25c114-e078-11ee-8d9f-561af8fef755": {
                "text": "Snail Mail Volunteer - 📧 Emails: {E} | 📬 Letters: {L}",
                "flair_css_class": "5c25c114-e078-11ee-8d9f-561af8fef755",
                "id": "5c25c114-e078-11ee-8d9f-561af8fef755",
            },
            "6cbbe36e-e078-11ee-a579-fe45dae59718": {
                "text": "Moderator - 📧 Emails: {E} | 📬 Letters: {L}",
                "flair_css_class": "6cbbe36e-e078-11ee-a579-fe45dae59718",
                "id": "6cbbe36e-e078-11ee-a579-fe45dae59718",
            },
        }
        self.CURRENT_MODS = [
            "digitalmayhap",
            "othermod",
            "newmod",
        ]

    def get_current_flair(self, redditor):
        if isinstance(redditor, mock_redditor.Redditor):
            redditor = redditor.fullname
        match redditor:
            case "thisisreallytricky":
                return {
                    "flair_text": "📧 Emails: 1 | 📬 Letters: 1",
                    "flair_css_class": "",
                }
            case "digitalmayhap":
                return {
                    "flair_text": "Moderator - 📧 Emails: 1 | 📬 Letters: 1",
                    "flair_css_class": "6cbbe36e-e078-11ee-a579-fe45dae59718",
                }
            case "newuser":
                return {
                    "flair_text": "",
                    "flair_css_class": "",
                }
            case "othermod":
                return {
                    "flair_text": "Moderator Ranged - 📧 Emails: 1 | 📬 Letters: 1",
                    "flair_css_class": "",
                }
            case "snailmail":
                return {
                    "flair_text": "Snail Mail Volunteer - 📧 Emails: 1 | 📬 Letters: 1",
                    "flair_css_class": "5c25c114-e078-11ee-8d9f-561af8fef755",
                }
            case _:
                return None

    def set_redditor_flair(self, redditor, new_flair_text, flair_template_obj):
        return

    def get_redditor(self, name):
        if name not in [
            "thisisreallytricky",
            "digitalmayhap",
            "newuser",
            "othermod",
            "newmod",
            "snailmail",
        ]:
            return None
        return Redditor(name, name)
