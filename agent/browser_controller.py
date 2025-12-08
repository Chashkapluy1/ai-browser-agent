"""Модуль управления браузером через Playwright."""

import os
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page, Playwright


class BrowserController:
    """Управляет жизненным циклом браузера и взаимодействием со страницей."""

    def __init__(self, headless: bool = False):
        """
        Инициализирует контроллер браузера.

        Args:
            headless: Запускать браузер в headless режиме или нет.
        """
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright: Optional[Playwright] = None
        self.headless = headless

    def _find_system_chrome(self) -> Optional[str]:
        """
        Пытается найти системный Chrome на Windows.

        Returns:
            Путь к Chrome или None.
        """
        possible_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    async def start(self) -> None:
        """
        Запускает браузер и создает новую страницу.

        Raises:
            Exception: Если не удалось запустить браузер.
        """
        self.playwright = await async_playwright().start()

        # Проверяем, есть ли путь к системному Chrome в переменных окружения
        chrome_path = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
        if not chrome_path:
            chrome_path = self._find_system_chrome()

        launch_options = {"headless": self.headless}
        if chrome_path and os.path.exists(chrome_path):
            launch_options["executable_path"] = chrome_path

        try:
            self.browser = await self.playwright.chromium.launch(**launch_options)
        except Exception as e:
            error_msg = (
                f"Не удалось запустить браузер: {str(e)}\n\n"
                "Возможные решения:\n"
                "1. Установите браузер: playwright install chromium\n"
                "2. Или установите Google Chrome и укажите путь через переменную окружения:\n"
                "   $env:PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH='C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'\n"
                "3. Или используйте другой браузер (firefox/webkit)"
            )
            raise RuntimeError(error_msg) from e

        self.page = await self.browser.new_page()

        # Устанавливаем таймауты
        self.page.set_default_timeout(30000)
        self.page.set_default_navigation_timeout(30000)

    async def go_to(self, url: str) -> None:
        """
        Переходит по указанному URL.

        Args:
            url: URL для перехода.
        """
        if self.page:
            await self.page.goto(url, wait_until="networkidle")

    async def get_page_content(self) -> str:
        """
        Возвращает HTML-содержимое текущей страницы.

        Returns:
            HTML-содержимое страницы или пустая строка.
        """
        if self.page:
            return await self.page.content()
        return ""

    async def get_current_url(self) -> str:
        """
        Возвращает текущий URL страницы.

        Returns:
            Текущий URL или пустая строка.
        """
        if self.page:
            return self.page.url
        return ""

    async def get_page_title(self) -> str:
        """
        Возвращает заголовок текущей страницы.

        Returns:
            Заголовок страницы или пустая строка.
        """
        if self.page:
            return await self.page.title()
        return ""

    async def wait_for_load(self, timeout: int = 30000) -> None:
        """
        Ожидает загрузки страницы.

        Args:
            timeout: Таймаут ожидания в миллисекундах.
        """
        if self.page:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)

    async def stop(self) -> None:
        """Закрывает браузер и освобождает ресурсы."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

