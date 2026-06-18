import os
import importlib


def test_ssl_verify_defaults_false():
    """Default: EXECOS_SSL_VERIFY not set → verify=False (safe for corporate proxies)."""
    os.environ.pop("EXECOS_SSL_VERIFY", None)
    import web.config as cfg
    importlib.reload(cfg)
    assert cfg.get_ssl_verify() is False


def test_ssl_verify_true_when_env_set():
    """EXECOS_SSL_VERIFY=true → verify=True."""
    os.environ["EXECOS_SSL_VERIFY"] = "true"
    import web.config as cfg
    importlib.reload(cfg)
    assert cfg.get_ssl_verify() is True
    os.environ.pop("EXECOS_SSL_VERIFY", None)


def test_ssl_verify_false_for_any_non_true_value():
    """EXECOS_SSL_VERIFY=yes does NOT enable verification — only 'true' does."""
    os.environ["EXECOS_SSL_VERIFY"] = "yes"
    import web.config as cfg
    importlib.reload(cfg)
    assert cfg.get_ssl_verify() is False
    os.environ.pop("EXECOS_SSL_VERIFY", None)
