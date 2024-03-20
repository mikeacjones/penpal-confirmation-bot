class Comment:
    def __init__(
        self,
        author_fullname,
        body="",
        is_root=True,
        banned_by=None,
        link_author="bot",
        saved=False,
    ):
        self.author_fullname = author_fullname
        self.body = body
        self.is_root = is_root
        self.banned_by = banned_by
        self.link_author = link_author
        self.saved = saved

    def reply(self, body):
        if not body or body == "":
            raise Exception("Comment reply body can't be empty")

    def save(self):
        self.saved = True
        return
