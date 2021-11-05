import pytest
from album_club_bot.script import add

def test_add():
    assert add(1, 2) == 3