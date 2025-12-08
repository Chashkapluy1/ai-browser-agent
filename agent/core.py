"""Ядро AI-агента - мозговой центр системы."""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from openai import RateLimitError, APIError, AuthenticationError

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

        Args:
            api_key: API ключ OpenAI.
            tool_manager: Менеджер инструментов для выполнения действий.
            max_context_messages: Максимальное количество сообщений в контексте.
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
                system_prompt = f.read()
        except FileNotFoundError:
            system_prompt = (
                "Ты — автономный AI-агент, управляющий веб-браузером. "
                "Анализируй страницу и используй доступные инструменты для достижения цели."
            )

        self.messages.append({"role": "system", "content": system_prompt})

    def _trim_context(self) -> None:
        """
        Обрезает контекстное окно, сохраняя системный промпт и начальную задачу.

        Использует стратегию скользящего окна: сохраняет системный промпт,
        первую задачу пользователя и последние N сообщений.
        """
        if len(self.messages) <= self.max_context_messages:
            return

        # Находим индексы системного промпта и первой задачи пользователя
        system_idx = None
        first_user_idx = None

        for i, msg in enumerate(self.messages):
            if msg.get("role") == "system" and system_idx is None:
                system_idx = i
            elif msg.get("role") == "user" and first_user_idx is None:
                first_user_idx = i
                if system_idx is not None:
                    break

        # Сохраняем системный промпт и первую задачу
        essential_messages = []
        if system_idx is not None:
            essential_messages.append(self.messages[system_idx])
        if first_user_idx is not None and first_user_idx != system_idx:
            essential_messages.append(self.messages[first_user_idx])

        # Берем последние N сообщений (исключая системные)
        recent_messages = [
            msg
            for msg in self.messages[first_user_idx + 1 :]
            if msg.get("role") != "system"
        ]

        # Объединяем: системный промпт + первая задача + последние сообщения
        keep_count = self.max_context_messages - len(essential_messages)
        if keep_count > 0:
            recent_messages = recent_messages[-keep_count:]
            self.messages = essential_messages + recent_messages
        else:
            self.messages = essential_messages

        self.logger.info(
            f"Контекст обрезан: {len(self.messages)} сообщений (максимум {self.max_context_messages})"
        )

    async def run_agent_loop(
        self, user_prompt: str, browser_controller: BrowserController
    ) -> None:
        """
        Основной цикл работы агента.

        Args:
            user_prompt: Задача от пользователя.
            browser_controller: Контроллер браузера для взаимодействия.
        """
        self.current_iteration = 0
        # Очищаем предыдущий контекст, оставляя только системный промпт
        self.messages = [msg for msg in self.messages if msg.get("role") == "system"]
        self.messages.append({"role": "user", "content": f"Цель: {user_prompt}"})
        self.logger.info(f"Начало выполнения задачи: {user_prompt}")

        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            self.logger.info(f"Итерация {self.current_iteration}")

            try:
                # Обрезаем контекст, если он слишком большой
                self._trim_context()

                # 1. Наблюдение: получить текущее состояние страницы
                if browser_controller.page is None:
                    self.logger.error("Страница браузера не инициализирована")
                    break

                # Оптимизированный вызов: получаем всю информацию за один раз
                page_summary = await PageAnalyzer.get_page_summary(browser_controller.page)
                
                # Используем simplified_dom из summary, если доступен, иначе получаем отдельно
                simplified_dom = page_summary.get("simplified_dom")
                if not simplified_dom:
                    simplified_dom = await PageAnalyzer.get_simplified_dom(browser_controller.page)

                observation = (
                    f"Текущая страница:\n"
                    f"URL: {page_summary['url']}\n"
                    f"Заголовок: {page_summary['title']}\n"
                    f"Текстовая информация: {page_summary['text_preview'][:500]}...\n\n"
                    f"Интерактивные элементы на странице:\n{simplified_dom}"
                )

                self.messages.append({"role": "user", "content": observation})

                # 2. Мысль: отправить запрос к LLM для получения следующего действия
                try:
                    response = await self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=self.messages,
                        tools=self.tool_manager.get_tool_definitions(),
                        tool_choice="auto",
                        temperature=0.7,
                    )
                except AuthenticationError as auth_error:
                    # Ошибка аутентификации - неверный API ключ
                    error_msg = (
                        "❌ Ошибка: Неверный API ключ OpenAI.\n"
                        "Проверьте правильность ключа в файле .env\n"
                        "Получить новый ключ можно на https://platform.openai.com/account/api-keys"
                    )
                    self.logger.error(error_msg)
                    print(f"\n{'='*60}")
                    print(error_msg)
                    print(f"{'='*60}\n")
                    break  # Останавливаем агента
                except RateLimitError as rate_error:
                    # Проверяем, является ли это ошибкой квоты (insufficient_quota)
                    error_body = getattr(rate_error, "body", {})
                    error_type = error_body.get("error", {}).get("type", "")
                    
                    if error_type == "insufficient_quota":
                        error_msg = (
                            "❌ Ошибка: Превышен лимит квоты OpenAI API.\n"
                            "У вас закончились средства или достигнут лимит использования.\n"
                            "Пожалуйста, пополните баланс на https://platform.openai.com/account/billing"
                        )
                        self.logger.error(error_msg)
                        print(f"\n{'='*60}")
                        print(error_msg)
                        print(f"{'='*60}\n")
                        break  # Останавливаем агента
                    else:
                        # Обычная ошибка rate limit - можно повторить попытку
                        error_msg = f"⚠️  Превышен лимит запросов. Повторная попытка..."
                        self.logger.warning(error_msg)
                        print(error_msg)
                        await asyncio.sleep(2)  # Небольшая задержка перед повтором
                        continue
                except APIError as api_error:
                    error_msg = f"Ошибка API OpenAI: {str(api_error)}"
                    self.logger.error(error_msg, exc_info=True)
                    self.messages.append({"role": "user", "content": error_msg})
                    print(f"⚠️  {error_msg}")
                    continue
                except Exception as api_error:
                    error_msg = f"Неожиданная ошибка: {str(api_error)}"
                    self.logger.error(error_msg, exc_info=True)
                    self.messages.append({"role": "user", "content": error_msg})
                    print(f"⚠️  {error_msg}")
                    continue

                response_message = response.choices[0].message

                # Добавляем ответ модели в историю
                if response_message.content:
                    self.logger.info(f"AI ответ: {response_message.content[:200]}...")
                    self.messages.append(
                        {
                            "role": "assistant",
                            "content": response_message.content,
                            "tool_calls": (
                                [
                                    {
                                        "id": tc.id,
                                        "type": tc.type,
                                        "function": {
                                            "name": tc.function.name,
                                            "arguments": tc.function.arguments,
                                        },
                                    }
                                    for tc in response_message.tool_calls or []
                                ]
                                if response_message.tool_calls
                                else None
                            ),
                        }
                    )

                # 3. Действие: выполнить действие, выбранное LLM
                if response_message.tool_calls:
                    tool_call = response_message.tool_calls[0]
                    function_name = tool_call.function.name
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        self.logger.error(
                            f"Ошибка парсинга аргументов инструмента: {tool_call.function.arguments}. "
                            f"Ошибка: {str(e)}"
                        )
                        # Сообщаем LLM об ошибке, чтобы она могла исправиться
                        error_msg = (
                            f"Ошибка: инструмент {function_name} получил невалидные аргументы JSON. "
                            f"Пожалуйста, проверь формат аргументов и попробуй снова."
                        )
                        self.messages.append({"role": "user", "content": error_msg})
                        continue

                    self.logger.info(
                        f"Выполнение инструмента: {function_name} с аргументами: {function_args}"
                    )

                    # Вызов инструмента и получение результата
                    result = await self.tool_manager.call_tool(function_name, **function_args)

                    # Добавляем результат в историю
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": result,
                        }
                    )

                    self.logger.info(f"Результат выполнения: {result[:200]}...")

                    # Небольшая задержка для стабилизации страницы
                    await browser_controller.page.wait_for_timeout(1000)

                else:
                    # Задача выполнена или требуется ввод пользователя
                    final_message = response_message.content or "Задача выполнена."
                    self.logger.info(f"Агент завершил работу: {final_message}")
                    print(f"\n{'='*60}")
                    print(f"Агент завершил работу:")
                    print(f"{final_message}")
                    print(f"{'='*60}\n")
                    break

            except Exception as e:
                self.logger.error(f"Ошибка в цикле агента: {str(e)}", exc_info=True)
                error_message = f"Произошла ошибка: {str(e)}. Продолжаю работу..."
                self.messages.append({"role": "user", "content": error_message})
                print(f"⚠️  Ошибка: {str(e)}")

        if self.current_iteration >= self.max_iterations:
            self.logger.warning("Достигнуто максимальное количество итераций")
            print(
                f"\n⚠️  Достигнуто максимальное количество итераций ({self.max_iterations}). "
                "Работа агента остановлена."
            )
