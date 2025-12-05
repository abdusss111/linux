"""
Сервис для управления маппингом участников встречи (device_id -> имя)
Хранит маппинг в памяти с возможностью расширения на Redis
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timezone, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class MappingService:
    """
    Сервис для управления маппингом участников встречи.
    Хранит соответствие device_id -> имя участника и индексирует варианты для быстрого поиска.
    """
    
    def __init__(self, ttl_hours: int = 24):
        """
        Args:
            ttl_hours: Время жизни маппинга в часах (по умолчанию 24 часа)
        """
        # Структура: meeting_id -> {device_id: {name, variants, updated_at}}
        self._mapping: Dict[str, Dict[str, Dict]] = {}
        # Индекс для быстрого поиска: meeting_id -> {variant: device_id}
        self._index: Dict[str, Dict[str, str]] = defaultdict(dict)
        self.ttl_hours = ttl_hours
        self._cleanup_times: Dict[str, datetime] = {}
    
    def save_mapping(
        self,
        meeting_id: str,
        device_id: str,
        name: str,
        variants: List[str]
    ) -> None:
        """
        Сохраняет маппинг для участника
        
        Args:
            meeting_id: ID встречи
            device_id: Основной ID устройства
            name: Имя участника
            variants: Список вариантов device_id для поиска
        """
        if meeting_id not in self._mapping:
            self._mapping[meeting_id] = {}
            self._index[meeting_id] = {}
        
        now = datetime.now(timezone.utc)
        
        # Проверяем, был ли уже такой маппинг
        was_existing = device_id in self._mapping[meeting_id]
        old_name = self._mapping[meeting_id].get(device_id, {}).get("name") if was_existing else None
        
        # Сохраняем основной маппинг
        self._mapping[meeting_id][device_id] = {
            "name": name,
            "variants": variants,
            "updated_at": now
        }
        
        # Создаем индекс для всех вариантов
        all_variants = [device_id] + variants
        indexed_variants = []
        for variant in all_variants:
            if variant:  # Пропускаем пустые строки
                self._index[meeting_id][variant] = device_id
                indexed_variants.append(variant)
        
        # Обновляем время очистки
        self._cleanup_times[meeting_id] = now + timedelta(hours=self.ttl_hours)
        
        # Подробное логирование
        log_msg = (
            f"[MAPPING-SAVE] Meeting {meeting_id}: "
            f"device_id='{device_id}', name='{name}', "
            f"variants={variants}, "
            f"indexed_variants={indexed_variants}, "
            f"action={'UPDATED' if was_existing else 'CREATED'}"
        )
        if was_existing and old_name != name:
            log_msg += f", old_name='{old_name}'"
        
        logger.info(log_msg)
        print(log_msg)  # Дублируем в stdout
    
    def find_name_by_device_id(
        self,
        meeting_id: str,
        device_id: str
    ) -> Optional[str]:
        """
        Ищет имя участника по device_id
        
        Args:
            meeting_id: ID встречи
            device_id: ID устройства для поиска
        
        Returns:
            Имя участника или None если не найдено
        """
        if meeting_id not in self._mapping:
            log_msg = (
                f"[MAPPING-FIND] Meeting {meeting_id}: No mapping found for meeting, "
                f"device_id='{device_id}', "
                f"available_meetings={list(self._mapping.keys())}"
            )
            logger.warning(log_msg)
            print(log_msg)  # Дублируем в stdout
            return None
        
        # Стратегия поиска:
        # 1. Прямой поиск по device_id
        if device_id in self._mapping[meeting_id]:
            name = self._mapping[meeting_id][device_id]["name"]
            logger.debug(
                f"[MAPPING-FIND] Meeting {meeting_id}: Found via direct lookup - "
                f"device_id='{device_id}', name='{name}'"
            )
            return name
        
        # 2. Очистка device_id от спецсимволов (начальные \x00-\x1F)
        cleaned_id = self._clean_device_id(device_id)
        if cleaned_id and cleaned_id != device_id:
            if cleaned_id in self._mapping[meeting_id]:
                name = self._mapping[meeting_id][cleaned_id]["name"]
                logger.debug(
                    f"[MAPPING-FIND] Meeting {meeting_id}: Found via cleaned_id - "
                    f"device_id='{device_id}', cleaned_id='{cleaned_id}', name='{name}'"
                )
                return name
            # Проверка через индекс
            if cleaned_id in self._index[meeting_id]:
                mapped_id = self._index[meeting_id][cleaned_id]
                name = self._mapping[meeting_id][mapped_id]["name"]
                logger.debug(
                    f"[MAPPING-FIND] Meeting {meeting_id}: Found via cleaned_id index - "
                    f"device_id='{device_id}', cleaned_id='{cleaned_id}', "
                    f"mapped_id='{mapped_id}', name='{name}'"
                )
                return name
        
        # 3. Извлечение части после "devices/"
        if "devices/" in device_id:
            device_part = device_id.split("devices/")[-1]
            if device_part in self._index[meeting_id]:
                mapped_id = self._index[meeting_id][device_part]
                name = self._mapping[meeting_id][mapped_id]["name"]
                logger.debug(
                    f"[MAPPING-FIND] Meeting {meeting_id}: Found via devices/ part - "
                    f"device_id='{device_id}', device_part='{device_part}', "
                    f"mapped_id='{mapped_id}', name='{name}'"
                )
                return name
            # Также пробуем поиск по полному пути после "spaces/"
            if "spaces/" in device_id:
                space_device_path = device_id.split("spaces/")[-1]  # j5ZV3BSRHZEB/devices/227
                if space_device_path in self._index[meeting_id]:
                    mapped_id = self._index[meeting_id][space_device_path]
                    name = self._mapping[meeting_id][mapped_id]["name"]
                    logger.debug(
                        f"[MAPPING-FIND] Meeting {meeting_id}: Found via spaces/ path - "
                        f"device_id='{device_id}', space_device_path='{space_device_path}', "
                        f"mapped_id='{mapped_id}', name='{name}'"
                    )
                    return name
        
        # 4. Поиск по последней части пути (после последнего /)
        if "/" in device_id:
            last_part = device_id.split("/")[-1]
            if last_part in self._index[meeting_id]:
                mapped_id = self._index[meeting_id][last_part]
                name = self._mapping[meeting_id][mapped_id]["name"]
                logger.debug(
                    f"[MAPPING-FIND] Meeting {meeting_id}: Found via last path part - "
                    f"device_id='{device_id}', last_part='{last_part}', "
                    f"mapped_id='{mapped_id}', name='{name}'"
                )
                return name
            # Также пробуем поиск по части пути "devices/NUMBER"
            parts = device_id.split("/")
            if len(parts) >= 2 and parts[-2] == "devices":
                device_number = parts[-1]
                if device_number in self._index[meeting_id]:
                    mapped_id = self._index[meeting_id][device_number]
                    name = self._mapping[meeting_id][mapped_id]["name"]
                    logger.debug(
                        f"[MAPPING-FIND] Meeting {meeting_id}: Found via device number - "
                        f"device_id='{device_id}', device_number='{device_number}', "
                        f"mapped_id='{mapped_id}', name='{name}'"
                    )
                    return name
        
        # 5. Поиск по всем вариантам через индекс
        if device_id in self._index[meeting_id]:
            mapped_id = self._index[meeting_id][device_id]
            name = self._mapping[meeting_id][mapped_id]["name"]
            logger.debug(
                f"[MAPPING-FIND] Meeting {meeting_id}: Found via index - "
                f"device_id='{device_id}', mapped_id='{mapped_id}', name='{name}'"
            )
            return name
        
        # Не найдено - логируем подробную информацию для отладки
        available_device_ids = list(self._mapping[meeting_id].keys())
        available_index_keys = list(self._index[meeting_id].keys())[:20]  # Первые 20 для краткости
        
        log_msg = (
            f"[MAPPING-FIND] Meeting {meeting_id}: NOT FOUND - "
            f"device_id='{device_id}', "
            f"total_mappings={len(self._mapping[meeting_id])}, "
            f"total_index_entries={len(self._index[meeting_id])}, "
            f"available_device_ids={available_device_ids}, "
            f"available_index_keys_sample={available_index_keys}"
        )
        logger.warning(log_msg)
        print(log_msg)  # Дублируем в stdout
        
        return None
    
    def get_mapping(self, meeting_id: str) -> Optional[Dict[str, Dict]]:
        """
        Получает весь маппинг для встречи
        
        Args:
            meeting_id: ID встречи
        
        Returns:
            Словарь с маппингом или None если не найден
        """
        if meeting_id not in self._mapping:
            logger.debug(f"[MAPPING-GET] Meeting {meeting_id}: No mapping found")
            return None
        
        mapping = self._mapping[meeting_id].copy()
        logger.info(
            f"[MAPPING-GET] Meeting {meeting_id}: Retrieved mapping with {len(mapping)} participants"
        )
        return mapping
    
    def clear_mapping(self, meeting_id: str) -> None:
        """
        Очищает маппинг для встречи
        
        Args:
            meeting_id: ID встречи
        """
        if meeting_id in self._mapping:
            del self._mapping[meeting_id]
        if meeting_id in self._index:
            del self._index[meeting_id]
        if meeting_id in self._cleanup_times:
            del self._cleanup_times[meeting_id]
        
        logger.info(f"Cleared mapping for meeting {meeting_id}")
    
    def _clean_device_id(self, device_id: str) -> str:
        """
        Очищает device_id от спецсимволов (начальные \x00-\x1F)
        
        Args:
            device_id: Исходный device_id
        
        Returns:
            Очищенный device_id
        """
        if not device_id:
            return device_id
        
        # Удаляем начальные непечатаемые символы (0x00-0x1F)
        cleaned = device_id.lstrip('\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
                                    '\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f')
        return cleaned
    
    def cleanup_expired(self) -> None:
        """
        Очищает истекшие маппинги (старше TTL)
        """
        now = datetime.now(timezone.utc)
        expired_meetings = [
            meeting_id
            for meeting_id, cleanup_time in self._cleanup_times.items()
            if cleanup_time < now
        ]
        
        for meeting_id in expired_meetings:
            self.clear_mapping(meeting_id)
        
        if expired_meetings:
            logger.info(f"Cleaned up {len(expired_meetings)} expired mappings")
    
    def get_unknown_name(self, device_id: str) -> str:
        """
        Генерирует имя "Unknown" с последними 4 символами device_id
        
        Args:
            device_id: ID устройства
        
        Returns:
            Строка вида "Unknown (xxxx)"
        """
        last_chars = device_id[-4:] if len(device_id) >= 4 else device_id
        return f"Unknown ({last_chars})"


# Глобальный экземпляр сервиса маппинга
mapping_service = MappingService()

