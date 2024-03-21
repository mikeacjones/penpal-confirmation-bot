import re
import praw
import prawcore
from datetime import datetime, timezone
from types import SimpleNamespace

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
        self.SUBREDDIT_NAME = SUBREDDIT_NAME
        self.REDDIT = praw.Reddit(
            client_id=SECRETS["REDDIT_CLIENT_ID"],
            client_secret=SECRETS["REDDIT_CLIENT_SECRET"],
            user_agent=SECRETS["REDDIT_USER_AGENT"],
            username=SECRETS["REDDIT_USERNAME"],
            password=SECRETS["REDDIT_PASSWORD"],
        )

    def init(self):
        self.SUBREDDIT = self.REDDIT.subreddit(self.SUBREDDIT_NAME)
        self.me = self.REDDIT.user.me()
        self.id = self.me.id
        self.fullname = self.me.fullname
        self.inbox_stream = self.REDDIT.inbox.stream(pause_after=-1)
        self.comment_stream = self.SUBREDDIT.stream.comments(pause_after=-1)
        self.BOT_NAME = self.me.name

    def reset_streams(self):
        self.inbox_stream = self.REDDIT.inbox.stream(pause_after=-1)
        self.comment_stream = self.SUBREDDIT.stream.comments(pause_after=-1)

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

    def get_current_confirmation_post(self):
        for submission in self.me.submissions.new(limit=5):
            if submission.subreddit.id == self.SUBREDDIT.id:
                if submission.stickied:
                    return submission
        return None

    def post_monthly_submission(self):
        """Creates the monthly confirmation thread."""
        previous_submission = self.get_current_confirmation_post()
        now = datetime.now(timezone.utc)
        if previous_submission:
            submission_datetime = datetime.fromtimestamp(
                previous_submission.created_utc, timezone.utc
            )
            is_same_month_year = (
                submission_datetime.year == now.year
                and submission_datetime.month == now.month
            )
            if is_same_month_year:
                LOGGER.info(
                    "Post monthly confirmation called and skipped; monthly post already exists"
                )
                return

        monthly_post_flair_id = self.load_template("monthly_post_flair_id")
        monthly_post_template = self.load_template("monthly_post")
        monthly_post_title_template = self.load_template("monthly_post_title")

        if previous_submission and previous_submission.stickied:
            previous_submission.mod.sticky(state=False)

        new_submission = self.SUBREDDIT.submit(
            title=now.strftime(monthly_post_title_template),
            selftext=monthly_post_template.format(
                bot_name=self.BOT_NAME,
                subreddit_name=self.SUBREDDIT_NAME,
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
        new_submission.stickied = True
        new_submission.mod.suggested_sort(sort="new")
        return new_submission

    def lock_previous_submissions(self, exempt_submission):
        """Locks previous month posts."""
        LOGGER.info("Locking previous submissions")
        for submission in self.me.submissions.new(limit=10):
            if submission == exempt_submission:
                continue
            if not submission.locked:
                LOGGER.info("Locking https://reddit.com%s", submission.permalink)
                submission.mod.lock()

    def send_message_to_mods(self, subject, message):
        # changed how we send the modmail so that it because an archivable message
        # mod discussions can't be archived which is annoying
        return self.SUBREDDIT.modmail.create(
            subject=subject, body=message, recipient=self.me
        )
