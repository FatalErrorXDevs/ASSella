"""Configure a reliable CA bundle for HTTPS clients.

PyInstaller does not guarantee that the host operating system's CA search
paths are available inside an AppImage.  certifi provides a portable Mozilla
bundle, while the environment variables keep urllib, requests, and other
OpenSSL consumers on the same trust store.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def configure_ssl_certificates() -> str | None:
    """Point Python HTTPS clients at certifi's bundled CA file when present."""
    try:
        import certifi

        bundle = certifi.where()
    except (ImportError, OSError) as exc:
        logger.debug("certifi CA bundle unavailable; using system trust store: %s", exc)
        return None

    if not bundle or not os.path.isfile(bundle):
        logger.warning("certifi returned a missing CA bundle path: %s", bundle)
        return None

    # Respect an explicitly supplied CA bundle (useful for enterprise proxies
    # and test environments), otherwise use the portable bundled certificate.
    os.environ.setdefault("SSL_CERT_FILE", bundle)
    os.environ.setdefault("REQUESTS_CA_BUNDLE", bundle)
    os.environ.setdefault("CURL_CA_BUNDLE", bundle)
    return bundle

