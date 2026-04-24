import sys
from loguru import logger

def setup_logger() -> None:
    """
    Настраивает loguru для записи в файл и потокобезопасной работы (enqueue=True).
    """
    # Удаляем стандартный логгер (который пишет только в консоль по умолчанию)
    logger.remove()
    
    import os
    
    def get_app_dir() -> str:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    log_path = os.path.join(get_app_dir(), "app.log")
    
    # Настраиваем запись в файл app.log
    # enqueue=True гарантирует потокобезопасность при работе с asyncio и threading
    logger.add(
        log_path,
        rotation="5 MB",         # Ротация каждые 5 МБ
        retention="10 days",     # Хранить логи за последние 10 дней
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        enqueue=True,
        encoding="utf-8"
    )
    
    # Для удобства ручной отладки оставим вывод в консоль (если есть консоль)
    if sys.stderr is not None:
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            enqueue=True
        )
    
    logger.debug("Логгер успешно инициализирован.")
