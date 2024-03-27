""" from mock_bot import Bot
from mock_redditor import Redditor
from mock_comment import Comment
import main
from main import should_process_comment
from main import handle_confirmation_thread_comment
from main import handle_confirmation


# bot should reply to a normal comment left on the bot's monthly post
def test_should_process_comment_true(BOT):
    comment = Comment("thisisreallytricky")
    main.BOT = BOT
    assert should_process_comment(comment)


# bot should not reply to non-root comments
def test_should_process_comment_false(BOT):
    comment = Comment("thisisreallytricky", is_root=False)
    main.BOT = BOT
    assert not should_process_comment(comment)


# bot should not reply to comments if they aren't in reply to the Bot's monthly post
def test_should_process_comment_false2(BOT):
    comment = Comment("thisisreallytricky", link_author="blahblah")
    main.BOT = BOT
    assert not should_process_comment(comment)


# bot should not reply to comments which have been removed
def test_should_process_comment_false3(BOT):
    comment = Comment("thisisreallytricky", banned_by="digitalmayhap")
    main.BOT = BOT
    assert not should_process_comment(comment)


# bot should not reply to saved comments
def test_should_process_comment_false4(BOT):
    comment = Comment("thisisreallytricky", saved=True)
    main.BOT = BOT
    assert not should_process_comment(comment)


# bot should ignore its own comments
def test_should_process_comment_false5(BOT):
    comment = Comment("bot")
    main.BOT = BOT
    assert not should_process_comment(comment)


def test_handle_confirmation_ranged_ok(BOT):
    comment = Comment("bot")
    matches = ["thisisreallytricky", 5, 5]
    main.BOT = BOT
    result = handle_confirmation(comment, matches)
    assert (
        result
        == "> `u/thisisreallytricky` updated from ` Emails: 1 |  Letters: 1` to ` Emails: 6 |  Letters: 6`"
    )


def test_handle_confirmation_selfupdate(BOT):
    comment = Comment("thisisreallytricky")
    matches = ["thisisreallytricky", 5, 5]
    main.BOT = BOT
    result = handle_confirmation(comment, matches)
    assert result == BOT.CANT_UPDATE_YOURSELF


def test_handle_confirmation_failed(BOT):
    comment = Comment("bot")
    matches = ["thisisreallytricky", 9999, 9999]
    main.BOT = BOT
    result = handle_confirmation(comment, matches)
    assert result == BOT.FLAIR_UPDATE_FAILED.format(mentioned_name="thisisreallytricky")


def test_handle_confirmation_thread_comment_single_ok(BOT):
    comment = Comment("bot", "u/thisisreallytricky 5-5")
    main.BOT = BOT
    reply_body = handle_confirmation_thread_comment(comment)
    assert (
        reply_body
        == "\n\n> `u/thisisreallytricky` updated from ` Emails: 1 |  Letters: 1` to ` Emails: 6 |  Letters: 6`"
    )
"""
