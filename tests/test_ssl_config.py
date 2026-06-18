import os
from web.config import get_ssl_verify


def test_ssl_verify_defaults_false(monkeypatch):
    """EXECOS_SSL_VERIFY not set → verify=False (safe default for corporate proxies)."""
    monkeypatch.delenv("EXECOS_SSL_VERIFY", raising=False)
    assert get_ssl_verify() is False


def test_ssl_verify_true_when_env_set(monkeypatch):
    """EXECOS_SSL_VERIFY=true → verify=True."""
    monkeypatch.setenv("EXECOS_SSL_VERIFY", "true")
    assert get_ssl_verify() is True


def test_ssl_verify_false_for_any_non_true_value(monkeypatch):
    """EXECOS_SSL_VERIFY=yes does NOT enable verification — only 'true' does."""
    monkeypatch.setenv("EXECOS_SSL_VERIFY", "yes")
    assert get_ssl_verify() is False
