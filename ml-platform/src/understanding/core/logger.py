import logging
from rich import console, logging as richLogging

class LoggerFactory:
    @staticmethod
    def create_logger(level) -> logging.Logger:
        recognized_level = level or logging.INFO
        handler = richLogging.RichHandler(console=console.Console(width=255), level=recognized_level, markup=True)
        formateur_de_log = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formateur_de_log)
        logger = logging.getLogger("main_prepare_data_logger")
        logger.addHandler(handler)
        logger.setLevel(recognized_level)
        return logger
