import logging
from logging.config import dictConfig


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def setup_logging(log_level: str) -> None:
    level = log_level.upper()

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id": {
                    "()": RequestIdFilter,
                }
            },
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s [request_id=%(request_id)s]"
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "level": level,
                    "formatter": "standard",
                    "filters": ["request_id"],
                    "stream": "ext://sys.stdout",
                }
            },
            "loggers": {
                "gridpilot": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": False,
                },
            },
            "root": {
                "handlers": ["default"],
                "level": level,
            },
        }
    )


logger = logging.getLogger("gridpilot.api")