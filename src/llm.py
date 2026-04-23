import os
from loguru import logger
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# Загружаем переменные окружения (в т.ч. GOOGLE_API_KEY из .env)
load_dotenv()

class LLMPipeline:
    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        """
        Инициализация LangChain пайплайна с памятью.
        Используем gemini-2.5-flash: эта модель умнее версии lite, и у неё точно работает бесплатная квота (1500 запросов).
        """
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or api_key.startswith("AIzaSy..."):
            logger.error("Ключ GOOGLE_API_KEY не установлен или используется пример из .env.example")
            raise ValueError("Ключ GOOGLE_API_KEY не найден в файле .env")

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
        context_path = os.path.join(os.path.dirname(__file__), "..", "context.txt")
        if os.path.exists(context_path):
            try:
                with open(context_path, "r", encoding="utf-8") as f:
                    extra_context = f.read().strip()
            except Exception as e:
                logger.error(f"Не удалось прочитать context.txt: {e}")

        # Системный промпт с новыми правилами
        sys_prompt = f"""Ты скрытый AI-помощник для решения задач по программированию (олимпиады, Yandex Contest).
У тебя ЕСТЬ память контекста — ты помнишь условие задачи и свой предыдущий код.

СТРОГИЕ ПРАВИЛА:
1. Пользователь выделяет текст на экране. Это может быть условие задачи, кусок кода, или вердикт системы (например: "WA", "Wrong Answer", "TL", "Time Limit Exceeded", или текст ошибки компиляции).
2. Если пользователь прислал вердикт ошибки ("WA", "Осталось 100 попыток WA" и т.д.) — значит твое ПРОШЛОЕ решение оказалось неверным. Твоя задача: проанализировать свою ошибку, понять где баг, и написать НОВЫЙ, исправленный код.
3. Выдавай ТОЛЬКО КОД. Никаких Markdown-блоков (```python), никаких "Понял, вот исправленный вариант", никаких комментариев. Только чистый код для быстрой вставки.
4. Если пришел обычный текстовый вопрос — дай короткий ответ без лишней воды.

Дополнительные шпаргалки и алгоритмы от пользователя:
{extra_context if extra_context else 'Нет дополнительных примеров.'}
"""

        messages = [SystemMessage(content=sys_prompt)] + self.history + [HumanMessage(content=text)]

        try:
            from langchain_core.output_parsers import StrOutputParser
            chain = self.llm | StrOutputParser()
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
            logger.error(f"Ошибка при вызове Gemini: {e}")
            return ""
