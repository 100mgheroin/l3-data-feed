import sys

from loguru import logger

LOG_FORMAT = (
    "[{time:YYYY-MM-DD HH:mm:ss.SSS}] "
    "<level>{level: ^8}</level> | " 
    "{name}:{function}:{line} - " 
    "<b>{message}</b>"
)

class LogConfig:
    _id: int | None = None

    def setup(self) -> None:
        logger.remove()

        self._id = logger.add(sys.stdout, level="INFO", format=LOG_FORMAT)

    def set_debug(self, enable: bool) -> None:
        if self._id is not None:
            logger.remove(self._id)

        if enable:
            self._id = logger.add(
                sys.stdout, level="DEBUG", format=LOG_FORMAT
            )
            logger.debug("Debug mode has been enabled.")
        else:
            self._id = logger.add(
                sys.stdout, level="INFO", format=LOG_FORMAT
            )
            logger.info("Debug mode has been disabled.")