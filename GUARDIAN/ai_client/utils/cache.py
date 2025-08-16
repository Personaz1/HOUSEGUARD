"""
Кэширование для оптимизации производительности
"""

import time
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SystemCache:
    """Кэш для системных операций"""
    
    def __init__(self):
        self.cache_dir = "cache"
        self.ensure_cache_dir()
        
        # Кэш в памяти для быстрого доступа
        self.memory_cache = {}
        
    def ensure_cache_dir(self):
        """Создаем директорию кэша если не существует"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logger.info(f"✅ Created cache directory: {self.cache_dir}")
    
    def get_cache_key(self, operation: str, params: Dict[str, Any] = None) -> str:
        """Генерируем ключ кэша"""
        import hashlib
        
        key_parts = [operation]
        if params:
            # Сортируем параметры для стабильности
            sorted_params = sorted(params.items())
            # Создаем короткий хеш от параметров
            params_str = json.dumps(sorted_params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            key_parts.append(params_hash)
        
        return "_".join(key_parts)
    
    def get(self, operation: str, params: Dict[str, Any] = None, ttl_seconds: int = 600) -> Optional[Dict[str, Any]]:
        """Получить данные из кэша"""
        try:
            cache_key = self.get_cache_key(operation, params)
            
            # Проверяем память
            if cache_key in self.memory_cache:
                cached_data = self.memory_cache[cache_key]
                if time.time() - cached_data["timestamp"] < ttl_seconds:
                    logger.info(f"✅ Cache HIT (memory): {operation}")
                    return cached_data["data"]
                else:
                    del self.memory_cache[cache_key]
            
            # Проверяем файл
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    
                    if time.time() - cached_data["timestamp"] < ttl_seconds:
                        # Загружаем в память
                        self.memory_cache[cache_key] = cached_data
                        logger.info(f"✅ Cache HIT (file): {operation}")
                        return cached_data["data"]
                    else:
                        # Удаляем устаревший файл
                        os.remove(cache_file)
                        logger.info(f"🗑️ Removed expired cache: {operation}")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"⚠️ Corrupted cache file {cache_file}: {e}")
                    try:
                        os.remove(cache_file)
                    except:
                        pass
            
            logger.info(f"❌ Cache MISS: {operation}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Cache get error: {e}")
            return None
    
    def set(self, operation: str, data: Dict[str, Any], params: Dict[str, Any] = None, ttl_seconds: int = 600):
        """Сохранить данные в кэш"""
        try:
            cache_key = self.get_cache_key(operation, params)
            cache_data = {
                "data": data,
                "timestamp": time.time(),
                "ttl_seconds": ttl_seconds,
                "created_at": datetime.now().isoformat()
            }
            
            # Сохраняем в память
            self.memory_cache[cache_key] = cache_data
            
            # Сохраняем в файл
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"💾 Cache SET: {operation} (TTL: {ttl_seconds}s)")
            
        except Exception as e:
            logger.error(f"❌ Cache set error: {e}")
    
    def invalidate(self, operation: str, params: Dict[str, Any] = None):
        """Инвалидировать кэш"""
        try:
            cache_key = self.get_cache_key(operation, params)
            
            # Удаляем из памяти
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
            
            # Удаляем файл
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)
            
            logger.info(f"🗑️ Cache INVALIDATED: {operation}")
            
        except Exception as e:
            logger.error(f"❌ Cache invalidate error: {e}")
    
    def delete(self, cache_key: str):
        """Удалить кэш по ключу (для совместимости)"""
        try:
            # Удаляем из памяти
            if cache_key in self.memory_cache:
                del self.memory_cache[cache_key]
            
            # Удаляем файл
            cache_file = os.path.join(self.cache_dir, f"{cache_key}.json")
            if os.path.exists(cache_file):
                os.remove(cache_file)
                logger.info(f"🗑️ Deleted cache: {cache_key}")
            
        except Exception as e:
            logger.error(f"❌ Cache delete error: {e}")
    
    def clear_all(self):
        """Очистить весь кэш"""
        try:
            # Очищаем память
            self.memory_cache.clear()
            
            # Очищаем файлы
            for file in os.listdir(self.cache_dir):
                if file.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, file))
            
            logger.info("🗑️ Cache CLEARED: All data removed")
            
        except Exception as e:
            logger.error(f"❌ Cache clear error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику кэша"""
        try:
            memory_count = len(self.memory_cache)
            file_count = len([f for f in os.listdir(self.cache_dir) if f.endswith('.json')])
            
            return {
                "memory_entries": memory_count,
                "file_entries": file_count,
                "cache_dir": self.cache_dir
            }
            
        except Exception as e:
            logger.error(f"❌ Cache stats error: {e}")
            return {"error": str(e)}

# Глобальный экземпляр кэша
system_cache = SystemCache() 