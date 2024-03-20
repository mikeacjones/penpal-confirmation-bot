[![Pytest (main)](https://github.com/mikeacjones/reddit-penpal-confirmation-bot/actions/workflows/test-and-deploy.yml/badge.svg?branch=main)](https://github.com/mikeacjones/reddit-penpal-confirmation-bot/actions/workflows/test-and-deploy.yml) [![Coverage Status (main)](https://coveralls.io/repos/github/mikeacjones/reddit-penpal-confirmation-bot/badge.svg?branch=main&kill_cache=1)](https://coveralls.io/github/mikeacjones/reddit-penpal-confirmation-bot?branch=main)

# Pen Pal Confirmation Bot v1

## About

Source code for this bot can be found here: [https://github.com/mikeacjones/penpal-confirmation-bot](https://github.com/mikeacjones/penpal-confirmation-bot)

The Pen Pal Confirmation Bot v1 is a flair bot designed to automatically track and update the number of emails and letters users have exchanged. It does this by monitoring all top-level comments on its monthly Confirmation Post.

**Top Level Comment:** Defined as a comment that is directly responding to the post, not a reply to another comment.

The bot scans these comments for a specific pattern: a mention of another user followed by #-#, where the first number represents emails and the second represents letters. 

For instance, the comment `u/digitalmayhap - 1 - 2` would add 1 email and 2 letters to u/digitalmayhap's flair.

The current regular expression (regex) used for detection is: `u/([a-zA-Z0-9_-]{3,})\s+\\?-?\s*(\d+)(?:\s+|\s*-\s*)(\d+)`. This regex allows the bot to recognize various formats, such as:

- u/digitalmayhap - 1 - 2
- u/digitalmayhap - 1 2
- u/digitalmayhap 1 2
- u/digitalmayhap 1 - 2

To test this regex pattern, visit [https://regex101.com](https://regex101.com) and ensure the "flavor" is set to Python, matching the bot's coding language.

## Configuration

### Flair Templates

The bot supports two flair types: ranged and non-ranged. Ranged flairs are applied based on a specific total of emails and letters exchanged, while non-ranged flairs track counts without enforcing a range. Non-ranged flairs remain until manually updated.

A flair that doesn't fit these categories won't be modified by the bot, such as the `Bot` flair or any mod-specific flairs, e.g., `Bot Maintenance`.

#### Defining a Ranged Flair

For a ranged flair, use the format:

`MIN-MAX:📧 Emails: {E} | 📬 Letters: {L}`

Ranges are inclusive. For example, a 0-49 range applies until the count reaches 50, at which point a new flair is assigned. Arbitrary text and colors can be added, and a "mod only" flag is available for mod-exclusive flairs.

> If no ranged flair is defined which is flagged as "mod only", then moderators who wish to track their exchanges will need to utilize a non-ranged flair.

#### Defining a Non-Ranged Flair

Non-ranged flairs use the format:

`📧 Emails: {E} | 📬 Letters: {L}`

Additional text can precede or follow this template, like:

`Snail Mail Volunteer - 📧 Emails: {E} | 📬 Letters: {L}`

Non-ranged flairs need to be assigned manually. If you forget to replace the {E} and {L} with initial values, the bot will default these to 0 the first time someone confirms a change.

### Monthly Post

The bot schedules monthly posts in UTC. It must author these posts to track comments correctly.

#### Title

Edit the title via `confirmation-bot/monthly_post_title`. Incorporate the current date into the post title using the default format `%B %Y Confirmation Thread`, e.g., "March 2024 Confirmation Thread". For formatting details, see: [Python datetime formatting](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior). Any supported strftime variable can be used.

#### Content

Edit the post content via `confirmation-bot/monthly_post`. The content can be static or utilize variables for dynamic formatting.

Variables available for the monthly post content include:

- `bot_name`: The bot's username.
- `subreddit_name`: The subreddit's name.
- `previous_month_submission`: A [PRAW Submission](https://praw.readthedocs.io/en/latest/code_overview/models/submission.html) object from the previous month.
- `now`: Current date as a Python datetime object.

### Confirmation Reply Message

To update the reply message for successful confirmations, edit `confirmation-bot/confirmation_message`. The message can be static or include variables for customization.

Variables for the reply message:

- `mentioned_name`: The username of the mentioned user.
- `old_flair`: The mentioned user's current flair.
- `new_flair`: The mentioned user's updated flair.

### Can't Update Yourself

When a user attempts to change their own flair count, the bot replies with whatever static message is defined in the wiki page `confirmation-bot/cant_update_yourself`. No dynamic variables are available.

### User Doesn't Exist

If a user tags another user that does not exist, the bot replies with this message.

Edit the content of the reply via `confirmation-bot/user_doesnt_exist`. The content can be static or utilize variables for dynamic formatting.

Variables available for the comment include:

- `mentioned_name`: The name the user tagged.
