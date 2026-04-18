"""Инструменты для взаимодействия с браузером."""

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError


class BrowserTools:
    """Набор инструментов для взаимодействия с браузером."""

    def __init__(self, page: Page):
        """
        Инициализирует инструменты браузера.

        Args:
            page: Объект страницы Playwright.
        """
        self.page = page

    async def click_element(self, ai_id: str) -> str:
        """
        Кликает по элементу с указанным data-ai-id.
        После клика по ссылке или кнопке, которая ведет на новую страницу, используй 'wait_for_navigation'.

        Args:
            ai_id: Идентификатор элемента (например, 'ai-id-5').
        """
        if not ai_id or not isinstance(ai_id, str):
            return "Ошибка: невалидный идентификатор элемента."

        try:
            selector = f"[data-ai-id='{ai_id}']"
            await self.page.click(selector, timeout=10000)
            return f"Успешно нажат элемент с идентификатором {ai_id}."
        except PlaywrightTimeoutError:
            return f"Ошибка: элемент {ai_id} не найден или недоступен для клика."
        except Exception as e:
            return f"Ошибка при клике на элемент {ai_id}: {str(e)}"

    async def type_text(self, ai_id: str, text: str) -> str:
        """
        Вводит текст в поле с указанным data-ai-id.

        Args:
            ai_id: Идентификатор элемента (например, 'ai-id-3').
            text: Текст для ввода.
        """
        if not ai_id or not isinstance(ai_id, str):
            return "Ошибка: невалидный идентификатор элемента."
        if not isinstance(text, str):
            return "Ошибка: текст должен быть строкой."

        try:
            selector = f"[data-ai-id='{ai_id}']"
            await self.page.fill(selector, text, timeout=10000)
            return f"Текст '{text}' успешно введен в элемент {ai_id}."
        except PlaywrightTimeoutError:
            return f"Ошибка: элемент {ai_id} не найден или недоступен для ввода."
        except Exception as e:
            return f"Ошибка при вводе текста в элемент {ai_id}: {str(e)}"

    async def navigate_to_url(self, url: str) -> str:
        """
        Переходит на указанный URL.

        Args:
            url: URL для перехода.
        """
        if not url or not isinstance(url, str):
            return "Ошибка: невалидный URL."

        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
            return f"Успешно перешел на {url}."
        except Exception as e:
            return f"Ошибка при переходе на {url}: {str(e)}"

    async def scroll_page(self, direction: str = "down", pixels: int = 500) -> str:
        """
        Прокручивает страницу в указанном направлении.

        Args:
            direction: Направление прокрутки ('down', 'up', 'top', 'bottom').
            pixels: Количество пикселей для прокрутки (для down/up).
        """
        valid_directions = {"down", "up", "top", "bottom"}
        if direction not in valid_directions:
            return f"Ошибка: недопустимое направление '{direction}'. Используйте: {', '.join(valid_directions)}"

        if not isinstance(pixels, int) or pixels < 0:
            return "Ошибка: количество пикселей должно быть неотрицательным целым числом."

        try:
            if direction == "down":
                await self.page.evaluate(f"window.scrollBy(0, {pixels})")
            elif direction == "up":
                await self.page.evaluate(f"window.scrollBy(0, -{pixels})")
            elif direction == "top":
                await self.page.evaluate("window.scrollTo(0, 0)")
            elif direction == "bottom":
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            await self.page.wait_for_timeout(500)
            return f"Страница прокручена {direction}."
        except Exception as e:
            return f"Ошибка при прокрутке страницы: {str(e)}"

    async def get_element_text(self, ai_id: str) -> str:
        """
        Получает текст элемента с указанным data-ai-id.

        Args:
            ai_id: Идентификатор элемента.
        """
        try:
            selector = f"[data-ai-id='{ai_id}']"
            text = await self.page.text_content(selector, timeout=10000)
            return text or f"Элемент {ai_id} не содержит текста."
        except PlaywrightTimeoutError:
            return f"Ошибка: элемент {ai_id} не найден."
        except Exception as e:
            return f"Ошибка при получении текста элемента {ai_id}: {str(e)}"

    async def wait_for_element(self, ai_id: str, timeout: int = 10000) -> str:
        """
        Ожидает появления элемента на странице.

        Args:
            ai_id: Идентификатор элемента.
            timeout: Таймаут ожидания в миллисекундах.
        """
        try:
            selector = f"[data-ai-id='{ai_id}']"
            await self.page.wait_for_selector(selector, timeout=timeout)
            return f"Элемент {ai_id} появился на странице."
        except PlaywrightTimeoutError:
            return f"Элемент {ai_id} не появился в течение {timeout}мс."
        except Exception as e:
            return f"Ошибка при ожидании элемента {ai_id}: {str(e)}"

    async def press_key(self, key: str) -> str:
        """
        Нажимает клавишу на странице.

        Args:
            key: Название клавиши (например, 'Enter', 'Escape', 'Tab').
        """
        try:
            await self.page.keyboard.press(key)
            return f"Нажата клавиша {key}."
        except Exception as e:
            return f"Ошибка при нажатии клавиши {key}: {str(e)}"

    async def wait_for_navigation(self, timeout: int = 30000) -> str:
        """
        Ожидает завершения навигации на странице после действия (например, клика).
        Используй это СРАЗУ ПОСЛЕ клика по ссылке или кнопке, которая ведет на новую страницу.

        Args:
            timeout: Таймаут ожидания в миллисекундах.
        """
        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=timeout)
            return "Навигация на новую страницу успешно завершена."
        except Exception as e:
            return f"Ошибка при ожидании навигации: {str(e)}"

    async def close_popup_if_present(self) -> str:
        """
        Проверяет наличие распространенных попап-окон (регистрация, cookie) и пытается их закрыть.
        Используй этот инструмент в начале работы на новой странице или если не можешь кликнуть по элементу.
        """
        # Ищем кнопку закрытия по самым распространенным признакам
        close_button_selectors = [
            '[aria-label="Close"]',
            '[aria-label="close"]',
            'button[class*="close"]',
            'div[class*="close"]',
            '[id*="close"]',
            'button:has-text("Accept")',
            'button:has-text("Accept all")',
            'button:has-text("Хорошо")',
            'button:has-text("Принять все")',
            'button:has-text("No, thanks")',
        ]

        for selector in close_button_selectors:
            try:
                # Используем locator, так как он не бросает ошибку, если элемент не найден сразу
                close_button = self.page.locator(selector).first
                # Проверяем, что элемент видим, прежде чем кликнуть
                if await close_button.is_visible(timeout=1000):
                    await close_button.click()
                    await self.page.wait_for_timeout(500)  # Даем время на анимацию закрытия
                    return f"Найдено и закрыто всплывающее окно с помощью селектора '{selector}'."
            except Exception:
                # Просто пробуем следующий селектор, если клик не удался или элемент не найден
                continue

        return "Всплывающих окон для закрытия не найдено."
