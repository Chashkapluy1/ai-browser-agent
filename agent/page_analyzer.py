"""Модуль анализа и разметки DOM страницы."""

import os
from typing import Dict

from playwright.async_api import Page


class PageAnalyzer:
    """Анализирует DOM страницы и делает его понятным для AI."""

    @staticmethod
    def _load_js_script(filename: str) -> str:
        """
        Загружает JavaScript скрипт из файла.
        """
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "scripts", filename
        )
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return ""

    @staticmethod
    async def get_simplified_dom(page: Page) -> str:
        """
        Возвращает упрощенную и размеченную версию DOM.
        """
        # === ИЗМЕНЕНИЕ ЗДЕСЬ ===
        await page.wait_for_load_state("domcontentloaded", timeout=30000)

        js_script = PageAnalyzer._load_js_script("analyze_page.js")
        if not js_script:
            js_script = """
            () => {
                let idCounter = 0;
                const interactiveElements = document.querySelectorAll(
                    'a, button, input:not([type="hidden"]), textarea, select, [role="button"], [onclick], [tabindex="0"]'
                );
                const simplified_elements = [];

                interactiveElements.forEach(el => {
                    const style = window.getComputedStyle(el);
                    if (style.display !== 'none' &&
                        style.visibility !== 'hidden' &&
                        style.opacity !== '0' &&
                        !el.disabled &&
                        el.offsetParent !== null) {

                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            const newId = `ai-id-${idCounter++}`;
                            el.setAttribute('data-ai-id', newId);

                            let text = el.innerText || el.textContent || el.value || el.placeholder || el.getAttribute('aria-label') || el.title || '';
                            text = text.trim().substring(0, 150);

                            const tagName = el.tagName.toLowerCase();
                            const elementType = el.type || el.tagName.toLowerCase();

                            simplified_elements.push(
                                `<${tagName} data-ai-id="${newId}" type="${elementType}">${text}</${tagName}>`
                            );
                        }
                    }
                });

                return simplified_elements.join('\\n');
            }
            """

        simplified_dom = await page.evaluate(f"({js_script})()")
        return simplified_dom or "На странице нет интерактивных элементов."

    @staticmethod
    async def get_page_text_content(page: Page) -> str:
        """
        Извлекает текстовое содержимое страницы.
        """
        # === ИЗМЕНЕНИЕ ЗДЕСЬ ===
        await page.wait_for_load_state("domcontentloaded", timeout=30000)

        js_script = PageAnalyzer._load_js_script("get_page_text.js")
        if not js_script:
            js_script = """
            () => {
                const scripts = document.querySelectorAll('script, style, noscript');
                scripts.forEach(el => el.remove());
                const bodyText = document.body.innerText || document.body.textContent || '';
                return bodyText.trim().substring(0, 2000);
            }
            """

        text_content = await page.evaluate(f"({js_script})()")
        return text_content or ""

    @staticmethod
    async def get_page_summary(page: Page) -> Dict[str, str]:
        """
        Получает краткую сводку о странице.
        """
        await page.wait_for_load_state("domcontentloaded", timeout=30000)

        js_script = PageAnalyzer._load_js_script("get_page_data.js")
        if not js_script:
            # Fallback: делаем два отдельных вызова
            summary = {
                "url": page.url,
                "title": await page.title(),
                "text_preview": await PageAnalyzer.get_page_text_content(page),
                "simplified_dom": await PageAnalyzer.get_simplified_dom(page),  # Добавим и DOM для консистентности
            }
            return summary

        page_data = await page.evaluate(f"({js_script})()")

        summary = {
            "url": page.url,
            "title": await page.title(),
            "text_preview": page_data.get("text_preview", ""),
            "simplified_dom": page_data.get("simplified_dom", "Не удалось проанализировать DOM."),
        }

        return summary
