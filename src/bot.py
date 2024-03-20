import re
import praw
import prawcore
from logger import LOGGER
from helpers import sint


class Bot:
    _instance = None

    def __new__(cls, SECRETS, SUBREDDIT_NAME):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialize(SECRETS, SUBREDDIT_NAME)
        return cls._instance

    def initialize(self, SECRETS, SUBREDDIT_NAME):
        self.configure_reddit(SECRETS, SUBREDDIT_NAME)

    def configure_reddit(self, SECRETS, SUBREDDIT_NAME):
        self.REDDIT = praw.Reddit(
            client_id=SECRETS["REDDIT_CLIENT_ID"],
            client_secret=SECRETS["REDDIT_CLIENT_SECRET"],
            user_agent=SECRETS["REDDIT_USER_AGENT"],
            username=SECRETS["REDDIT_USERNAME"],
            password=SECRETS["REDDIT_PASSWORD"],
        )
        self.SUBREDDIT = self.REDDIT.subreddit(SUBREDDIT_NAME)
        self.me = self.REDDIT.user.me()
        self.id = self.me.id
        self.fullname = self.me.fullname
        self.inbox_stream = self.REDDIT.inbox.stream(pause_after=-1)
        self.comment_stream = self.SUBREDDIT.stream.comments(pause_after=-1)
        self.BOT_NAME = self.me.name

    def load_settings(self):
        self.CONFIRMATION_PATTERN = re.compile(
            self.load_template("confirmation_regex_pattern")
        )
        self.FLAIR_PATTERN = re.compile(self.load_template("flair_regex"))
        self.FLAIR_TEMPLATE_PATTERN = re.compile(
            self.load_template("ranged_flair_template_regex")
        )
        self.SPECIAL_FLAIR_TEMPLATE_PATTERN = re.compile(
            self.load_template("special_flair_template_regex")
        )
        self.CONFIRMATION_TEMPLATE = self.load_template("confirmation_message")
        self.USER_DOESNT_EXIST = self.load_template("user_doesnt_exist")
        self.CANT_UPDATE_YOURSELF = self.load_template("cant_update_yourself")
        self.FLAIR_UPDATE_FAILED = self.load_template("flair_update_failed")
        self.FLAIR_TEMPLATES, self.SPECIAL_FLAIR_TEMPLATES = self.load_flair_templates()
        self.CURRENT_MODS = [str(mod) for mod in self.SUBREDDIT.moderator()]

    def load_template(self, template):
        """Loads a template either from local file or Reddit Wiki, returned as a string."""
        try:
            wiki = self.SUBREDDIT.wiki[f"confirmation-bot/{template}"]
            LOGGER.info("Loaded template %s from wiki", template)
            return wiki.content_md
        except (prawcore.exceptions.NotFound, prawcore.exceptions.Forbidden):
            with open(f"src/mdtemplates/{template}.md", "r", encoding="utf-8") as file:
                LOGGER.info(
                    "Loading template %s from src/mdtemplates/%s.md", template, template
                )
                return file.read()

    def load_flair_templates(self):
        """Loads flair templates from Reddit, returned as a list."""
        templates = self.SUBREDDIT.flair.templates
        LOGGER.info("Loading flair templates")
        flair_templates = {}
        special_templates = {}

        for template in templates:
            match = self.FLAIR_TEMPLATE_PATTERN.search(template["text"])
            if match:
                flair_templates[(sint(match.group(2), 0), sint(match.group(3), 0))] = (
                    template
                )
                LOGGER.info(
                    "Loaded flair template with minimum of %s and maximum of %s",
                    match.group(2),
                    match.group(3),
                )
            else:
                special_match = self.SPECIAL_FLAIR_TEMPLATE_PATTERN.search(
                    template["text"]
                )
                if special_match:
                    if template["css_class"] != template["id"]:
                        self.SUBREDDIT.flair.templates.update(
                            template["id"], css_class=template["id"]
                        )
                    special_templates[template["id"]] = template
                    LOGGER.info(f"Loaded special flair template `{template['text']}`")
        return (flair_templates, special_templates)

    def set_redditor_flair(self, redditor, new_flair_text, flair_template):
        self.SUBREDDIT.flair.set(
            redditor, text=new_flair_text, flair_template_id=flair_template["id"]
        )

    def get_current_flair(self, redditor):
        """Uses an API call to ensure we have the latest flair text"""
        return next(self.SUBREDDIT.flair(redditor))

    def get_redditor(self, name):
        try:
            redditor = self.REDDIT.redditor(name)
            if redditor.id:
                return redditor
        except prawcore.exceptions.NotFound:
            return None
        return None
