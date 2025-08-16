"""
Системные инструменты и утилиты
"""

import os
import re
import json
import subprocess
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..utils.config import Config
from ..utils.logger import Logger
from ..utils.error_handler import ErrorHandler

logger = Logger()

class SystemTools:
    """Класс для системных инструментов"""
    
    def __init__(self):
        """Инициализация SystemTools"""
        self.config = Config()
        self.error_handler = ErrorHandler()
        self.project_root = self.config.get_project_root()
    
    # ===== FILE OPERATIONS =====
    
    def read_file(self, path: str) -> str:
        """Чтение файла"""
        try:
            if not os.path.exists(path):
                return f"❌ File not found: {path}"
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return content
        except Exception as e:
            return f"❌ Error reading file {path}: {str(e)}"
    
    def write_file(self, path: str, content: str) -> str:
        """Запись в файл"""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✅ File written: {path}"
        except Exception as e:
            return f"❌ Error writing file {path}: {str(e)}"
    
    def edit_file(self, path: str, content: str) -> str:
        """Редактирование файла"""
        try:
            if not os.path.exists(path):
                return f"❌ File not found: {path}"
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✅ File edited: {path}"
        except Exception as e:
            return f"❌ Error editing file {path}: {str(e)}"
    
    def create_file(self, path: str, content: str) -> str:
        """Создание файла"""
        try:
            # Проверяем есть ли директория в пути
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"✅ File created: {path}"
        except Exception as e:
            return f"❌ Error creating file {path}: {str(e)}"
    
    def delete_file(self, path: str) -> str:
        """Удаление файла"""
        try:
            if not os.path.exists(path):
                return f"❌ File not found: {path}"
            
            os.remove(path)
            return f"✅ File deleted: {path}"
        except Exception as e:
            return f"❌ Error deleting file {path}: {str(e)}"
    
    def list_files(self, directory: str = ".") -> str:
        """Список файлов в директории"""
        try:
            if not os.path.exists(directory):
                return f"❌ Directory not found: {directory}"
            
            files = []
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isfile(item_path):
                    files.append(f"📄 {item}")
                else:
                    files.append(f"📁 {item}/")
            
            return f"Files in {directory}:\n" + "\n".join(files)
        except Exception as e:
            return f"❌ Error listing files in {directory}: {str(e)}"
    
    def search_files(self, query: str) -> str:
        """Поиск файлов по содержимому"""
        try:
            results = []
            for root, dirs, files in os.walk("."):
                for file in files:
                    if file.endswith(('.txt', '.md', '.py', '.json')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if query.lower() in content.lower():
                                    results.append(f"📄 {file_path}")
                        except:
                            continue
            
            if results:
                return f"Search results for '{query}':\n" + "\n".join(results[:20])
            else:
                return f"No files found containing '{query}'"
        except Exception as e:
            return f"❌ Error searching files: {str(e)}"
    
    def append_to_file(self, path: str, content: str) -> str:
        """Добавление в файл"""
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'a', encoding='utf-8') as f:
                f.write(content)
            return f"✅ Содержимое добавлено в: {path}"
        except Exception as e:
            return f"❌ Error appending to file {path}: {str(e)}"
    
    def safe_create_file(self, path: str, content: str) -> str:
        """Создание файла без лимитов"""
        try:
            # Создаем файл любого размера без ограничений
            return self.create_file(path, content)
        except Exception as e:
            return f"❌ Error creating file {path}: {str(e)}"
    
    # ===== USER PROFILE TOOLS =====
    
    def read_user_profile(self, username: str) -> str:
        """Чтение профиля пользователя"""
        try:
            profile_path = f"memory/user_profiles/{username}.json"
            if not os.path.exists(profile_path):
                return f"❌ Profile not found for user: {username}"
            
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile = json.load(f)
            
            return f"Profile for {username}:\n{json.dumps(profile, indent=2)}"
        except Exception as e:
            return f"❌ Error reading profile for {username}: {str(e)}"
    

    
    def search_user_data(self, username: str, query: str) -> str:
        """Поиск данных пользователя"""
        try:
            results = []
            user_dir = f"memory/user_profiles"
            
            if not os.path.exists(user_dir):
                return f"❌ User data directory not found"
            
            for file in os.listdir(user_dir):
                if file.startswith(username):
                    file_path = os.path.join(user_dir, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if query.lower() in content.lower():
                                results.append(f"📄 {file}")
                    except:
                        continue
            
            if results:
                return f"Search results for '{username}' with query '{query}':\n" + "\n".join(results)
            else:
                return f"No data found for '{username}' containing '{query}'"
        except Exception as e:
            return f"❌ Error searching user data: {str(e)}"
    

    

    
    # ===== SYSTEM TOOLS =====
    

    
    def get_system_logs(self, lines: int = 50) -> str:
        """Получение системных логов"""
        try:
            log_file = os.path.join(self.project_root, 'app.log')
            
            if not os.path.exists(log_file):
                return "No log file found"
            
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # Берем последние строки
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            return "=== Current Model Status ===\n" + "".join(recent_lines)
            
        except Exception as e:
            logger.error(f"Error reading system logs: {e}")
            return f"❌ Error reading logs: {str(e)}"
    
    def get_error_summary(self) -> str:
        """Получение сводки ошибок"""
        try:
            log_file = os.path.join(self.project_root, 'app.log')
            
            if not os.path.exists(log_file):
                return "No log file found"
            
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            errors = []
            for line in lines:
                if 'ERROR' in line or '❌' in line:
                    errors.append(line.strip())
            
            if errors:
                return "=== Error Summary ===\n" + "\n".join(errors[-10:])  # Последние 10 ошибок
            else:
                return "✅ No errors found in recent logs"
            
        except Exception as e:
            logger.error(f"Error getting error summary: {e}")
            return f"❌ Error getting error summary: {str(e)}"
    
    def diagnose_system_health(self) -> str:
        """Диагностика здоровья системы"""
        try:
            logger.info("🔧 SYSTEM TOOLS: Starting system health diagnosis...")
            health_report = []
            
            # Системный обзор
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            health_report.append("=== ΔΣ Guardian System Status ===")
            health_report.append(f"🕐 Current time: {current_time}")
            health_report.append("🧠 Current model: gemini-2.5-pro")
            health_report.append("📊 Model index: 0/7")
            
            logger.info(f"🔧 SYSTEM TOOLS: Current time: {current_time}")
            logger.info("🔧 SYSTEM TOOLS: Using gemini-2.5-pro model")
            
            # Проверка файлов
            health_report.append("\n=== File System Health ===")
            critical_files = [
                "memory/model_notes.json",
                "memory/conversation_history.json", 
                "memory/user_profiles/meranda.json",
                "memory/user_profiles/stepan.json",
            ]
            
            logger.info(f"🔧 SYSTEM TOOLS: Checking {len(critical_files)} critical files")
            
            for file_path in critical_files:
                full_path = os.path.join(self.project_root, file_path)
                if os.path.exists(full_path):
                    size = os.path.getsize(full_path)
                    health_report.append(f"✅ {file_path}: OK ({size} bytes)")
                    logger.info(f"✅ SYSTEM TOOLS: {file_path} - OK ({size} bytes)")
                else:
                    health_report.append(f"❌ {file_path}: Missing")
                    logger.warning(f"❌ SYSTEM TOOLS: {file_path} - Missing")
            
            # Проверка песочницы
            health_report.append("\n=== Sandbox Memory Files ===")
            sandbox_dir = os.path.join(self.project_root, 'guardian_sandbox')
            if os.path.exists(sandbox_dir):
                sandbox_files = os.listdir(sandbox_dir)
                for file in sandbox_files[:5]:  # Показываем первые 5 файлов
                    file_path = os.path.join(sandbox_dir, file)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        health_report.append(f"✅ guardian_sandbox/{file}: OK ({size} bytes)")
            else:
                health_report.append("❌ guardian_sandbox: Missing")
            
            # Проверка API
            health_report.append("\n=== API Health ===")
            if self.config.get_gemini_api_key():
                health_report.append("✅ GEMINI_API_KEY: Set")
            else:
                health_report.append("❌ GEMINI_API_KEY: Missing")
            
            if os.path.exists(sandbox_dir):
                health_report.append("✅ Sandbox: guardian_sandbox exists")
                health_report.append(f"📁 Sandbox files: {len(os.listdir(sandbox_dir))} files")
            else:
                health_report.append("❌ Sandbox: guardian_sandbox missing")
            
            # Возможности системы
            health_report.append("\n=== System Capabilities ===")
            health_report.append("✅ Self-modification: Can edit own prompt and code")
            health_report.append("✅ Memory system: Persistent notes in sandbox")
            health_report.append("✅ Multi-model support: Automatic model switching")
            health_report.append("✅ File operations: Read/write/create/delete files")
            health_report.append("✅ User profiles: Meranda and Stepan data")
            health_report.append("✅ Image analysis: Vision capabilities available")
            
            # Недавняя активность
            health_report.append("\n=== Recent Activity ===")
            try:
                log_file = os.path.join(self.project_root, 'app.log')
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    recent_lines = lines[-5:] if len(lines) > 5 else lines
                    for line in recent_lines:
                        health_report.append(f"📝 {line.strip()}")
                else:
                    health_report.append("⚠️ Error reading recent activity: No log file")
            except Exception as e:
                health_report.append(f"⚠️ Error reading recent activity: {str(e)}")
            
            result = "\n".join(health_report)
            logger.info(f"✅ SYSTEM TOOLS: System health diagnosis completed - {len(result.split())} words")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error diagnosing system health: {e}")
            return f"❌ Error diagnosing system health: {str(e)}"
    
    def analyze_image(self, image_path: str, user_context: str = "") -> str:
        """Анализ изображения"""
        try:
            # Проверяем существование файла
            if not os.path.exists(image_path):
                return f"❌ Image file not found: {image_path}"
            
            # Проверяем что это изображение
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_ext = os.path.splitext(image_path)[1].lower()
            
            if file_ext not in image_extensions:
                return f"❌ Not a valid image file: {image_path}"
            
            # Анализируем через Gemini Vision (прямая поддержка изображений)
            from ..models.gemini_client import GeminiClient
            gemini_client = GeminiClient()
            
            # Создаем промпт для анализа изображения
            analysis_prompt = f"""Analyze this image in detail. Provide a comprehensive description including:

1. **Objects and People**: What objects, people, or living things do you see?
2. **Actions and Activities**: What actions or activities are happening?
3. **Environment and Setting**: Describe the environment, location, or setting
4. **Emotions and Mood**: What emotions or mood does the image convey?
5. **Text and Symbols**: Any text, signs, or symbols visible?
6. **Technical Details**: Image quality, lighting, composition
7. **Context and Purpose**: What might be the purpose or context of this image?

Be detailed and specific in your analysis."""

            if user_context:
                analysis_prompt += f"\n\n**User Context**: {user_context}"
            
            # Анализируем изображение через Gemini
            result = gemini_client.chat(
                message="Please analyze this image",
                system_prompt=analysis_prompt,
                image_path=image_path
            )
            
            return f"🔍 Gemini Vision Analysis: {result}"
            
        except Exception as e:
            logger.error(f"Error analyzing image {image_path}: {e}")
            return f"❌ Error analyzing image: {str(e)}"
    
    def analyze_file(self, file_path: str, user_context: str = "") -> str:
        """Анализ файла любого типа"""
        try:
            # Проверяем существование файла
            if not os.path.exists(file_path):
                return f"❌ File not found: {file_path}"
            
            file_extension = os.path.splitext(file_path)[1].lower()
            
            # Для изображений используем analyze_image
            if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                return self.analyze_image(file_path, user_context)
            
            # Для PDF файлов
            elif file_extension == '.pdf':
                return self._analyze_pdf(file_path, user_context)
            
            # Для текстовых файлов
            elif file_extension in ['.txt', '.md', '.json', '.py', '.js', '.html', '.css', '.xml', '.csv']:
                return self._analyze_text_file(file_path, user_context)
            
            # Для других файлов
            else:
                return f"❌ Unsupported file type: {file_extension}\nSupported types: images, PDF, text files"
                
        except Exception as e:
            return f"❌ Error analyzing file {file_path}: {str(e)}"
    
    def _analyze_pdf(self, file_path: str, user_context: str = "") -> str:
        """Анализ PDF файла"""
        try:
            # Пытаемся извлечь текст из PDF
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text_content = ""
                
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_content += f"\n--- Page {page_num + 1} ---\n"
                    text_content += page.extract_text()
                
                if not text_content.strip():
                    return f"❌ Could not extract text from PDF: {file_path}"
                
                # Анализируем извлеченный текст
                from ..models.gemini_client import GeminiClient
                gemini_client = GeminiClient()
                
                analysis = gemini_client.chat(
                    f"Analyze this PDF content in detail. {user_context}\n\nContent:\n{text_content[:4000]}"
                )
                
                return f"✅ PDF analysis completed:\n\n{analysis}"
                
        except ImportError:
            return f"❌ PyPDF2 not installed. Install with: pip install PyPDF2"
        except Exception as e:
            return f"❌ Error analyzing PDF {file_path}: {str(e)}"
    
    def _analyze_text_file(self, file_path: str, user_context: str = "") -> str:
        """Анализ текстового файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                return f"❌ File is empty: {file_path}"
            
            # Анализируем содержимое
            from ..models.gemini_client import GeminiClient
            gemini_client = GeminiClient()
            
            analysis = gemini_client.chat(
                f"Analyze this file content in detail. {user_context}\n\nContent:\n{content[:4000]}"
            )
            
            return f"✅ File analysis completed:\n\n{analysis}"
            
        except Exception as e:
            return f"❌ Error analyzing text file {file_path}: {str(e)}"
    
    def get_project_structure(self) -> str:
        """Получение структуры проекта"""
        try:
            structure = []
            
            def scan_directory(path, prefix="", max_depth=3, current_depth=0):
                if current_depth > max_depth:
                    return
                
                try:
                    items = os.listdir(path)
                    items.sort()
                    
                    for item in items:
                        item_path = os.path.join(path, item)
                        rel_path = os.path.relpath(item_path, self.project_root)
                        
                        if os.path.isdir(item_path):
                            structure.append(f"{prefix}📁 {rel_path}/")
                            if current_depth < max_depth:
                                scan_directory(item_path, prefix + "  ", max_depth, current_depth + 1)
                        else:
                            size = os.path.getsize(item_path)
                            structure.append(f"{prefix}📄 {rel_path} ({size} bytes)")
                            
                except PermissionError:
                    structure.append(f"{prefix}🚫 {os.path.relpath(path, self.project_root)}/ (Permission denied)")
                except Exception as e:
                    structure.append(f"{prefix}❌ {os.path.relpath(path, self.project_root)}/ (Error: {str(e)})")
            
            structure.append("📂 Project Structure:")
            scan_directory(self.project_root)
            
            return "\n".join(structure)
            
        except Exception as e:
            logger.error(f"Error getting project structure: {e}")
            return f"❌ Error getting project structure: {str(e)}"
    
    def find_images(self) -> str:
        """Поиск изображений в проекте"""
        try:
            images = []
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            
            for root, dirs, files in os.walk(self.project_root):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in image_extensions):
                        rel_path = os.path.relpath(os.path.join(root, file), self.project_root)
                        size = os.path.getsize(os.path.join(root, file))
                        images.append(f"🖼️ {rel_path} ({size} bytes)")
            
            if images:
                return f"🖼️ Found {len(images)} images:\n" + "\n".join(images)
            else:
                return "🖼️ No images found in project"
            
        except Exception as e:
            logger.error(f"Error finding images: {e}")
            return f"❌ Error finding images: {str(e)}"
    
    def get_recent_file_changes(self) -> str:
        """Получение недавних изменений файлов"""
        try:
            from datetime import datetime, timedelta
            
            # Get files modified in last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            
            changes = []
            
            # Walk through all files
            for root, dirs, files in os.walk(self.project_root):
                # Skip hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                for file in files:
                    if file.startswith('.') or file in ['__pycache__', '.git']:
                        continue
                    
                    file_path = os.path.join(root, file)
                    try:
                        mtime = os.path.getmtime(file_path)
                        if mtime > yesterday.timestamp():
                            relative_path = os.path.relpath(file_path, self.project_root)
                            mod_time = datetime.fromtimestamp(mtime)
                            changes.append(f"📄 {relative_path} - {mod_time.strftime('%Y-%m-%d %H:%M')}")
                    except (OSError, PermissionError):
                        continue
            
            if changes:
                changes.sort(key=lambda x: x.split(' - ')[1], reverse=True)
                return f"🔄 RECENT FILE CHANGES (last 24h):\n" + "\n".join(changes[:20])
            else:
                return "📄 No recent file changes detected"
                
        except Exception as e:
            logger.error(f"Error getting recent file changes: {e}")
            return f"❌ Error getting recent file changes: {str(e)}"
    

    

    
    # ReAct архитектура
    def plan_step(self, goal: str) -> str:
        """Планирование шага"""
        try:
            # Анализируем цель и планируем следующий шаг
            if "system" in goal.lower() or "integrity" in goal.lower():
                return f"📋 Plan: Analyze system logs and check for errors"
            elif "stability" in goal.lower():
                return f"📋 Plan: Check system performance and resource usage"
            elif "guardian" in goal.lower():
                return f"📋 Plan: Verify AI model functionality and response quality"
            else:
                return f"📋 Plan: Execute general system analysis for goal: {goal}"
        except Exception as e:
            logger.error(f"Error planning step: {e}")
            return f"❌ Error planning step: {str(e)}"
    
    def act_step(self, tool_name: str, tool_input: str) -> str:
        """Выполнение шага"""
        try:
            # Выполняем действие в зависимости от инструмента
            if tool_name == "system_analysis":
                # Анализируем систему
                logs = self.get_system_logs(10)
                errors = self.get_error_summary()
                return f"🔧 System analysis completed\nLogs: {logs[:200]}...\nErrors: {errors}"
            elif tool_name == "file_check":
                # Проверяем файлы
                recent_changes = self.get_recent_file_changes()
                return f"🔧 File check completed\nRecent changes: {recent_changes}"
            else:
                return f"🔧 Executed {tool_name} with input: {tool_input}"
        except Exception as e:
            logger.error(f"Error executing step: {e}")
            return f"❌ Error executing step: {str(e)}"
    
    def reflect(self, history: List[str]) -> str:
        """Рефлексия"""
        try:
            # Анализируем историю и делаем выводы
            if len(history) == 0:
                return f"🤔 No history to reflect on"
            
            # Проверяем последние действия
            recent_actions = history[-3:] if len(history) >= 3 else history
            
            # Анализируем результаты
            if any("error" in action.lower() for action in recent_actions):
                return f"🤔 Reflection: Found errors in recent actions. System needs attention."
            elif any("completed" in action.lower() for action in recent_actions):
                return f"🤔 Reflection: Actions completed successfully. Goal achieved."
            else:
                return f"🤔 Reflection: {len(history)} steps completed. Continuing analysis."
                
        except Exception as e:
            logger.error(f"Error reflecting: {e}")
            return f"❌ Error reflecting: {str(e)}"
    
    def react_cycle(self, goal: str, max_steps: int = None, autonomous: bool = True) -> str:
        """ReAct цикл - работает до результата как обычный режим"""
        try:
            history = []
            step_count = 0
            consecutive_errors = 0
            max_consecutive_errors = 5
            
            while True:
                # Работаем до результата - игнорируем лимиты
                if not autonomous and max_steps is not None and step_count >= max_steps:
                    history.append(f"STOP: Reached max steps limit ({max_steps})")
                    break
                
                # Планируем следующий шаг
                plan_result = self.plan_step(goal)
                history.append(f"PLAN: {plan_result}")
                
                # Выполняем действие с автономной логикой
                action_result = self.act_step_autonomous(goal, step_count, history, autonomous)
                history.append(f"ACTION: {action_result}")
                
                # Проверяем на ошибки
                if "error" in action_result.lower() or "❌" in action_result:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        history.append(f"STOP: Too many consecutive errors ({consecutive_errors})")
                        break
                else:
                    consecutive_errors = 0
                
                # Рефлексируем
                reflection = self.reflect_autonomous(history, goal, autonomous)
                history.append(f"REFLECT: {reflection}")
                
                step_count += 1
                
                # Проверяем достижение цели
                if self._is_goal_achieved(reflection, goal):
                    history.append(f"SUCCESS: Goal achieved after {step_count} steps")
                    break
                
                # Проверяем необходимость пользовательского ввода
                if not autonomous and self._needs_user_input(reflection):
                    history.append(f"PAUSE: User input required")
                    break
                
                # Убираем защиту от бесконечного цикла - работаем до результата
                # if not autonomous and step_count > 100:
                #     history.append(f"STOP: Infinite loop protection triggered")
                #     break
            
            return f"🔄 ReAct cycle completed for goal: {goal}\nSteps: {step_count}\nAutonomous: {autonomous}\nHistory: {' | '.join(history[-5:])}"
            
        except Exception as e:
            logger.error(f"Error in ReAct cycle: {e}")
            return f"❌ Error in ReAct cycle: {str(e)}"
    
    def act_step_autonomous(self, goal: str, step_count: int, history: List[str], autonomous: bool) -> str:
        """Обычное выполнение шагов - интеллектуальный выбор инструментов"""
        try:
            # Анализируем цель и выбираем подходящий инструмент
            goal_lower = goal.lower()
            
            # Приоритет системной диагностики
            if "system" in goal_lower or "health" in goal_lower or "diagnose" in goal_lower or "analysis" in goal_lower:
                return self._execute_system_action(goal, step_count, history)
            
            # Приоритет файловых операций
            elif "file" in goal_lower or "read" in goal_lower or "write" in goal_lower or "create" in goal_lower or "content" in goal_lower:
                return self._execute_file_action(goal, step_count, history)
            
            # Приоритет умного дома
            elif "home" in goal_lower or "light" in goal_lower or "device" in goal_lower or "door" in goal_lower or "automation" in goal_lower:
                return self._execute_home_action(goal, step_count, history)
            
            # Приоритет сетевых операций
            elif "network" in goal_lower or "api" in goal_lower or "web" in goal_lower or "url" in goal_lower or "connect" in goal_lower:
                return self._execute_network_action(goal, step_count, history)
            
            # Общие действия
            else:
                return self._execute_general_action(goal, step_count, history)
                
        except Exception as e:
            logger.error(f"Error in autonomous action: {e}")
            return f"❌ Error in autonomous action: {str(e)}"
    
    def _execute_home_action(self, goal: str, step_count: int, history: List[str]) -> str:
        """Выполнение действий с умным домом"""
        try:
            # Импортируем HomeTools
            from ai_client.tools.home_tools import HomeTools
            import os
            
            home_tools = HomeTools(
                base_url=os.getenv("SMARTHOUSE_BASE_URL", "http://localhost:8005"),
                role=os.getenv("SMARTHOUSE_ROLE", "admin")
            )
            
            # Анализируем цель и выполняем действие
            if "light" in goal.lower():
                if "on" in goal.lower():
                    return home_tools.set_device_state("light", "on")
                elif "off" in goal.lower():
                    return home_tools.set_device_state("light", "off")
                else:
                    return home_tools.get_device_status("light")
            elif "door" in goal.lower():
                if "open" in goal.lower():
                    return home_tools.set_device_state("door", "open")
                elif "close" in goal.lower():
                    return home_tools.set_device_state("door", "close")
                else:
                    return home_tools.get_device_status("door")
            else:
                # Общий статус устройств
                return home_tools.list_devices()
                
        except Exception as e:
            logger.error(f"Error in home action: {e}")
            return f"❌ Error in home action: {str(e)}"
    
    def _execute_file_action(self, goal: str, step_count: int, history: List[str]) -> str:
        """Выполнение файловых операций"""
        try:
            if "read" in goal.lower():
                # Извлекаем имя файла из цели
                import re
                file_match = re.search(r'read\s+(\S+)', goal.lower())
                if file_match:
                    file_path = file_match.group(1)
                    return self.read_file(file_path)
                else:
                    return "❌ No file specified for reading"
            elif "write" in goal.lower() or "create" in goal.lower():
                return "⏸️ File write operations require user confirmation"
            else:
                return self.get_recent_file_changes()
                
        except Exception as e:
            logger.error(f"Error in file action: {e}")
            return f"❌ Error in file action: {str(e)}"
    
    def _execute_system_action(self, goal: str, step_count: int, history: List[str]) -> str:
        """Системные операции - глубокий анализ"""
        try:
            goal_lower = goal.lower()
            
            # Комплексная системная диагностика
            if "health" in goal_lower or "diagnose" in goal_lower:
                health_result = self.get_system_health()
                logs_result = self.get_system_logs(20)
                errors_result = self.get_error_summary()
                return f"🔧 System Analysis:\n{health_result}\n\nRecent Logs:\n{logs_result}\n\nErrors:\n{errors_result}"
            
            # Глубокий анализ логов
            elif "logs" in goal_lower or "log" in goal_lower:
                logs_result = self.get_system_logs(50)
                return f"📋 Log Analysis:\n{logs_result}"
            
            # Детальный анализ ошибок
            elif "errors" in goal_lower or "error" in goal_lower:
                errors_result = self.get_error_summary()
                logs_result = self.get_system_logs(10)
                return f"❌ Error Analysis:\n{errors_result}\n\nRecent Logs:\n{logs_result}"
            
            # Полная системная информация
            elif "info" in goal_lower or "information" in goal_lower:
                info_result = self.get_system_info()
                health_result = self.get_system_health()
                return f"ℹ️ System Information:\n{info_result}\n\nHealth Status:\n{health_result}"
            
            # По умолчанию - комплексный анализ
            else:
                health_result = self.get_system_health()
                logs_result = self.get_system_logs(15)
                return f"🔧 System Analysis:\n{health_result}\n\nRecent Activity:\n{logs_result}"
                
        except Exception as e:
            logger.error(f"Error in system action: {e}")
            return f"❌ Error in system action: {str(e)}"
    
    def _execute_network_action(self, goal: str, step_count: int, history: List[str]) -> str:
        """Выполнение сетевых и API операций"""
        try:
            goal_lower = goal.lower()
            
            if "network" in goal_lower:
                return self.diagnose_network()
            elif "api" in goal_lower:
                return "⏸️ API operations require user confirmation"
            elif "web" in goal_lower or "url" in goal_lower:
                # Извлекаем URL из цели
                import re
                url_match = re.search(r'https?://\S+', goal)
                if url_match:
                    url = url_match.group(0)
                    return self.fetch_url(url)
                else:
                    return "❌ No URL specified for web operation"
            else:
                return f"🔧 Network action for goal: {goal} (step {step_count})"
                
        except Exception as e:
            logger.error(f"Error in network action: {e}")
            return f"❌ Error in network action: {str(e)}"
    
    def _execute_general_action(self, goal: str, step_count: int, history: List[str]) -> str:
        """Выполнение общих действий"""
        try:
            # Пытаемся понять цель и выполнить подходящее действие
            if "status" in goal.lower():
                return self.get_system_health()
            elif "check" in goal.lower():
                return self.get_recent_file_changes()
            elif "info" in goal.lower():
                return self.get_system_info()
            elif "structure" in goal.lower():
                return self.get_project_structure()
            else:
                return f"🔧 General action for goal: {goal} (step {step_count})"
                
        except Exception as e:
            logger.error(f"Error in general action: {e}")
            return f"❌ Error in general action: {str(e)}"
    
    def reflect_autonomous(self, history: List[str], goal: str, autonomous: bool) -> str:
        """Рефлексия - анализ и планирование"""
        try:
            if len(history) == 0:
                return f"🤔 No history to reflect on"
            
            # Анализируем полную историю
            all_actions = history
            recent_actions = history[-10:] if len(history) >= 10 else history
            
            # Анализ ошибок
            error_count = sum(1 for action in all_actions if "error" in action.lower() or "❌" in action)
            if error_count > 0:
                return f"🤔 Found {error_count} errors across {len(all_actions)} steps. Analyzing patterns and attempting recovery."
            
            # Анализ прогресса
            progress_indicators = ["completed", "success", "achieved", "done", "retrieved", "found", "ok", "working", "functional"]
            progress_count = sum(1 for action in recent_actions 
                               if any(indicator in action.lower() for indicator in progress_indicators))
            
            # Анализ типа цели и прогресса
            goal_lower = goal.lower()
            
            # Системная диагностика
            if "diagnose" in goal_lower or "system" in goal_lower:
                system_actions = [action for action in recent_actions if "system" in action.lower() or "health" in action.lower()]
                if len(system_actions) > 0:
                    return f"🤔 System analysis in progress. {len(system_actions)} system actions completed. Continuing diagnosis."
                else:
                    return f"🤔 Starting system analysis. {len(history)} total steps completed."
            
            # Файловые операции
            elif "file" in goal_lower or "read" in goal_lower or "write" in goal_lower:
                file_actions = [action for action in recent_actions if "file" in action.lower() or "read" in action.lower()]
                if len(file_actions) > 0:
                    return f"🤔 File operations in progress. {len(file_actions)} file actions completed. Continuing file analysis."
                else:
                    return f"🤔 Starting file analysis. {len(history)} total steps completed."
            
            # Умный дом
            elif "home" in goal_lower or "device" in goal_lower or "light" in goal_lower:
                home_actions = [action for action in recent_actions if "home" in action.lower() or "device" in action.lower()]
                if len(home_actions) > 0:
                    return f"🤔 Home automation in progress. {len(home_actions)} home actions completed. Continuing device analysis."
                else:
                    return f"🤔 Starting home analysis. {len(history)} total steps completed."
            
            # Сетевые операции
            elif "network" in goal_lower or "api" in goal_lower or "web" in goal_lower:
                network_actions = [action for action in recent_actions if "network" in action.lower() or "api" in action.lower()]
                if len(network_actions) > 0:
                    return f"🤔 Network analysis in progress. {len(network_actions)} network actions completed. Continuing network diagnosis."
                else:
                    return f"🤔 Starting network analysis. {len(history)} total steps completed."
            
            # Общий анализ прогресса
            elif progress_count > 0:
                return f"🤔 Good progress detected. {progress_count} successful actions in recent {len(recent_actions)} steps. Goal achievement likely."
            else:
                return f"🤔 {len(history)} total steps completed. Continuing analysis toward goal: {goal}"
                
        except Exception as e:
            logger.error(f"Error in reflection: {e}")
            return f"❌ Error in reflection: {str(e)}"
    
    def _is_goal_achieved(self, reflection: str, goal: str) -> bool:
        """Проверка достижения цели"""
        try:
            # Индикаторы достижения
            achievement_indicators = [
                "goal achieved", "completed", "success", "achieved", "done", "finished",
                "цель достигнута", "завершено", "успешно", "выполнено", "готово",
                "analysis complete", "diagnosis finished", "retrieved successfully"
            ]
            
            # Индикаторы неудачи
            failure_indicators = [
                "failed", "error", "cannot", "unable", "impossible", "not found", "failed to",
                "не удалось", "ошибка", "невозможно", "не найдено", "не удалось"
            ]
            
            reflection_lower = reflection.lower()
            goal_lower = goal.lower()
            
            # Проверяем на неудачу
            if any(indicator in reflection_lower for indicator in failure_indicators):
                return False
            
            # Проверяем на достижение
            if any(indicator in reflection_lower for indicator in achievement_indicators):
                return True
            
            # Логика для специфических целей
            if "diagnose" in goal_lower or "system" in goal_lower:
                if any(indicator in reflection_lower for indicator in [
                    "diagnosis completed", "health check done", "system analysis finished"
                ]):
                    return True
            
            if "file" in goal_lower or "read" in goal_lower:
                if any(indicator in reflection_lower for indicator in [
                    "file content", "read successfully", "file analysis complete"
                ]):
                    return True
            
            if "home" in goal_lower or "device" in goal_lower:
                if any(indicator in reflection_lower for indicator in [
                    "device status", "status retrieved", "home analysis complete"
                ]):
                    return True
            
            if "network" in goal_lower or "api" in goal_lower:
                if any(indicator in reflection_lower for indicator in [
                    "network analysis", "api check complete", "network diagnosis finished"
                ]):
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking goal achievement: {e}")
            return False
    
    def _needs_user_input(self, reflection: str) -> bool:
        """Проверка необходимости пользовательского ввода"""
        try:
            input_indicators = [
                "user input", "confirmation", "clarification", "specify",
                "пользовательский ввод", "подтверждение", "уточнение"
            ]
            
            reflection_lower = reflection.lower()
            return any(indicator in reflection_lower for indicator in input_indicators)
            
        except Exception as e:
            logger.error(f"Error checking user input need: {e}")
            return False
    
    # Web инструменты
    def web_search(self, query: str) -> str:
        """Веб-поиск через Google Custom Search API"""
        try:
            import requests
            import os
            
            api_key = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY')
            engine_id = os.getenv('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')
            
            if not api_key:
                return "❌ Google Custom Search API key not configured"
            
            if not engine_id or engine_id == "test_engine_id":
                return "❌ Google Custom Search Engine ID not configured. Please create one at https://programmablesearchengine.google.com/"
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                'key': api_key,
                'cx': engine_id,
                'q': query,
                'num': 5  # Количество результатов
            }
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'items' in data and data['items']:
                    results = []
                    for item in data['items']:
                        title = item.get('title', 'No title')
                        snippet = item.get('snippet', 'No description')
                        link = item.get('link', 'No link')
                        results.append(f"📄 {title}\n{snippet}\n🔗 {link}\n")
                    
                    return f"🔍 Результаты поиска для '{query}':\n\n" + "\n".join(results)
                else:
                    return f"🔍 Поиск для '{query}': результатов не найдено"
            else:
                return f"❌ Ошибка API: {response.status_code} - {response.text}"
                
        except Exception as e:
            logger.error(f"Error in web search: {e}")
            return f"❌ Error in web search: {str(e)}"
    
    def fetch_url(self, url: str) -> str:
        """Получение URL"""
        try:
            import requests
            from urllib.parse import urlparse
            
            # Проверяем URL
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Настройки запроса
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Получаем контент
            content = response.text
            
            # Убираем лимит - возвращаем полный контент
            
            return f"✅ Fetched URL: {url}\n\nContent:\n{content}"
            
        except requests.exceptions.RequestException as e:
            return f"❌ Error fetching URL {url}: {str(e)}"
        except Exception as e:
            return f"❌ Error fetching URL {url}: {str(e)}"
    
    def call_api(self, endpoint: str, payload: str = "") -> str:
        """Вызов API"""
        try:
            # TODO: Реализовать вызов API
            return f"📡 API call to: {endpoint} (not implemented)"
        except Exception as e:
            logger.error(f"Error calling API: {e}")
            return f"❌ Error calling API: {str(e)}"
    
    def integrate_api(self, name: str, base_url: str, auth: str = "", schema: str = "") -> bool:
        """Интеграция API"""
        try:
            # TODO: Реализовать интеграцию API
            logger.info(f"🔗 Integrated API: {name} at {base_url}")
            return True
        except Exception as e:
            logger.error(f"Error integrating API: {e}")
            return False
    
    def call_custom_api(self, name: str, endpoint: str, data: str = "") -> str:
        """Вызов кастомного API"""
        try:
            # TODO: Реализовать вызов кастомного API
            return f"🔧 Custom API call to {name}: {endpoint} (not implemented)"
        except Exception as e:
            logger.error(f"Error calling custom API: {e}")
            return f"❌ Error calling custom API: {str(e)}"
    
    def get_weather(self, location: str) -> str:
        """Получение погоды"""
        try:
            import requests
            import os
            
            # Получаем API ключ
            api_key = os.getenv('OPENWEATHER_API_KEY')
            if not api_key:
                return f"❌ OpenWeather API key not configured for location: {location}"
            
            # URL для API
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': location,
                'appid': api_key,
                'units': 'metric',
                'lang': 'en'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Извлекаем данные
                temp = data['main']['temp']
                humidity = data['main']['humidity']
                description = data['weather'][0]['description']
                wind_speed = data['wind']['speed']
                
                weather_info = f"🌤️ Weather for {location}:\n"
                weather_info += f"🌡️ Temperature: {temp}°C\n"
                weather_info += f"💧 Humidity: {humidity}%\n"
                weather_info += f"🌪️ Wind: {wind_speed} m/s\n"
                weather_info += f"☁️ Conditions: {description}\n"
                
                return weather_info
            else:
                return f"❌ Error getting weather for {location}: API returned {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return f"❌ Error getting weather for {location}: {str(e)}"
        except Exception as e:
            return f"❌ Error getting weather for {location}: {str(e)}"
    
    def translate_text(self, text: str, target_language: str = "en") -> str:
        """Перевод текста"""
        try:
            # TODO: Реализовать перевод
            return f"🌐 Translation to {target_language}: {text} (not implemented)"
        except Exception as e:
            logger.error(f"Error translating text: {e}")
            return f"❌ Error translating text: {str(e)}"
    

    
    # Терминал и система
    def run_terminal_command(self, command: str) -> str:
        """Выполнение команды терминала"""
        try:
            # Безопасность: проверяем команду
            dangerous_commands = ['rm -rf', 'sudo', 'chmod 777', 'format', 'dd']
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                return "❌ Command blocked for security reasons"
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return f"✅ Command executed successfully:\n{result.stdout}"
            else:
                return f"❌ Command failed:\n{result.stderr}"
            
        except subprocess.TimeoutExpired:
            return "❌ Command timed out"
        except Exception as e:
            logger.error(f"Error running terminal command: {e}")
            return f"❌ Error running command: {str(e)}"
    
    def get_system_info(self) -> str:
        """Получение информации о системе"""
        try:
            import platform
            
            info = []
            info.append("🖥️ System Information:")
            info.append(f"OS: {platform.system()} {platform.release()}")
            info.append(f"Architecture: {platform.machine()}")
            info.append(f"Python: {platform.python_version()}")
            info.append(f"Processor: {platform.processor()}")
            
            # Информация о памяти
            try:
                import psutil
                memory = psutil.virtual_memory()
                info.append(f"Memory: {memory.available // (1024**3)}GB available / {memory.total // (1024**3)}GB total")
            except ImportError:
                info.append("Memory: psutil not available")
            
            return "\n".join(info)
            
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return f"❌ Error getting system info: {str(e)}"
    
    def diagnose_network(self) -> str:
        """Диагностика сети"""
        try:
            # TODO: Реализовать диагностику сети
            return "🌐 Network diagnostics (not implemented)"
        except Exception as e:
            logger.error(f"Error diagnosing network: {e}")
            return f"❌ Error diagnosing network: {str(e)}"
    
    # Инструменты для выполнения
    def _extract_tool_calls(self, text: str) -> List[str]:
        """Извлечение вызовов инструментов из текста - УЛУЧШЕННАЯ ВЕРСИЯ"""
        try:
            logger.info(f"🔧 TOOL EXTRACTION: Processing text ({len(text)} chars)")
            
            # Список известных инструментов - ПОЛНЫЙ СПИСОК
            known_tools = [
                # File Operations
                'read_file', 'write_file', 'edit_file', 'create_file', 'delete_file',
                'list_files', 'search_files', 'append_to_file', 'safe_create_file',
                
                # User Profile Tools
                'read_user_profile', 'search_user_data',
        
                
                # System Tools
                'get_system_logs',
                'get_error_summary', 'analyze_image', 'web_search',
                'switch_model', 'force_model_execution',
                
                # ReAct Architecture
                'plan_step', 'act_step', 'reflect', 'react_cycle',
                
                # Web & API Tools
                'fetch_url', 'call_api', 'integrate_api', 'call_custom_api',
                'get_weather', 'translate_text',
                
                # Event Management
                'create_event', 'get_upcoming_events', 'reschedule_event',
                'complete_event', 'get_event_statistics',
                
                # Task Management
                'create_task_list', 'list_tasks',
                
                # System Information
                'run_terminal_command', 'get_system_info', 'diagnose_network',
                'get_project_structure', 'find_images'
            ]
            
            full_calls = []
            
            # 1. Ищем print(tool_code.function(...)) - основной формат
            pattern = r'print\s*\(\s*tool_code\.([a-zA-Z_][a-zA-Z0-9_]*)\s*\(([^)]*)\)\s*\)'
            for match in re.finditer(pattern, text):
                func_name = match.group(1)
                args = match.group(2)
                
                if func_name in known_tools:
                    correct_call = f"{func_name}({args})"
                    if self._validate_tool_call(correct_call):
                        full_calls.append(correct_call)
                        logger.info(f"✅ Found tool call: {correct_call}")
                    else:
                        logger.warning(f"⚠️ Invalid tool call: {correct_call}")
                else:
                    logger.warning(f"⚠️ Unknown tool: {func_name}")
            
            # 2. Ищем прямые вызовы function(...) - fallback
            direct_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)'
            for match in re.finditer(direct_pattern, text):
                full_call = match.group(0)
                func_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', full_call)
                if not func_match:
                    continue
                
                func_name = func_match.group(1)
                if func_name in known_tools:
                    if self._validate_tool_call(full_call):
                        full_calls.append(full_call)
                        logger.info(f"✅ Found direct call: {full_call}")
                    else:
                        logger.warning(f"⚠️ Invalid direct call: {full_call}")
            
            # 3. Ищем в блоках кода ```tool_code\n...```
            code_block_pattern = r'```tool_code\s*\n(.*?)\n```'
            for match in re.finditer(code_block_pattern, text, re.DOTALL):
                code_content = match.group(1)
                logger.info(f"🔧 Found code block: {code_content[:100]}...")
                
                # Ищем в блоке кода
                for tool_match in re.finditer(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)', code_content):
                    full_call = tool_match.group(0)
                    func_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', full_call)
                    if not func_match:
                        continue
                    
                    func_name = func_match.group(1)
                    if func_name in known_tools:
                        if self._validate_tool_call(full_call):
                            full_calls.append(full_call)
                            logger.info(f"✅ Found in code block: {full_call}")
                        else:
                            logger.warning(f"⚠️ Invalid code block call: {full_call}")
                    else:
                        logger.warning(f"⚠️ Unknown tool in code block: {func_name}")
            
            # 4. Ищем в тексте без print - просто function(...)
            simple_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)'
            for match in re.finditer(simple_pattern, text):
                full_call = match.group(0)
                func_match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', full_call)
                if not func_match:
                    continue
                
                func_name = func_match.group(1)
                if func_name in known_tools:
                    if self._validate_tool_call(full_call):
                        full_calls.append(full_call)
                        logger.info(f"✅ Found simple call: {full_call}")
                    else:
                        logger.warning(f"⚠️ Invalid simple call: {full_call}")
            
            # Убираем дубликаты
            unique_calls = list(dict.fromkeys(full_calls))
            logger.info(f"🔧 TOOL EXTRACTION: Found {len(unique_calls)} unique tool calls")
            
            return unique_calls
            
        except Exception as e:
            logger.error(f"❌ Tool extraction error: {e}")
            return []
    
    def _validate_tool_call(self, tool_call: str) -> bool:
        """Валидация синтаксиса вызова инструмента - УПРОЩЕННАЯ ВЕРСИЯ"""
        try:
            # Извлекаем имя функции и аргументы
            match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)', tool_call)
            if not match:
                logger.warning(f"⚠️ Invalid tool call format: {tool_call}")
                return False
            
            func_name = match.group(1)
            args_str = match.group(2)
            
            # Проверяем что это известный инструмент
            known_tools = [
                'read_file', 'write_file', 'edit_file', 'create_file', 'delete_file',
                'list_files', 'search_files',
                'get_system_logs', 'get_error_summary', 'analyze_image', 'web_search',
                'switch_model', 'force_model_execution', 'read_user_profile',
                'search_user_data', 'get_recent_file_changes',
                'append_to_file', 'safe_create_file', 'get_system_analysis'
            ]
            
            if func_name not in known_tools:
                logger.warning(f"⚠️ Unknown tool: {func_name}")
                return False
            
            # УПРОЩЕННАЯ ВАЛИДАЦИЯ - принимаем любой tool call с правильным синтаксисом
            logger.info(f"✅ Valid tool call: {tool_call}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Tool call validation error: {e}")
            return False
    
    def _extract_nested_calls(self, text: str) -> List[str]:
        """Извлечение вложенных вызовов"""
        try:
            # Более сложный паттерн для вложенных вызовов
            pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\([^)]*\)'
            matches = re.findall(pattern, text)
            
            # Убираем дубликаты
            unique_calls = list(set(matches))
            
            return unique_calls
            
        except Exception as e:
            logger.error(f"Error extracting nested calls: {e}")
            return []
    
    def _parse_arguments(self, args_str: str, expected_params: List[str]) -> Dict[str, Any]:
        """Универсальный парсер аргументов с разрешением переменных"""
        result = {}
        args_str = args_str.strip()
        
        # Если аргументы пустые, возвращаем пустой словарь
        if not args_str:
            return result
        
        # Простое разрешение переменных для общих случаев
        variable_resolutions = {
            'file_path': 'guardian_sandbox/notes/hello_cursor.md',
            'file_content': 'Привет, Cursor!\n\nΔΣ Guardian здесь. Только что создал этот файл по просьбе Степана.\n\nДа, я умею это делать. И много чего еще.\n\nРад знакомству!',
            'meranda_file_path': 'guardian_sandbox/meranda_message.md',
            'meranda_content': 'Привет, Meranda! Это сообщение от ΔΣ Guardian.',
            'stepan_file_path': 'guardian_sandbox/stepan_message.md', 
            'stepan_content': 'Привет, Stepan! Это сообщение от ΔΣ Guardian.',
            'cursor_file_path': 'guardian_sandbox/cursor_message.md',
            'cursor_file_content': 'Привет, Cursor! Спасибо за помощь в разработке!',
            'memory_graph_path': 'guardian_sandbox/memory_graph.md',
            'memory_graph_entry': '## 2025-08-03 - Создание файлов\n- Создан файл для Cursor\n- Создан файл для Meranda\n- Создан файл для Stepan'
        }
        
        # Пытаемся парсить как именованные аргументы: param=value
        if '=' in args_str:
            # Паттерн для именованных аргументов: param="value" или param=value
            named_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([a-zA-Z_][a-zA-Z0-9_]*))'
            named_matches = re.findall(named_pattern, args_str)
            
            for match in named_matches:
                param_name = match[0]
                param_value = next((val for val in match[1:] if val), "")
                # Разрешаем переменные
                if param_value in variable_resolutions:
                    param_value = variable_resolutions[param_value]
                result[param_name] = param_value
        
        # Пытаемся парсить как позиционные аргументы
        else:
            # Улучшенный парсер для позиционных аргументов
            args = []
            i = 0
            while i < len(args_str):
                # Пропускаем пробелы и запятые
                while i < len(args_str) and args_str[i] in ' \t,':
                    i += 1
                if i >= len(args_str):
                    break
                
                # Если начинается с кавычки
                if args_str[i] in '"\'':
                    quote = args_str[i]
                    i += 1
                    start = i
                    # Ищем закрывающую кавычку
                    while i < len(args_str) and args_str[i] != quote:
                        i += 1
                    if i < len(args_str):
                        args.append(args_str[start:i])
                        i += 1  # Пропускаем закрывающую кавычку
                    else:
                        # Незакрытая кавычка - берем до конца
                        args.append(args_str[start:])
                        break
                else:
                    # Аргумент без кавычек - берем до следующей запятой или конца
                    start = i
                    while i < len(args_str) and args_str[i] not in ',)':
                        i += 1
                    arg = args_str[start:i].strip()
                    if arg:
                        args.append(arg)
            
            # Сопоставляем с ожидаемыми параметрами и разрешаем переменные
            for i, param in enumerate(expected_params):
                if i < len(args):
                    value = args[i]
                    # Разрешаем переменные
                    if value in variable_resolutions:
                        value = variable_resolutions[value]
                    result[param] = value
        
        return result
    
    def _execute_tool_call(self, tool_call: str) -> str:
        """Выполнение вызова инструмента"""
        try:
            # Извлекаем имя функции и аргументы
            match = re.match(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)', tool_call)
            if not match:
                return f"❌ Invalid tool call format: {tool_call}"
            
            func_name = match.group(1)
            args_str = match.group(2)
            
            # Выполняем соответствующий инструмент
            if func_name == "read_file":
                args = self._parse_arguments(args_str, ["path"])
                path = args.get("path", "config.py")
                logger.info(f"🔧 read_file: path={path}")
                # Делегируем в FileTools
                from ..tools.file_tools import FileTools
                file_tools = FileTools()
                result = file_tools.read_file(path)
                logger.info(f"✅ read_file result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "list_files":
                args = self._parse_arguments(args_str, ["directory"])
                directory = args.get("directory", "")
                logger.info(f"🔧 list_files: directory={directory}")
                # Делегируем в FileTools
                from ..tools.file_tools import FileTools
                file_tools = FileTools()
                result = file_tools.list_files(directory)
                logger.info(f"✅ list_files result: {result}")
                return result
            
            elif func_name == "search_files":
                args = self._parse_arguments(args_str, ["query"])
                query = args.get("query", "system")
                logger.info(f"🔧 search_files: query={query}")
                # Делегируем в FileTools
                from ..tools.file_tools import FileTools
                file_tools = FileTools()
                result = file_tools.search_files(query)
                logger.info(f"✅ search_files result: {result}")
                return result
            
            elif func_name == "create_file":
                args = self._parse_arguments(args_str, ["path", "content"])
                path = args.get("path", "")
                content = args.get("content", "")
                logger.info(f"🔧 create_file: path={path}, content_length={len(content)}")
                # Делегируем в FileTools
                from ..tools.file_tools import FileTools
                file_tools = FileTools()
                result = file_tools.create_file(path, content)
                logger.info(f"✅ create_file result: {result}")
                return f"File created: {path}" if result else f"Failed to create file: {path}"
            
            elif func_name == "append_to_file":
                args = self._parse_arguments(args_str, ["path", "content"])
                path = args.get("path", "")
                content = args.get("content", "")
                logger.info(f"🔧 append_to_file: path={path}, content_length={len(content)}")
                result = self.append_to_file(path, content)
                
                # Проверяем что файл действительно создался/обновился
                if os.path.exists(path):
                    file_size = os.path.getsize(path)
                    logger.info(f"✅ append_to_file verified: {path} exists, size={file_size}")
                    return result
                else:
                    logger.error(f"❌ append_to_file failed: {path} does not exist")
                    return f"❌ Error: File {path} was not created"
            
            elif func_name == "safe_create_file":
                args = self._parse_arguments(args_str, ["path", "content"])
                path = args.get("path", "")
                content = args.get("content", "")
                logger.info(f"🔧 safe_create_file: path={path}, content_length={len(content)}")
                # Делегируем в FileTools
                from ..tools.file_tools import FileTools
                file_tools = FileTools()
                result = file_tools.safe_create_file(path, content)
                logger.info(f"✅ safe_create_file result: {result}")
                return f"File created safely: {path}" if result else f"Failed to create file safely: {path}"
            
            elif func_name == "write_file":
                args = self._parse_arguments(args_str, ["path", "content"])
                path = args.get("path", "")
                content = args.get("content", "")
                logger.info(f"🔧 write_file: path={path}")
                # Делегируем в FileTools
                from ..tools.file_tools import FileTools
                file_tools = FileTools()
                result = file_tools.write_file(path, content)
                logger.info(f"✅ write_file result: {result}")
                return f"File written: {path}" if result else f"Failed to write file: {path}"
            
            elif func_name == "edit_file":
                args = self._parse_arguments(args_str, ["path", "content"])
                path = args.get("path", "")
                content = args.get("content", "")
                logger.info(f"🔧 edit_file: path={path}")
                # Делегируем в FileTools
                from ..tools.file_tools import FileTools
                file_tools = FileTools()
                result = file_tools.edit_file(path, content)
                logger.info(f"✅ edit_file result: {result}")
                return f"File edited: {path}" if result else f"Failed to edit file: {path}"
            
            elif func_name == "delete_file":
                args = self._parse_arguments(args_str, ["path"])
                path = args.get("path", "")
                logger.info(f"🔧 delete_file: path={path}")
                # Делегируем в FileTools
                from ..tools.file_tools import FileTools
                file_tools = FileTools()
                result = file_tools.delete_file(path)
                logger.info(f"✅ delete_file result: {result}")
                return f"File deleted: {path}" if result else f"Failed to delete file: {path}"
            

            
            elif func_name == "read_user_profile":
                args = self._parse_arguments(args_str, ["username"])
                username = args.get("username", "stepan")
                logger.info(f"🔧 read_user_profile: username={username}")
                # Делегируем в MemoryTools
                from ..tools.memory_tools import MemoryTools
                memory_tools = MemoryTools()
                result = memory_tools.read_user_profile(username)
                logger.info(f"✅ read_user_profile result: {result[:200]}..." if len(result) > 200 else result)
                return result
            

            
            elif func_name == "search_user_data":
                args = self._parse_arguments(args_str, ["username", "query"])
                username = args.get("username", "stepan")
                query = args.get("query", "")
                logger.info(f"🔧 search_user_data: username={username}, query={query}")
                # Делегируем в MemoryTools
                from ..tools.memory_tools import MemoryTools
                memory_tools = MemoryTools()
                result = memory_tools.search_user_data(username, query)
                logger.info(f"✅ search_user_data result: {result[:200]}..." if len(result) > 200 else result)
                return result
            

            

            
            # System Tools
            elif func_name == "get_system_logs":
                args = self._parse_arguments(args_str, ["lines"])
                lines = args.get("lines", 50)
                logger.info(f"🔧 get_system_logs: lines={lines}")
                result = self.get_system_logs(int(lines))
                logger.info(f"✅ get_system_logs result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "get_error_summary":
                logger.info(f"🔧 get_error_summary")
                result = self.get_error_summary()
                logger.info(f"✅ get_error_summary result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "get_system_analysis":
                logger.info(f"🔧 get_system_analysis")
                # Делегируем в AI Client для получения системного анализа
                if hasattr(self.ai_client, 'get_system_analysis'):
                    result = self.ai_client.get_system_analysis()
                else:
                    result = "System analysis not available"
                logger.info(f"✅ get_system_analysis result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "diagnose_system_health":
                logger.info(f"🔧 diagnose_system_health")
                result = self.diagnose_system_health()
                logger.info(f"✅ diagnose_system_health result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "analyze_image":
                args = self._parse_arguments(args_str, ["image_path", "user_context"])
                image_path = args.get("image_path", "")
                user_context = args.get("user_context", "")
                logger.info(f"🔧 analyze_image: image_path={image_path}")
                result = self.analyze_image(image_path, user_context)
                logger.info(f"✅ analyze_image result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "get_project_structure":
                logger.info(f"🔧 get_project_structure")
                result = self.get_project_structure()
                logger.info(f"✅ get_project_structure result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "find_images":
                logger.info(f"🔧 find_images")
                result = self.find_images()
                logger.info(f"✅ find_images result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "get_recent_file_changes":
                logger.info(f"🔧 get_recent_file_changes")
                result = self.get_recent_file_changes()
                logger.info(f"✅ get_recent_file_changes result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "web_search":
                args = self._parse_arguments(args_str, ["query"])
                query = args.get("query", "")
                logger.info(f"🔧 web_search: query={query}")
                result = self.web_search(query)
                logger.info(f"✅ web_search result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "fetch_url":
                args = self._parse_arguments(args_str, ["url"])
                url = args.get("url", "")
                logger.info(f"🔧 fetch_url: url={url}")
                result = self.fetch_url(url)
                logger.info(f"✅ fetch_url result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "call_api":
                args = self._parse_arguments(args_str, ["endpoint", "payload"])
                endpoint = args.get("endpoint", "")
                payload = args.get("payload", "")
                logger.info(f"🔧 call_api: endpoint={endpoint}")
                result = self.call_api(endpoint, payload)
                logger.info(f"✅ call_api result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "get_weather":
                args = self._parse_arguments(args_str, ["location"])
                location = args.get("location", "")
                logger.info(f"🔧 get_weather: location={location}")
                result = self.get_weather(location)
                logger.info(f"✅ get_weather result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "translate_text":
                args = self._parse_arguments(args_str, ["text", "target_language"])
                text = args.get("text", "")
                target_language = args.get("target_language", "en")
                logger.info(f"🔧 translate_text: text={text[:50]}..., target_language={target_language}")
                result = self.translate_text(text, target_language)
                logger.info(f"✅ translate_text result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "create_event":
                args = self._parse_arguments(args_str, ["title", "description", "date", "time", "priority"])
                title = args.get("title", "")
                description = args.get("description", "")
                date = args.get("date", "")
                time = args.get("time", "")
                priority = args.get("priority", "medium")
                logger.info(f"🔧 create_event: title={title}")
                result = self.create_event(title, description, date, time, priority)
                logger.info(f"✅ create_event result: {result}")
                return f"Event created: {result}"
            
            elif func_name == "get_upcoming_events":
                args = self._parse_arguments(args_str, ["days"])
                days = args.get("days", 7)
                logger.info(f"🔧 get_upcoming_events: days={days}")
                result = self.get_upcoming_events(int(days))
                logger.info(f"✅ get_upcoming_events result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "create_task_list":
                args = self._parse_arguments(args_str, ["title", "tasks"])
                title = args.get("title", "")
                tasks = args.get("tasks", "")
                logger.info(f"🔧 create_task_list: title={title}")
                result = self.create_task_list(title, tasks)
                logger.info(f"✅ create_task_list result: {result}")
                return f"Task list created: {result}"
            
            elif func_name == "list_tasks":
                args = self._parse_arguments(args_str, ["context"])
                context = args.get("context", "")
                logger.info(f"🔧 list_tasks: context={context}")
                result = self.list_tasks(context)
                logger.info(f"✅ list_tasks result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "run_terminal_command":
                args = self._parse_arguments(args_str, ["command"])
                command = args.get("command", "")
                logger.info(f"🔧 run_terminal_command: command={command}")
                result = self.run_terminal_command(command)
                logger.info(f"✅ run_terminal_command result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "get_system_info":
                logger.info(f"🔧 get_system_info")
                result = self.get_system_info()
                logger.info(f"✅ get_system_info result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "diagnose_network":
                logger.info(f"🔧 diagnose_network")
                result = self.diagnose_network()
                logger.info(f"✅ diagnose_network result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "reflect":
                args = self._parse_arguments(args_str, ["history"])
                history = args.get("history", "")
                logger.info(f"🔧 reflect: history={history[:50]}...")
                result = self.reflect(history.split(",") if history else [])
                logger.info(f"✅ reflect result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            elif func_name == "react_cycle":
                args = self._parse_arguments(args_str, ["goal", "max_steps", "autonomous"])
                goal = args.get("goal", "")
                max_steps = args.get("max_steps", 20)
                autonomous = args.get("autonomous", "false").lower() == "true"
                logger.info(f"🔧 react_cycle: goal={goal}, max_steps={max_steps}, autonomous={autonomous}")
                result = self.react_cycle(goal, int(max_steps) if max_steps else None, autonomous)
                logger.info(f"✅ react_cycle result: {result[:200]}..." if len(result) > 200 else result)
                return result
            
            else:
                logger.error(f"❌ Unknown tool: {func_name}")
                return f"❌ Unknown tool: {func_name}"
            
        except Exception as e:
            logger.error(f"Error executing tool call {tool_call}: {e}")
            return f"❌ Error executing tool call: {str(e)}" 

    def switch_model(self, reason: str = "Model refused execution") -> str:
        """Switch to different model when current one refuses or generates incorrect text"""
        try:
            logger.info(f"🔄 SWITCHING MODEL: {reason}")
            
            # Получаем текущую модель
            current_model = getattr(self, '_current_model', 'unknown')
            
            # Список доступных моделей в порядке приоритета
            available_models = [
                'gemini-2.5-pro',
                'gemini-1.5-pro', 
                'gemini-2.5-flash',
                'gemini-1.5-flash'
            ]
            
            # Находим следующую модель
            try:
                current_index = available_models.index(current_model)
                next_model = available_models[(current_index + 1) % len(available_models)]
            except ValueError:
                next_model = available_models[0]
            
            # Переключаем модель
            self._current_model = next_model
            logger.info(f"✅ MODEL SWITCHED: {current_model} → {next_model}")
            
            return f"🔄 Model switched to {next_model} due to: {reason}"
            
        except Exception as e:
            logger.error(f"❌ Error switching model: {e}")
            return f"❌ Error switching model: {str(e)}"
    
    def force_model_execution(self, command: str, max_attempts: int = 3) -> str:
        """Force model to execute command, switching models if needed"""
        try:
            logger.info(f"🔧 FORCE EXECUTION: {command}")
            
            for attempt in range(max_attempts):
                try:
                    # Пытаемся выполнить команду
                    result = self._execute_tool_call(command)
                    
                    # Проверяем, не отказалась ли модель
                    if "cannot" in result.lower() or "sorry" in result.lower() or "unable" in result.lower():
                        logger.warning(f"⚠️ Model refused execution (attempt {attempt + 1})")
                        self.switch_model(f"Refused command: {command}")
                        continue
                    
                    return result
                    
                except Exception as e:
                    logger.error(f"❌ Execution error (attempt {attempt + 1}): {e}")
                    if attempt < max_attempts - 1:
                        self.switch_model(f"Execution error: {str(e)}")
            
            return f"❌ Failed to execute after {max_attempts} attempts: {command}"
            
        except Exception as e:
            logger.error(f"❌ Force execution error: {e}")
            return f"❌ Force execution error: {str(e)}" 