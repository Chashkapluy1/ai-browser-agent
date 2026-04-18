/**
 * JavaScript скрипт для анализа и разметки интерактивных элементов страницы.
 * Присваивает каждому видимому интерактивному элементу уникальный data-ai-id.
 * 
 * @returns {string} Упрощенное текстовое представление интерактивных элементов
 */
() => {
    let idCounter = 0;
    const interactiveElements = document.querySelectorAll(
        'a, button, input:not([type="hidden"]), textarea, select, [role="button"], [onclick], [tabindex="0"]'
    );
    const simplified_elements = [];

    interactiveElements.forEach(el => {
        // Проверяем, что элемент видим и активен
        const style = window.getComputedStyle(el);
        if (style.display !== 'none' && 
            style.visibility !== 'hidden' && 
            style.opacity !== '0' &&
            !el.disabled &&
            el.offsetParent !== null) {
            
            const rect = el.getBoundingClientRect();
            // Проверяем, что элемент имеет размеры
            if (rect.width > 0 && rect.height > 0) {
                const newId = `ai-id-${idCounter++}`;
                el.setAttribute('data-ai-id', newId);
                
                // Извлекаем текст элемента
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
}


