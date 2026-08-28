"""PyInstaller runtime hook: configure CA certificates before app imports."""

from utils.ssl_config import configure_ssl_certificates

configure_ssl_certificates()

