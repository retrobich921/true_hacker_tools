import sys
from loguru import logger

def setup_logger() -> None:
    """
    Настраивает loguru для записи в файл и потокобезопасной работы (enqueue=True).
    """
    # Удаляем стандартный логгер (который пишет только в консоль по умолчанию)
    logger.remove()
    
    # Настраиваем запись в файл app.log
    # enqueue=True гарантирует потокобезопасность при работе с asyncio и threading
    logger.add(
        "app.log",
        rotation="5 MB",         # Ротация каждые 5 МБ
        retention="10 days",     # Хранить логи за последние 10 дней
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,
        encoding="utf-8"
    )
    
    # Для удобства ручной отладки оставим вывод в консоль (если запускать через терминал)
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        enqueue=True
    )
    
    logger.debug("Логгер успешно инициализирован.")
