"""Ядро AI-агента - мозговой центр системы."""

import asyncio
import json
import os
from typing import Any, Dict, List

from openai import (
    AsyncOpenAI,
    APIError,
    AuthenticationError,
    BadRequestError,
    PermissionDeniedError,
    RateLimitError,
)

from agent.browser_controller import BrowserController
from agent.page_analyzer import PageAnalyzer
from tools.tool_manager import ToolManager
from utils.logger import setup_logger


class AICore:
    """Основной класс AI-агента, управляющий циклом принятия решений."""

    def __init__(
        self,
        api_key: str,
        tool_manager: ToolManager,
        max_context_messages: int = 30,
    ):
        """
        Инициализирует ядро AI-агента.
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.tool_manager = tool_manager
        self.messages: List[Dict[str, Any]] = []
        self.logger = setup_logger("AICore")
        self.max_iterations = 50
        self.current_iteration = 0
        self.max_context_messages = max_context_messages

        # Загружаем системный промпт
        system_prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "prompts", "system_prompt.txt"
        )
        try:
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                self.system_prompt = f.read()
        except FileNotFoundError:
            self.system_prompt = (
                "Ты — автономный AI-агент, управляющий веб-браузером."
            )

    def _reset_and_start_new_task(self, user_prompt: str):
        """Очищает историю и начинает новую задачу."""
        self.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Цель: {user_prompt}"},
        ]
        self.logger.info(f"Начало выполнения задачи: {user_prompt}")

    async def run_agent_loop(
        self, user_prompt: str, browser_controller: BrowserController
    ) -> None:
        """
        Основной цикл работы агента.
        """
        self.current_iteration = 0
        self._reset_and_start_new_task(user_prompt)

        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            self.logger.info(f"Итерация {self.current_iteration}")

            try:
                # 1. Наблюдение: получить текущее состояние страницы
                if not browser_controller.page:
                    self.logger.error("Страница браузера не инициализирована")
                    break

                page_summary = await PageAnalyzer.get_page_summary(browser_controller.page)
                observation = (
                    f"Текущая страница:\n"
                    f"URL: {page_summary['url']}\n"
                    f"Заголовок: {page_summary['title']}\n"
                    f"Текстовая информация: {page_summary['text_preview'][:500]}...\n\n"
                    f"Интерактивные элементы на странице:\n{page_summary['simplified_dom']}"
                )
                self.messages.append({"role": "user", "content": observation})

                # 2. Мысль: отправить запрос к LLM
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=self.messages,
                    tools=self.tool_manager.get_tool_definitions(),
                    tool_choice="auto",
                )
                response_message = response.choices[0].message

                # Сохраняем ответ ассистента в историю СРАЗУ
                self.messages.append(response_message.model_dump())

                # 3. Действие: выполнить действие, выбранное LLM
                if response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name

                        try:
                            function_args = json.loads(tool_call.function.arguments)
                            self.logger.info(f"Выполнение инструмента: {function_name} с аргументами: {function_args}")
                            result = await self.tool_manager.call_tool(function_name, **function_args)
                        except json.JSONDecodeError as e:
                            self.logger.error(f"Ошибка парсинга JSON: {tool_call.function.arguments}")
                            result = f"Ошибка: невалидные аргументы JSON - {str(e)}"

                        self.logger.info(f"Результат выполнения: {result[:200]}...")

                        # Добавляем результат работы инструмента в историю
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": function_name,
                                "content": result,
                            }
                        )
                    await asyncio.sleep(1)  # Небольшая пауза
                else:
                    final_message = response_message.content or "Задача выполнена."
                    self.logger.info(f"Агент завершил работу: {final_message}")
                    print(f"\n{'=' * 60}\nАгент завершил работу:\n{final_message}\n{'=' * 60}\n")
                    break

            except BadRequestError:
                self.logger.warning("Обнаружена некорректная структура истории сообщений. Сбрасываю задачу.")
                print("⚠️ Произошла ошибка структуры сообщений. Начинаю задачу заново.")
                self._reset_and_start_new_task(user_prompt)
                continue
            except (AuthenticationError, PermissionDeniedError, RateLimitError, APIError) as e:
                error_message = f"Критическая ошибка API OpenAI: {str(e)}"
                self.logger.error(error_message)
                print(f"❌ {error_message}")
                break
            except Exception as e:
                self.logger.error(f"Ошибка в цикле агента: {str(e)}", exc_info=True)
                print(f"⚠️ Ошибка: {str(e)}. Продолжаю...")
                self.messages.append({"role": "user", "content": f"Произошла ошибка: {str(e)}"})

        if self.current_iteration >= self.max_iterations:
            self.logger.warning("Достигнуто максимальное количество итераций")
            print(f"\n⚠️ Достигнуто максимальное количество итераций ({self.max_iterations}). Работа агента остановлена.")
