from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class ParticipantMapping(BaseModel):
    """Участник с маппингом device_id"""
    model_config = ConfigDict(populate_by_name=True)
    
    device_id: str = Field(..., alias="deviceId", description="Основной ID устройства")
    name: str = Field(..., description="Имя участника")
    variants: List[str] = Field(default_factory=list, description="Варианты device_id для поиска")


class ParticipantsSyncRequest(BaseModel):
    """Запрос на синхронизацию маппинга участников"""
    model_config = ConfigDict(populate_by_name=True)
    
    session_id: str = Field(..., alias="sessionId", description="ID сессии встречи")
    space_id: Optional[str] = Field(None, alias="spaceId", description="Space ID из Google Meet")
    participants: List[ParticipantMapping] = Field(..., description="Массив участников")
    timestamp: Optional[datetime] = Field(None, description="Время синхронизации")


class ParticipantsResponse(BaseModel):
    """Ответ с маппингом участников"""
    participants: List[ParticipantMapping] = Field(..., description="Список участников с маппингом")
    last_updated: Optional[datetime] = Field(None, description="Время последнего обновления")


class RawTranscriptRequest(BaseModel):
    """Запрос на декодирование RAW транскрипта"""
    model_config = ConfigDict(populate_by_name=True)
    
    raw_data: str = Field(..., alias="rawData", description="Base64 строка с сырыми данными")
    label: str = Field(..., description="Метка канала: 'captions' или 'meet_messages'")
    session_id: str = Field(..., alias="sessionId", description="ID сессии")
    space_id: Optional[str] = Field(None, alias="spaceId", description="Space ID (опционально)")
    timestamp: Optional[datetime] = Field(None, description="Время получения данных")


class DecodedData(BaseModel):
    """Декодированные данные из protobuf"""
    device_id: str = Field(..., description="ID устройства")
    message_id: Optional[int] = Field(None, description="ID сообщения")
    text: str = Field(..., description="Текст транскрипта")
    version: int = Field(..., description="Версия сообщения")
    lang_id: Optional[int] = Field(None, description="ID языка")
    username: str = Field(..., description="Имя участника (из маппинга или 'Unknown')")


class RawTranscriptResponse(BaseModel):
    """Ответ на запрос декодирования RAW транскрипта"""
    success: bool = Field(..., description="Успешность декодирования")
    decoded: Optional[DecodedData] = Field(None, description="Декодированные данные (если успешно)")
    saved: bool = Field(False, description="Сохранен ли сегмент в БД")
    error: Optional[str] = Field(None, description="Сообщение об ошибке (если была)")

