"""
Сервис для кэширования сообщений с целью дедупликации
"""
import logging
from typing import Optional, Dict
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)


class MessageCacheService:
    """
    Сервис для кэширования обработанных сообщений
    Используется для предотвращения сохранения дубликатов
    """
    
    def __init__(self, ttl_hours: int = 1):
        """
        Args:
            ttl_hours: Время жизни кэша в часах (по умолчанию 1 час)
        """
        # Структура: meeting_id -> {composite_id: {text, version, processed_at}}
        self._cache: Dict[str, Dict[str, Dict]] = {}
        self.ttl_hours = ttl_hours
    
    def get_cache_key(self, meeting_id: str, message_id: Optional[int], device_id: str) -> str:
        """
        Генерирует ключ кэша для сообщения
        
        Args:
            meeting_id: ID встречи
            message_id: ID сообщения
            device_id: ID устройства
        
        Returns:
            Ключ кэша
        """
        msg_id_str = str(message_id) if message_id is not None else "none"
        return f"{meeting_id}:messages:{msg_id_str}/{device_id}"
    
    def is_duplicate(
        self,
        meeting_id: str,
        message_id: Optional[int],
        device_id: str,
        text: str,
        version: int
    ) -> bool:
        """
        Проверяет, является ли сообщение дубликатом
        
        Args:
            meeting_id: ID встречи
            message_id: ID сообщения
            device_id: ID устройства
            text: Текст сообщения
            version: Версия сообщения
        
        Returns:
            True если дубликат, False если новое сообщение
        """
        if meeting_id not in self._cache:
            return False
        
        cache_key = self.get_cache_key(meeting_id, message_id, device_id)
        
        if cache_key not in self._cache[meeting_id]:
            return False
        
        cached = self._cache[meeting_id][cache_key]
        
        # Проверяем TTL
        if cached["processed_at"] + timedelta(hours=self.ttl_hours) < datetime.now(timezone.utc):
            # Истек TTL, удаляем из кэша
            del self._cache[meeting_id][cache_key]
            if not self._cache[meeting_id]:
                del self._cache[meeting_id]
            return False
        
        # Если текст совпадает - это дубликат
        if cached["text"] == text and cached["version"] == version:
            return True
        
        # Если текст отличается - обновляем кэш
        return False
    
    def cache_message(
        self,
        meeting_id: str,
        message_id: Optional[int],
        device_id: str,
        text: str,
        version: int
    ) -> None:
        """
        Сохраняет сообщение в кэш
        
        Args:
            meeting_id: ID встречи
            message_id: ID сообщения
            device_id: ID устройства
            text: Текст сообщения
            version: Версия сообщения
        """
        if meeting_id not in self._cache:
            self._cache[meeting_id] = {}
        
        cache_key = self.get_cache_key(meeting_id, message_id, device_id)
        
        self._cache[meeting_id][cache_key] = {
            "text": text,
            "version": version,
            "processed_at": datetime.now(timezone.utc)
        }
    
    def cleanup_expired(self) -> None:
        """
        Очищает истекшие записи из кэша
        """
        now = datetime.now(timezone.utc)
        expired_count = 0
        
        for meeting_id in list(self._cache.keys()):
            for cache_key in list(self._cache[meeting_id].keys()):
                cached = self._cache[meeting_id][cache_key]
                if cached["processed_at"] + timedelta(hours=self.ttl_hours) < now:
                    del self._cache[meeting_id][cache_key]
                    expired_count += 1
            
            # Удаляем пустые встречи
            if not self._cache[meeting_id]:
                del self._cache[meeting_id]
        
        if expired_count > 0:
            logger.info(f"Cleaned up {expired_count} expired cache entries")


# Глобальный экземпляр сервиса кэширования
message_cache_service = MessageCacheService()

