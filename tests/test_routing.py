from alchemist.channels.gateway import Gateway
from alchemist.config import Config


class DummyProvider:
    pass


def make_gateway(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "workspace: {ws}\n"
        "channels:\n  telegram:\n    enabled: false\n".format(ws=tmp_path / "ws"),
        encoding="utf-8",
    )
    cfg = Config.load(str(cfg_file))
    from alchemist.workspace import Workspace

    gw = Gateway(cfg, DummyProvider(), Workspace(cfg.workspace))
    gw.mentions = {
        "scout": {"@scout", "@scout_bot", "scout"},
        "librarian": {"@librarian", "@lib_bot", "librarian"},
        "alchemist": {"@alchemist", "@alc_bot", "alchemist"},
        "publisher": {"@publisher", "@pub_bot", "publisher"},
    }
    return gw


def test_addressed_agent_detection(tmp_path):
    gw = make_gateway(tmp_path)
    assert gw._addressed_agent("@publisher write chapter 3") == "publisher"
    assert gw._addressed_agent("  @alchemist distill this") == "alchemist"
    assert gw._addressed_agent("random text no mention") == ""


def test_mentions_me(tmp_path):
    gw = make_gateway(tmp_path)
    assert gw._mentions_me("librarian", "hey @librarian organize this") is True
    assert gw._mentions_me("publisher", "hey @librarian organize this") is False


def test_strip_mentions(tmp_path):
    gw = make_gateway(tmp_path)
    assert gw._strip_mentions("@publisher write a chapter 3 draft") == "write a chapter 3 draft"
