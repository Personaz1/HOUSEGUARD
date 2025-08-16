"""
Response Processor - Правильная обработка ответов модели
Разделяет парсинг tool calls и форматирование для чата
"""

import re
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ToolCall:
    """Структура для tool call"""
    function_name: str
    arguments: Dict[str, Any]
    original_text: str
    start_pos: int
    end_pos: int

@dataclass
class ProcessedResponse:
    """Результат обработки ответа"""
    original_text: str
    tool_calls: List[ToolCall]
    formatted_text: str
    tool_results: List[Dict[str, Any]]

class ToolExtractor:
    """Простой экстрактор tool calls"""
    
    def __init__(self):
        # Простые паттерны для поиска tool calls
        self.tool_patterns = [
            r'SystemTools\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*(.*?)\s*\)',
            r'VisionTools\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*(.*?)\s*\)',
            r'HomeTools\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*(.*?)\s*\)',
        ]
    
    def extract_tool_calls(self, text: str) -> List[ToolCall]:
        """Извлекает tool calls из текста"""
        tool_calls = []
        seen = set()
        
        for pattern in self.tool_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
            
            for match in matches:
                try:
                    function_name = match.group(1)
                    args_str = match.group(2)
                    
                    # Парсим аргументы
                    arguments = self._parse_arguments(args_str)
                    
                    key = (function_name, args_str.strip())
                    if key in seen:
                        continue
                    seen.add(key)

                    tool_call = ToolCall(
                        function_name=function_name,
                        arguments=arguments,
                        original_text=match.group(0),
                        start_pos=match.start(),
                        end_pos=match.end()
                    )
                    
                    tool_calls.append(tool_call)
                    logger.info(f"🔧 TOOL EXTRACTOR: Found tool call: {function_name}({arguments})")
                    
                except Exception as e:
                    logger.error(f"❌ TOOL EXTRACTOR: Error parsing tool call: {e}")
        
        return tool_calls
    
    def _parse_arguments(self, args_str: str) -> Dict[str, Any]:
        """Парсит аргументы tool call"""
        arguments = {}
        args_str = args_str.strip()
        
        # Если нет аргументов или пустые скобки
        if not args_str or args_str == '{}':
            return arguments
        
        # Ищем первый аргумент (путь к файлу)
        first_quote = args_str.find('"')
        if first_quote != -1:
            end_quote = args_str.find('"', first_quote + 1)
            if end_quote != -1:
                file_path = args_str[first_quote + 1:end_quote]
                arguments["arg_0"] = file_path
                
                # Ищем второй аргумент (содержимое)
                remaining = args_str[end_quote + 1:].strip()
                if remaining.startswith(','):
                    remaining = remaining[1:].strip()
                
                # Если есть второй аргумент
                if remaining.startswith('"'):
                    # Ищем закрывающую кавычку для контента
                    content_start = 1  # Пропускаем открывающую кавычку
                    content_end = -1
                    
                    # Ищем закрывающую кавычку, учитывая экранирование
                    i = content_start
                    while i < len(remaining):
                        if remaining[i] == '"' and (i == 0 or remaining[i-1] != '\\'):
                            content_end = i
                            break
                        i += 1
                    
                    if content_end != -1:
                        # Нашли закрывающую кавычку
                        content = remaining[content_start:content_end]
                        arguments["arg_1"] = content
                    else:
                        # Не нашли закрывающую кавычку - берем все до конца
                        content = remaining[content_start:]
                        arguments["arg_1"] = content
                else:
                    # Если нет кавычки, берем все что осталось
                    arguments["arg_1"] = remaining
        
        return arguments

class ToolExecutor:
    """Выполняет tool calls"""
    
    def __init__(self, ai_client):
        self.ai_client = ai_client
    
    def execute_tool_call(self, tool_call: ToolCall, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Выполняет tool call"""
        try:
            function_name = tool_call.function_name
            arguments = tool_call.arguments
            logger.info(f"🔧 EXECUTE_TOOL: Starting execution of {function_name} with args: {arguments}")
            
            # Определяем целевой набор инструментов по имени функции
            # По умолчанию используем системные инструменты
            tool_instance = getattr(self.ai_client, 'system_tools', self.ai_client)

            # Функции зрения, которые должны исполняться через VisionTools
            vision_functions = {
                'list_cameras',
                'capture_image',
                'detect_motion',
                'get_camera_status',
            }

            # Если обнаружили вызов функции зрения — маршрутизируем в VisionTools
            if function_name in vision_functions and hasattr(self.ai_client, 'vision_tools'):
                tool_instance = self.ai_client.vision_tools
            
            # Функции дома SmartHouse — маршрутизируем в HomeTools
            home_functions = {
                'control_light', 'set_thermostat', 'lock_door', 'unlock_door', 'cover_set_position',
                'switch_on', 'switch_off', 'siren_on', 'siren_off', 'arm_security', 'disarm_security',
                'camera_snapshot', 'camera_analyze', 'get_device_status', 'get_sensor_data', 'get_state', 'list_devices'
            }
            if function_name in home_functions and hasattr(self.ai_client, 'home_tools'):
                tool_instance = self.ai_client.home_tools
            
            if hasattr(tool_instance, function_name):
                func = getattr(tool_instance, function_name)
                
                # Вызываем функцию с аргументами
                if function_name in ['create_file', 'append_to_file']:
                    logger.info(f"🔧 EXECUTE_TOOL: Processing {function_name}")
                    # Для файловых операций
                    file_path = arguments.get('arg_0', '')
                    content = arguments.get('arg_1', '')
                    logger.info(f"🔧 EXECUTE_TOOL: file_path={file_path}, content_length={len(content)}")
                    
                    if function_name == 'create_file':
                        result = func(file_path, content)
                        logger.info(f"🔧 EXECUTE_TOOL: create_file result: {result}")
                    else:  # append_to_file
                        result = func(file_path, content)
                        logger.info(f"🔧 EXECUTE_TOOL: append_to_file result: {result}")
                    
                    return {
                        'success': True,
                        'result': result,
                        'function': function_name,
                        'file_path': file_path
                    }
                elif function_name == 'read_file':
                    # Для read_file - только путь к файлу
                    file_path = arguments.get('arg_0', '')
                    result = func(file_path)
                    return {
                        'success': True,
                        'result': result,
                        'function': function_name,
                        'file_path': file_path
                    }
                elif function_name == 'list_files':
                    # Для list_files - только директория
                    directory = arguments.get('arg_0', '.')
                    result = func(directory)
                    return {
                        'success': True,
                        'result': result,
                        'function': function_name,
                        'directory': directory
                    }
                elif function_name == 'analyze_file':
                    # Для analyze_file - file_path и user_context
                    if arguments:
                        # Сортируем аргументы по ключам arg_0, arg_1, etc.
                        sorted_args = []
                        i = 0
                        while f'arg_{i}' in arguments:
                            sorted_args.append(arguments[f'arg_{i}'])
                            i += 1
                        # Убираем пустые хвостовые аргументы
                        while sorted_args and (sorted_args[-1] is None or (isinstance(sorted_args[-1], str) and sorted_args[-1].strip() == '')):
                            sorted_args.pop()
                        result = func(*sorted_args)
                    else:
                        # Если нет аргументов, возвращаем ошибку
                        return {
                            'success': False,
                            'error': 'analyze_file requires at least one argument (file_path)'
                        }
                    return {
                        'success': True,
                        'result': result,
                        'function': function_name
                    }
                elif function_name == 'analyze_image':
                    # Явная поддержка VisionTools.analyze_image(image_path)
                    # Маршрутизируем в VisionTools при наличии
                    tool_for_call = tool_instance
                    if hasattr(self.ai_client, 'vision_tools'):
                        tool_for_call = self.ai_client.vision_tools
                        func = getattr(tool_for_call, function_name, func)
                    # Собираем позиционные аргументы
                    if arguments:
                        sorted_args = []
                        i = 0
                        while f'arg_{i}' in arguments:
                            sorted_args.append(arguments[f'arg_{i}'])
                            i += 1
                        # Убираем пустые хвостовые аргументы
                        while sorted_args and (sorted_args[-1] is None or (isinstance(sorted_args[-1], str) and sorted_args[-1].strip() == '')):
                            sorted_args.pop()
                        result = func(*sorted_args)
                        # Auto-log insight to memory graph if possible
                        try:
                            image_path = sorted_args[0] if sorted_args else ''
                            if image_path:
                                analysis_json = image_path.rsplit('.', 1)[0] + '_analysis.json'
                                import os, json, datetime
                                if os.path.exists(analysis_json):
                                    with open(analysis_json, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                    # Сформируем краткий инсайт
                                    gv = data.get('google_vision') or {}
                                    basics = data.get('basic') or {}
                                    labels = ', '.join((gv.get('labels') or [])[:5])
                                    objects = ', '.join((gv.get('objects') or [])[:5])
                                    faces = gv.get('faces_detected')
                                    dims = basics.get('dimensions')
                                    insight = (
                                        f"Image {os.path.basename(image_path)} | {dims} | "
                                        f"GV labels: {labels or '—'} | GV objects: {objects or '—'} | GV faces: {faces}"
                                    )
                                    title = datetime.datetime.now().strftime('%Y-%m-%d %H:%M') + ' - Vision Insight'
                                    content = f"\n## {title}\n- {insight}\n"
                                    # Append to memory graph
                                    if hasattr(self.ai_client, 'system_tools'):
                                        self.ai_client.system_tools.append_to_file('guardian_sandbox/memory_graph.md', content)
                        except Exception:
                            pass
                    else:
                        return {
                            'success': False,
                            'error': 'analyze_image requires image_path'
                        }
                    return {
                        'success': True,
                        'result': result,
                        'function': function_name
                    }
                else:
                    # Для других функций - передаем аргументы позиционно
                    if tool_instance is getattr(self.ai_client, 'home_tools', None):
                        # Специальный парсер аргументов для HomeTools (поддержка bool/чисел/строк и нескольких аргументов)
                        pos_args = self._parse_home_args(tool_call.original_text)
                        result = func(*pos_args)
                    else:
                        if arguments:
                            # Сортируем аргументы по ключам arg_0, arg_1, etc.
                            sorted_args = []
                            i = 0
                            while f'arg_{i}' in arguments:
                                sorted_args.append(arguments[f'arg_{i}'])
                                i += 1
                            # Убираем пустые хвостовые аргументы
                            while sorted_args and (sorted_args[-1] is None or (isinstance(sorted_args[-1], str) and sorted_args[-1].strip() == '')):
                                sorted_args.pop()
                            result = func(*sorted_args)
                        else:
                            result = func()
                    return {
                        'success': True,
                        'result': result,
                        'function': function_name
                    }
            else:
                return {
                    'success': False,
                    'error': f'Function {function_name} not found'
                }
                
        except Exception as e:
            logger.error(f"❌ TOOL EXECUTOR: Error executing {tool_call.function_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _parse_home_args(self, original_text: str):
        """Парсинг позиционных аргументов из строки вида HomeTools.fn(arg1, arg2, ...) с поддержкой кавычек и типов."""
        try:
            # извлекаем содержимое скобок
            start = original_text.find('(')
            end = original_text.rfind(')')
            if start == -1 or end == -1 or end <= start:
                return []
            inside = original_text[start + 1:end]
            # посимвольный разбор с учетом кавычек
            args = []
            buf = []
            in_str = False
            quote_ch = ''
            for ch in inside:
                if in_str:
                    if ch == quote_ch:
                        in_str = False
                    buf.append(ch)
                else:
                    if ch in ('"', "'"):
                        in_str = True
                        quote_ch = ch
                        buf.append(ch)
                    elif ch == ',':
                        token = ''.join(buf).strip()
                        if token:
                            args.append(self._coerce_token(token))
                        buf = []
                    else:
                        buf.append(ch)
            token = ''.join(buf).strip()
            if token:
                args.append(self._coerce_token(token))
            return args
        except Exception:
            return []

    def _coerce_token(self, token: str):
        """Преобразование токена в bool/int/float/str, с снятием кавычек."""
        t = token.strip()
        # строка в кавычках
        if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
            return t[1:-1]
        tl = t.lower()
        if tl == 'true':
            return True
        if tl == 'false':
            return False
        # числа
        try:
            if '.' in t:
                return float(t)
            return int(t)
        except Exception:
            return t

class ResponseFormatter:
    """Форматирует ответы для чата"""
    
    def format_for_chat(self, text: str, tool_results: List[Dict[str, Any]]) -> str:
        """Форматирует ответ для отображения в чате"""
        formatted_text = text
        
        # Убираем "User:" сообщения из ответа AI
        formatted_text = re.sub(r'User:\s*[^\n]*\n?', '', formatted_text)
        formatted_text = re.sub(r'^\s*User:\s*[^\n]*\n?', '', formatted_text, flags=re.MULTILINE)
        
        # Добавляем результаты выполнения инструментов
        for result in tool_results:
            if result.get('success'):
                formatted_text += f"\n\n✅ {result.get('result', '')}"
            else:
                formatted_text += f"\n\n❌ Error: {result.get('error', '')}"
        
        return formatted_text

class ResponseProcessor:
    """Обрабатывает ответы AI"""
    
    def __init__(self, ai_client):
        self.ai_client = ai_client
        self.tool_extractor = ToolExtractor()
        self.tool_executor = ToolExecutor(ai_client)
        self.response_formatter = ResponseFormatter()
    
    async def process_complete_response(self, text: str, context: Dict[str, Any] = None) -> ProcessedResponse:
        """Обрабатывает полный ответ"""
        # Извлекаем tool calls
        tool_calls = self.tool_extractor.extract_tool_calls(text)
        logger.info(f"🔧 PROCESS_COMPLETE: Found {len(tool_calls)} tool calls")
        
        # Выполняем tool calls
        tool_results = []
        for tool_call in tool_calls:
            logger.info(f"🔧 PROCESS_COMPLETE: Executing tool call: {tool_call.function_name}")
            result = self.tool_executor.execute_tool_call(tool_call, context)
            logger.info(f"🔧 PROCESS_COMPLETE: Tool call result: {result}")
            tool_results.append(result)
        
        # Форматируем ответ
        formatted_text = self.response_formatter.format_for_chat(text, tool_results)
        
        return ProcessedResponse(
            original_text=text,
            tool_calls=tool_calls,
            formatted_text=formatted_text,
            tool_results=tool_results
        )
    
    async def process_streaming_response(self, text_stream):
        """Обрабатывает стриминг ответ - как у меня"""
        async for chunk in text_stream:
            yield chunk
        
        # После завершения стриминга обрабатываем tool calls
        # Это делается в web_app.py в chat_stream_endpoint
    
    def _clean_ai_internal_code(self, text: str) -> str:
        """Очищает внутренний код AI из ответа - ОТКЛЮЧЕНО для tool_code"""
        # Убираем python блоки
        text = re.sub(r'```python\s*\n.*?\n```', '', text, flags=re.DOTALL)
        # НЕ убираем tool_code блоки - они обрабатываются в system_tools.py
        # Убираем одиночные python
        text = re.sub(r'^python\s*$', '', text, flags=re.MULTILINE)
        # Убираем лишние тройные бектики без языка (но не tool_code)
        text = re.sub(r'```(?!tool_code)\s*\n[\s\S]*?\n```', '', text, flags=re.DOTALL)
        return text.strip() 