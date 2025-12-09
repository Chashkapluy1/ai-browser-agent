"""Точка входа для запуска AI-агента браузера."""

import asyncio
import os
import sys

from dotenv import load_dotenv

from agent.browser_controller import BrowserController
from agent.core import AICore
from tools.browser_tools import BrowserTools
from tools.tool_manager import ToolManager
from utils.logger import setup_logger


async def main() -> None:
    """Основная функция запуска агента."""
    logger = setup_logger("main")

    # Загружаем переменные окружения
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        logger.error(
            "OPENAI_API_KEY не найден в переменных окружения. "
            "Создайте файл .env и добавьте OPENAI_API_KEY=your_key"
        )
        print(
            "❌ Ошибка: OPENAI_API_KEY не найден.\n"
            "Создайте файл .env и добавьте: OPENAI_API_KEY=your_key"
        )
        sys.exit(1)

    # Инициализация компонентов
    browser_controller = BrowserController(headless=False)
    logger.info("Запуск браузера...")

    try:
        await browser_controller.start()
        logger.info("Браузер успешно запущен")

        # Создание инструментов и автоматическая регистрация
        browser_tools = BrowserTools(browser_controller.page)
        tool_manager = ToolManager()

        # Автоматическая регистрация всех публичных async методов из BrowserTools
        tool_manager.register_tools_from_instance(browser_tools)
        logger.info(f"Зарегистрировано инструментов: {len(tool_manager.tools)}")

        # Создание AI-агента
        agent = AICore(api_key=api_key, tool_manager=tool_manager)

        # Получение задачи от пользователя
        print("\n" + "=" * 60)
        print("🤖 AI Browser Agent")
        print("=" * 60)
        print("\nВведите задачу для агента (например: 'Найди вакансии Python на hh.ru')")
        print("Или введите 'exit' для выхода.\n")

        while True:
            user_task = input("Ваша задача: ").strip()

            if not user_task:
                print("Пожалуйста, введите задачу.")
                continue

            if user_task.lower() in ("exit", "quit", "выход"):
                print("До свидания!")
                break

            try:
                logger.info(f"Запуск агента с задачей: {user_task}")
                await agent.run_agent_loop(user_task, browser_controller)
                print("\n" + "-" * 60)
                print("Задача завершена. Можете ввести новую задачу или 'exit' для выхода.")
                print("-" * 60 + "\n")

            except KeyboardInterrupt:
                print("\n\n⚠️  Работа прервана пользователем.")
                break
            except Exception as e:
                logger.error(f"Критическая ошибка: {str(e)}", exc_info=True)
                print(f"\n❌ Произошла критическая ошибка: {str(e)}")
                print("Попробуйте еще раз или введите 'exit' для выхода.\n")

    except Exception as e:
        logger.error(f"Ошибка при запуске: {str(e)}", exc_info=True)
        print(f"❌ Ошибка при запуске: {str(e)}")
    finally:
        logger.info("Закрытие браузера...")
        await browser_controller.stop()
        logger.info("Браузер закрыт")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена.")
        # Даем время на корректное закрытие ресурсов
        import time
        time.sleep(0.1)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {str(e)}")
        sys.exit(1)
