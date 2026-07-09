import json
from utils.config import AppConfig


def test_config_roundtrip(tmp_path):
    cfg = AppConfig()
    cfg.load_test.url = "https://example.com"
    cfg.load_test.users = 25

    path = tmp_path / "config.json"
    cfg.save(str(path))

    loaded = AppConfig.from_file(str(path))
    assert loaded.load_test.url == "https://example.com"
    assert loaded.load_test.users == 25
