"""Runtime configuration read from environment variables."""
import os


def get_ssl_verify() -> bool:
    """Return True only when EXECOS_SSL_VERIFY=true is explicitly set.

    Defaults to False to support self-signed certs and corporate proxies.
    Set EXECOS_SSL_VERIFY=true in .env for production environments with valid certs.
    """
    return os.getenv("EXECOS_SSL_VERIFY", "false").strip().lower() == "true"
