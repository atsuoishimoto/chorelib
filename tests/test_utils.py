from shlex import quote

from chorelib import utils
from chorelib.utils import command, shell


def test_command(tmp_path):
    with utils.chdir(tmp_path):
        open("test file 1", "w").write("hello")
        output = command("cat", "test file 1", capture=True)
        assert output == "hello"


def test_shell(tmp_path):
    with utils.chdir(tmp_path):
        open("test file 1", "w").write("hello")
        output = shell("cat", quote("test file 1"), capture=True)
        assert output == "hello"
