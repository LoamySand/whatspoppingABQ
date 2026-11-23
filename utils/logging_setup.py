"""
Make the app's INFO logs visible under Prefect (WHAT-66).

Prefect configures logging when it is imported: the root logger is set to
WARNING, and the modules' own logging.basicConfig(level=logging.INFO) calls
then do nothing because the root logger already has a handler. The result
was that every collector INFO line ("Found N events", "Collected 1
measurement") was dropped, so a run that did nothing looked identical to a
run that never happened.

Setting the level on the app's top-level loggers lets their INFO records
through to Prefect's console handler. PREFECT_LOGGING_EXTRA_LOGGERS (set in
docker-compose.yml) additionally sends them to the flow run logs in the UI.
"""

import logging

APP_LOGGERS = ("collectors", "database", "flows", "scrapers", "utils")


def enable_app_logging(level: int = logging.INFO) -> None:
    """Set the app's top-level loggers to `level`. Safe to call more than once."""
    for name in APP_LOGGERS:
        logging.getLogger(name).setLevel(level)
