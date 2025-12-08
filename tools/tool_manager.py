"""Менеджер для регистрации и вызова инструментов."""

import inspect
import re
from typing import Any, Callable, Dict, List, Optional


def parse_google_docstring(doc: str) -> Dict[str, Any]:
    """
    Парсит docstring в стиле Google для извлечения описания и параметров.

    Args:
        doc: Docstring функции.

    Returns:
        Словарь с описанием и параметрами.
    """
    if not doc:
        return {"description": "", "params": {}}

    # Разделяем описание и секцию Args
    parts = doc.split("Args:")
    description = parts[0].strip()

    params: Dict[str, str] = {}
    if len(parts) > 1:
        arg_section = parts[1].strip()
        # Парсим параметры в формате "param_name: описание"
        for line in arg_section.split("\n"):
            match = re.match(r"\s*(\w+):\s*(.*)", line)
            if match:
                param_name, param_desc = match.groups()
                params[param_name] = param_desc.strip()

    return {"description": description, "params": params}


def python_type_to_json_type(python_type: type) -> str:
    """
    Преобразует тип Python в тип JSON Schema.

    Args:
        python_type: Тип Python.

    Returns:
        Тип JSON Schema.
    """
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
    }

    # Обработка Optional и Union
    origin = getattr(python_type, "__origin__", None)
    # Проверяем, является ли тип Optional (Optional[T] == Union[T, None])
    if origin is not None:
        # Optional[T] имеет __origin__ = Union, а __args__ = (T, type(None))
        args = getattr(python_type, "__args__", ())
        if args and len(args) == 2 and type(None) in args:
            # Это Optional, берем первый аргумент (не None)
            non_none_type = next((arg for arg in args if arg is not type(None)), None)
            if non_none_type:
                return python_type_to_json_type(non_none_type)

    return type_mapping.get(python_type, "string")


class ToolManager:
    """Менеджер для регистрации и вызова инструментов для AI-агента."""

    def __init__(self):
        """Инициализирует менеджер инструментов."""
        self.tools: Dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable) -> None:
        """
        Регистрирует инструмент для использования агентом.

        Args:
            name: Имя инструмента.
            func: Функция-инструмент (должна быть async).
        """
        if not inspect.iscoroutinefunction(func):
            raise ValueError(f"Инструмент {name} должен быть async функцией")
        self.tools[name] = func

    def register_tools_from_instance(self, instance: Any, prefix: str = "") -> None:
        """
        Автоматически регистрирует все публичные async методы из экземпляра класса.

        Args:
            instance: Экземпляр класса с методами-инструментами.
            prefix: Префикс для имен инструментов (необязательно).
        """
        for name, method in inspect.getmembers(instance, predicate=inspect.ismethod):
            if name.startswith("_") or not inspect.iscoroutinefunction(method):
                continue

            tool_name = f"{prefix}{name}" if prefix else name
            self.register_tool(tool_name, method)

    async def call_tool(self, name: str, **kwargs: Any) -> str:
        """
        Вызывает зарегистрированный инструмент.

        Args:
            name: Имя инструмента.
            **kwargs: Аргументы для передачи в инструмент.

        Returns:
            Результат выполнения инструмента в виде строки.
        """
        if name not in self.tools:
            return f"Ошибка: инструмент '{name}' не найден."

        try:
            result = await self.tools[name](**kwargs)
            return str(result)
        except Exception as e:
            return f"Ошибка при выполнении инструмента '{name}': {str(e)}"

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """
        Автоматически генерирует определения инструментов в формате OpenAI function calling.

        Схемы генерируются на основе сигнатур функций и их docstrings.

        Returns:
            Список определений функций для OpenAI API.
        """
        definitions = []

        for name, func in self.tools.items():
            # Получаем сигнатуру функции
            sig = inspect.signature(func)
            # Парсим docstring
            docstring_info = parse_google_docstring(func.__doc__ or "")

            properties: Dict[str, Any] = {}
            required: List[str] = []

            # Обрабатываем параметры функции
            for param_name, param in sig.parameters.items():
                # Пропускаем служебные параметры
                if param_name in ("self", "args", "kwargs"):
                    continue

                # Определяем тип параметра
                param_type = python_type_to_json_type(param.annotation) if param.annotation != inspect.Parameter.empty else "string"

                # Специальная обработка для enum-подобных типов (например, direction в scroll_page)
                param_schema: Dict[str, Any] = {
                    "type": param_type,
                    "description": docstring_info["params"].get(param_name, ""),
                }

                # Если параметр имеет значения по умолчанию, добавляем их
                if param.default != inspect.Parameter.empty:
                    param_schema["default"] = param.default

                properties[param_name] = param_schema

                # Если параметр обязательный (нет значения по умолчанию)
                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            # Специальные случаи для некоторых инструментов
            if name == "scroll_page" and "direction" in properties:
                properties["direction"]["enum"] = ["down", "up", "top", "bottom"]

            tool_definition = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": docstring_info["description"] or f"Выполняет действие: {name}",
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }

            definitions.append(tool_definition)

        return definitions
