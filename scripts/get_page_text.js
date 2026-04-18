/**
 * JavaScript скрипт для извлечения текстового содержимого страницы.
 * Удаляет скрипты и стили, возвращает только видимый текст.
 * 
 * @returns {string} Текстовое содержимое страницы (до 2000 символов)
 */
() => {
    // Удаляем скрипты и стили
    const scripts = document.querySelectorAll('script, style, noscript');
    scripts.forEach(el => el.remove());
    
    // Получаем видимый текст
    const bodyText = document.body.innerText || document.body.textContent || '';
    return bodyText.trim().substring(0, 2000);
}


