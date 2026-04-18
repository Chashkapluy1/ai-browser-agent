/**
 * JavaScript скрипт для получения полной информации о странице за один вызов.
 * Оптимизированная версия, объединяющая разметку элементов и извлечение текста.
 * 
 * @returns {Object} Объект с simplified_dom и text_preview
 */
() => {
    // Функция для извлечения текста страницы
    const getPageTextContent = () => {
        const scripts = document.querySelectorAll('script, style, noscript');
        scripts.forEach(el => el.remove());
        const bodyText = document.body.innerText || document.body.textContent || '';
        return bodyText.trim().substring(0, 2000);
    };

    // Функция для разметки интерактивных элементов
    const getSimplifiedDom = () => {
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

        return simplified_elements.join('\n') || "На странице нет интерактивных элементов.";
    };

    // Возвращаем объект с результатами обеих функций
    return {
        simplified_dom: getSimplifiedDom(),
        text_preview: getPageTextContent()
    };
}


