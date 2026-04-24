import os
from loguru import logger
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

import sys

def get_app_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Загружаем переменные окружения из папки с exe
env_path = os.path.join(get_app_dir(), ".env")
load_dotenv(dotenv_path=env_path)

class LLMPipeline:
    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        """
        Инициализация LangChain пайплайна с памятью.
        Используем gemini-2.5-flash: эта модель умнее версии lite, и у неё точно работает бесплатная квота (1500 запросов).
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key.startswith("AIzaSy..."):
            logger.error(f"Ключ GOOGLE_API_KEY не установлен или используется пример. Проверьте файл: {env_path}")
            raise ValueError(f"Ключ GOOGLE_API_KEY не найден в файле {env_path}")

        logger.debug(f"Инициализация LLM с моделью: {model_name}")
        self.llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.1)
        
        # Храним историю переписки (вопрос-ответ)
        self.history: list = []

    async def process_text(self, text: str) -> str:
        """
        Отправляет текст в Gemini. Имеет доступ к истории прошлых запросов,
        что позволяет понимать контекст "WA" или ошибок.
        """
        if not text.strip():
            return ""

        logger.info(f"Отправка запроса в Gemini. Длина текста: {len(text)} символов.")

        # Читаем шпаргалки пользователя из context.txt (если файл существует)
        extra_context = ""
        context_path = os.path.join(get_app_dir(), "context.txt")
        if os.path.exists(context_path):
            try:
                with open(context_path, "r", encoding="utf-8") as f:
                    extra_context = f.read().strip()
            except Exception as e:
                logger.error(f"Не удалось прочитать context.txt: {e}")

        # Системный промпт с новыми правилами
        sys_prompt = f"""Ты — студент, пишущий код на контесте по алгоритмам.
У тебя ЕСТЬ память контекста — ты помнишь условие задачи и свой предыдущий код.
Пользователь присылает текст задачи или ошибку (например, "WA", "Wrong Answer", "TL").
Если пришла ошибка — проанализируй свой прошлый код, найди баг и напиши НОВЫЙ код.
Твоя цель — выдать ТОЛЬКО чистый, рабочий код на Python 3. Никаких Markdown-блоков (```), никаких пояснений. Сразу код.

СТРОГИЕ ПРАВИЛА ОФОРМЛЕНИЯ КОДА:
1. Ввод-вывод: ИСПОЛЬЗУЙ ТОЛЬКО СТАНДАРТНЫЙ `input()` и `print()`. ЗАПРЕЩЕНО использовать `sys.stdin`, `sys.stdout`. ЗАПРЕЩЕНО писать кастомные функции ввода.
2. Имена переменных: мега-простые. Используй a, b, c, d, st, end, mx, q, mn, t, temp, n, s, i, j, k, x, y, res, ans, arr. Стандартные короткие названия классов.
3. Пустые строки: ЗАПРЕЩЕНЫ. В коде вообще не должно быть пустых строк (newline). Пиши код максимально плотно.
4. Комментарии: ЗАПРЕЩЕНЫ при любых условиях. В коде не должно быть ни одного комментария, ни #, ни docstring.
5. Не используй if __name__ == "__main__":. Просто пиши код с начала файла или вызывай solve() в конце.

Шпаргалки алгоритмов (при необходимости адаптируй их под новые правила):
{extra_context if extra_context else 'Нет дополнительных примеров.'}
"""

        messages = [SystemMessage(content=sys_prompt)] + self.history + [HumanMessage(content=text)]

        import asyncio
        from langchain_core.output_parsers import StrOutputParser
        
        chain = self.llm | StrOutputParser()
        
        max_retries = 3
        retry_delay = 2.0

        for attempt in range(1, max_retries + 1):
            try:
                answer = await chain.ainvoke(messages)
                answer = answer.strip()
    
                # Жестко удаляем Markdown-блоки, если Gemini всё равно их добавил
                if answer.startswith("```"):
                    lines = answer.split("\n")
                    if len(lines) > 1 and lines[0].startswith("```"):
                        lines = lines[1:]
                    if len(lines) > 0 and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    answer = "\n".join(lines).strip()
    
                logger.info("Ответ от Gemini успешно получен.")
                logger.debug(f"Длина ответа: {len(answer)} символов.")
                
                # Сохраняем этот диалог в память
                self.history.append(HumanMessage(content=text))
                self.history.append(AIMessage(content=answer))
                
                # Храним только последние 8 сообщений (4 пары вопрос-ответ), чтобы не сойти с ума
                if len(self.history) > 8:
                    self.history = self.history[-8:]
    
                return answer
    
            except Exception as e:
                logger.error(f"Попытка {attempt}/{max_retries} не удалась. Ошибка: {e}")
                if attempt < max_retries and ("503" in str(e) or "429" in str(e) or "UNAVAILABLE" in str(e)):
                    logger.info(f"Сервера Google перегружены. Ждем {retry_delay} сек перед повторной попыткой...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Экспоненциальный бэкофф
                else:
                    if attempt == max_retries:
                        logger.error("Все попытки исчерпаны. Google API перегружен. Попробуй позже.")
                    return ""
