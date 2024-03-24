import prawcore
import re
from helpers import sint
from logger import LOGGER


class Settings:
    _instance = None

    def __new__(cls, bot, subreddit_name):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_settings(bot, subreddit_name)
        return cls._instance

    def reload(self, bot, subreddit_name):
        self._load_settings(bot, subreddit_name)

    def _load_settings(self, bot, subreddit_name):
        self.ME = bot.user.me()
        self.BOT_NAME = self.ME.name
        self.ID = self.ME.id
        self.FULLNAME = self.ME.fullname
        self.SUBREDDIT_NAME = subreddit_name
        self.SUBREDDIT = bot.subreddit(subreddit_name)
        self.OUTAGE_MESSAGE = self.load_template(self.SUBREDDIT, "outage_recovery")
        self.CONFIRMATION_PATTERN = re.compile(
            self.load_template(self.SUBREDDIT, "confirmation_regex_pattern")
        )
        self.FLAIR_PATTERN = re.compile(
            self.load_template(self.SUBREDDIT, "flair_regex")
        )
        self.FLAIR_TEMPLATE_PATTERN = re.compile(
            self.load_template(self.SUBREDDIT, "ranged_flair_template_regex")
        )
        self.SPECIAL_FLAIR_TEMPLATE_PATTERN = re.compile(
            self.load_template(self.SUBREDDIT, "special_flair_template_regex")
        )
        self.CONFIRMATION_TEMPLATE = self.load_template(
            self.SUBREDDIT, "confirmation_message"
        )
        self.USER_DOESNT_EXIST = self.load_template(self.SUBREDDIT, "user_doesnt_exist")
        self.CANT_UPDATE_YOURSELF = self.load_template(
            self.SUBREDDIT, "cant_update_yourself"
        )
        self.FLAIR_UPDATE_FAILED = self.load_template(
            self.SUBREDDIT, "flair_update_failed"
        )
        self.FLAIR_TEMPLATES, self.SPECIAL_FLAIR_TEMPLATES = self._load_flair_templates(
            self.SUBREDDIT
        )
        self.CURRENT_MODS = [str(mod) for mod in self.SUBREDDIT.moderator()]

    def load_template(self, subreddit, template):
        """Loads a template either from local file or Reddit Wiki, returned as a string."""
        try:
            wiki = subreddit.wiki[f"confirmation-bot/{template}"]
            return wiki.content_md
        except (prawcore.exceptions.NotFound, prawcore.exceptions.Forbidden):
            with open(f"src/mdtemplates/{template}.md", "r", encoding="utf-8") as file:
                return file.read()

    def _load_flair_templates(self, subreddit):
        """Loads flair templates from Reddit, returned as a list."""
        templates = subreddit.flair.templates
        flair_templates = {}
        special_templates = {}

        for template in templates:
            match = self.FLAIR_TEMPLATE_PATTERN.search(template["text"])
            if match:
                template["text"] = template["text"].replace(match.group(1), "")
                flair_templates[(sint(match.group(2), 0), sint(match.group(3), 0))] = (
                    template
                )
                LOGGER.info(
                    f"Loaded flair template with range {match.group(2)} to {match.group(3)}: {template["text"]}"
                )
            else:
                special_match = self.SPECIAL_FLAIR_TEMPLATE_PATTERN.search(
                    template["text"]
                )
                if special_match:
                    if template["css_class"] != template["id"]:
                        subreddit.flair.templates.update(
                            template["id"], css_class=template["id"]
                        )
                    special_templates[template["id"]] = template
                    LOGGER.info(
                        f"Loaded non-ranged flair template: {template["text"]}"
                    )
        return (flair_templates, special_templates)
