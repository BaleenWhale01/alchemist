import os

from alchemist.config import Config


def test_env_overrides_for_secrets(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "workspace: {ws}\n"
        "provider:\n  name: openrouter\n  model: m1\n"
        "channels:\n  telegram:\n    accounts:\n      scout: ''\n".format(ws=tmp_path / "ws"),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-from-env")
    monkeypatch.setenv("TELEGRAM_TOKEN_SCOUT", "tok-from-env")
    cfg = Config.load(str(cfg_file))
    assert cfg.provider.resolved_key() == "sk-from-env"
    assert cfg.telegram.token_for("scout") == "tok-from-env"


def test_per_agent_model_override(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "provider:\n  name: openrouter\n  model: base-model\n"
        "agents:\n  alchemist:\n    model: strong-model\n",
        encoding="utf-8",
    )
    cfg = Config.load(str(cfg_file))
    assert cfg.model_for("scout") == "base-model"
    assert cfg.model_for("alchemist") == "strong-model"
