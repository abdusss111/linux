"""
Сервис для декодирования RAW данных транскрипта из protobuf формата
Обрабатывает base64, gzip декомпрессию и извлечение данных из protobuf
"""
import base64
import gzip
import struct
import logging
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DecoderService:
    """
    Сервис для декодирования RAW данных транскрипта
    """
    
    # Паттерны для поиска границ message_id
    MESSAGE_ID_PATTERNS = [
        [24, 0, 32, 1, 45, 0],
        [24, 0, 1, 32, 1, 45, 0],
        [24, 0, 45, 0],
        [24, 0, 1, 45, 0],
    ]
    
    def decode_raw_data(self, raw_data_base64: str) -> Dict[str, Any]:
        """
        Декодирует RAW данные из base64, распаковывает gzip и извлекает данные из protobuf
        
        Args:
            raw_data_base64: Base64 строка с сырыми данными
        
        Returns:
            Словарь с декодированными данными:
            {
                "device_id": str,
                "message_id": int | None,
                "text": str,
                "version": int,
                "lang_id": int | None
            }
        
        Raises:
            ValueError: При ошибках декодирования/декомпрессии
        """
        try:
            # Шаг 1: Декодирование base64
            try:
                raw_bytes = base64.b64decode(raw_data_base64)
            except Exception as e:
                raise ValueError(f"Failed to decode base64: {str(e)}")
            
            if len(raw_bytes) == 0:
                raise ValueError("Empty data after base64 decoding")
            
            # Шаг 2: Декомпрессия gzip
            logger.debug(
                f"[DECODER] Before decompression - length={len(raw_bytes)}, "
                f"first_10_bytes={list(raw_bytes[:10])}"
            )
            decompressed = self._decompress_gzip(raw_bytes)
            logger.debug(
                f"[DECODER] After decompression - length={len(decompressed)}, "
                f"first_20_bytes={list(decompressed[:20])}"
            )
            
            # Шаг 3: Декодирование protobuf
            decoded = self._decode_protobuf(decompressed)
            
            return decoded
            
        except Exception as e:
            logger.error(f"Error decoding raw data: {str(e)}", exc_info=True)
            raise
    
    def _decompress_gzip(self, data: bytes) -> bytes:
        """
        Декомпрессирует gzip данные
        
        Args:
            data: Сжатые данные
        
        Returns:
            Распакованные данные
        
        Raises:
            ValueError: При ошибке декомпрессии
        """
        # Проверка magic numbers gzip (31, 139)
        if len(data) < 2:
            raise ValueError("Data too short for gzip")
        
        # Если первые байты не gzip, попробуем пропустить первые 3 байта
        if data[0] == 0x1f and data[1] == 0x8b:
            # Это gzip - распаковываем
            try:
                return gzip.decompress(data)
            except Exception as e:
                raise ValueError(f"Failed to decompress gzip: {str(e)}")
        elif len(data) > 3:
            # Пробуем пропустить первые 3 байта и проверить снова
            if data[3] == 0x1f and data[4] == 0x8b:
                try:
                    return gzip.decompress(data[3:])
                except Exception as e:
                    raise ValueError(f"Failed to decompress gzip (offset 3): {str(e)}")
        
        # Если не gzip, возвращаем как есть (может быть уже распаковано)
        logger.warning("Data doesn't appear to be gzip compressed, using as-is")
        return data
    
    def _decode_protobuf(self, data: bytes) -> Dict[str, Any]:
        """
        Декодирует protobuf данные и извлекает поля
        
        Args:
            data: Распакованные байты protobuf
        
        Returns:
            Словарь с извлеченными данными
        
        Raises:
            ValueError: При ошибке декодирования
        """
        if len(data) < 10:
            raise ValueError("Data too short for protobuf decoding")
        
        # Логируем информацию о данных
        hex_preview = data[:50].hex() if len(data) >= 50 else data.hex()
        byte_preview = list(data[:50]) if len(data) >= 50 else list(data)
        logger.debug(
            f"[DECODER] Protobuf data - length={len(data)}, "
            f"first_50_bytes_hex={hex_preview}, "
            f"first_50_bytes={byte_preview}"
        )
        
        try:
            # Ищем начало данных (байт 16 + 1)
            start_idx = self._find_data_start(data)
            logger.debug(f"[DECODER] Data start index: {start_idx}")
            if start_idx is None:
                # Логируем больше информации при ошибке
                logger.error(
                    f"[DECODER] Could not find protobuf start marker. "
                    f"Data length={len(data)}, first 20 bytes={list(data[:20])}"
                )
                raise ValueError("Could not find protobuf data start marker")
            
            # Извлекаем device_id (между байтом 3 и следующим байтом 16)
            device_id, device_end = self._extract_device_id(data, start_idx)
            logger.debug(
                f"[DECODER] Extracted device_id='{device_id}', device_end={device_end}"
            )
            
            # Извлекаем текст - передаем device_end чтобы искать после device_id
            # Текст должен быть доступен независимо от того, найден ли device_id
            text = self._extract_text(data, device_end if device_end > 0 else start_idx)
            logger.debug(
                f"[DECODER] Extracted text length={len(text) if text else 0}, "
                f"text_preview='{text[:100] if text else None}...'"
            )
            
            # Извлекаем message_id - пробуем использовать device_end, если device_id найден,
            # иначе ищем независимо от start_idx
            search_start_for_message = device_end if device_end > start_idx else start_idx
            message_id, version = self._extract_message_id(data, search_start_for_message)
            logger.debug(
                f"[DECODER] Extracted message_id={message_id}, version={version}"
            )
            
            # Извлекаем lang_id (после паттерна [64, 0, 72] или [64, 0, 80])
            # Также ищем независимо от device_end
            search_start_for_lang = device_end if device_end > start_idx else start_idx
            lang_id = self._extract_lang_id(data, search_start_for_lang)
            logger.debug(f"[DECODER] Extracted lang_id={lang_id}")
            
            result = {
                "device_id": device_id or "",
                "message_id": message_id,
                "text": text or "",
                "version": version or 1,
                "lang_id": lang_id
            }
            
            logger.info(
                f"[DECODER] Final decoded result - device_id='{result['device_id']}', "
                f"text_length={len(result['text'])}, message_id={result['message_id']}, "
                f"version={result['version']}"
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"[DECODER] Protobuf decoding error: {str(e)}. "
                f"Data length={len(data)}, first 50 bytes={list(data[:50])}",
                exc_info=True
            )
            raise ValueError(f"Failed to decode protobuf: {str(e)}")
    
    def _find_data_start(self, data: bytes) -> Optional[int]:
        """
        Находит начало данных (байт 16 + 1)
        
        Args:
            data: Данные для поиска
        
        Returns:
            Индекс начала данных или None
        """
        # Ищем последовательность [16, 1] или просто байт 16
        for i in range(len(data) - 1):
            if data[i] == 16:
                # Проверяем следующий байт
                if i + 1 < len(data) and data[i + 1] == 1:
                    return i + 2
                return i + 1
        return None
    
    def _extract_device_id(self, data: bytes, start_idx: int) -> Tuple[Optional[str], int]:
        """
        Извлекает device_id из protobuf данных.
        Структура: в начале идет field tag 10 (вложенное сообщение),
        внутри которого field tag 10 с длиной 31 и строка device_id.
        
        Args:
            data: Данные для извлечения
            start_idx: Начальный индекс (может быть 0 или больше)
        
        Returns:
            Кортеж (device_id, end_index)
        """
        # Логируем начало поиска
        logger.debug(
            f"[DECODER] _extract_device_id: start_idx={start_idx}, "
            f"data_length={len(data)}, "
            f"data_from_start={list(data[start_idx:start_idx+50]) if start_idx + 50 <= len(data) else list(data[start_idx:])}"
        )
        
        # НОВЫЙ ПОДХОД: Ищем структуру [10, длина_сообщения(varint), 10, 31, "spaces/..."]
        # Проверяем с самого начала данных, так как device_id всегда в начале
        search_start = 0
        if len(data) >= 35:  # Минимум: 10, длина(1-5 байт), 10, 31, строка(31)
            # Ищем первый field tag 10 (вложенное сообщение)
            if data[search_start] == 10:
                # Читаем длину вложенного сообщения (varint)
                msg_len_idx = search_start + 1
                if msg_len_idx >= len(data):
                    logger.debug("[DECODER] _extract_device_id: No data after first field tag 10")
                else:
                    # Читаем varint для длины сообщения
                    msg_len = 0
                    varint_idx = msg_len_idx
                    varint_shift = 0
                    max_varint_bytes = 5  # Максимум 5 байт для varint
                    
                    for i in range(max_varint_bytes):
                        if varint_idx >= len(data):
                            break
                        byte_val = data[varint_idx]
                        msg_len |= (byte_val & 0x7F) << varint_shift
                        varint_idx += 1
                        if (byte_val & 0x80) == 0:  # Последний байт varint
                            break
                        varint_shift += 7
                    
                    # Теперь проверяем, что после длины varint идет field tag 10
                    nested_msg_start = varint_idx
                    if nested_msg_start < len(data) and data[nested_msg_start] == 10:
                        # Нашли второй field tag 10 - это начало device_id
                        device_len_idx = nested_msg_start + 1
                        if device_len_idx < len(data):
                            device_len = data[device_len_idx]
                            if device_len == 31:  # Длина device_id всегда 31 байт в наших данных
                                device_str_start = device_len_idx + 1
                                device_str_end = device_str_start + device_len
                                if device_str_end <= len(data):
                                    try:
                                        device_id_bytes = data[device_str_start:device_str_end]
                                        device_id = device_id_bytes.decode('utf-8', errors='replace')
                                        # Проверяем, что это действительно device_id
                                        if device_id and ('spaces/' in device_id or '/devices/' in device_id):
                                            logger.debug(
                                                f"[DECODER] _extract_device_id: Found via structure [10, varint_len, 10, 31, str] "
                                                f"at start - device_id='{device_id}', end_idx={device_str_end}"
                                            )
                                            return device_id, device_str_end
                                    except Exception as e:
                                        logger.debug(f"[DECODER] _extract_device_id: Structure decode failed: {str(e)}")
                    else:
                        logger.debug(
                            f"[DECODER] _extract_device_id: After reading varint length {msg_len} at idx {varint_idx}, "
                            f"expected field tag 10, got {data[varint_idx] if varint_idx < len(data) else 'EOF'}"
                        )
                    
        # СТАРЫЕ ПОДХОДЫ (оставляем для совместимости)
        
        # Подход 1: Ищем байт 3 (field tag для строки в старом формате)
        idx = start_idx
        search_limit = min(start_idx + 100, len(data))  # Ограничиваем поиск
        while idx < search_limit and data[idx] != 3:
            idx += 1
        
        if idx < len(data):
            logger.debug(
                f"[DECODER] _extract_device_id: Found byte 3 at index {idx}"
            )
            # Продолжаем со старой логикой...
            idx += 1
            if idx >= len(data):
                logger.warning(f"[DECODER] _extract_device_id: No data after byte 3")
            else:
                str_len = data[idx]
                idx += 1
                if idx + str_len <= len(data) and str_len > 0 and str_len < 1000:
                    try:
                        device_id_bytes = data[idx:idx + str_len]
                        device_id = device_id_bytes.decode('utf-8', errors='replace').strip('\x00')
                        if device_id and self._is_valid_device_id(device_id):
                            logger.debug(
                                f"[DECODER] _extract_device_id: Extracted via byte 3 - device_id='{device_id}'"
                            )
                            return device_id, idx + str_len
                        else:
                            logger.debug(
                                f"[DECODER] _extract_device_id: Byte 3 extracted invalid device_id (looks like text): '{device_id[:50] if device_id else None}...'"
                            )
                    except Exception as e:
                        logger.debug(f"[DECODER] _extract_device_id: Byte 3 decode failed: {str(e)}")
        
        # Подход 2: Ищем байт 98 (0x62) - возможный field tag для device_id
        # Сначала ищем после start_idx
        idx = start_idx
        search_limit = min(start_idx + 200, len(data))
        while idx < search_limit:
            if data[idx] == 98:  # 0x62
                # После 98 обычно идет длина строки (varint или прямой байт)
                tag_idx = idx
                idx += 1
                if idx >= len(data):
                    break
                
                # Пробуем прочитать длину (может быть varint или прямой байт)
                str_len = data[idx]
                idx += 1
                
                # Проверяем разумность длины (varint может быть много байт, но обычно < 1000)
                if str_len > 200:  # Если слишком большая, возможно это varint - пропускаем этот подход
                    idx = tag_idx + 1
                    continue
                
                if idx + str_len <= len(data) and str_len > 0:
                    try:
                        device_id_bytes = data[idx:idx + str_len]
                        device_id = device_id_bytes.decode('utf-8', errors='replace').strip('\x00').strip()
                        # Валидация: device_id не должен быть длинным текстом или содержать пробелы/знаки препинания как в обычном тексте
                        if device_id and self._is_valid_device_id(device_id):
                            logger.debug(
                                f"[DECODER] _extract_device_id: Extracted via byte 98 - device_id='{device_id}', "
                                f"tag_idx={tag_idx}, str_len={str_len}"
                            )
                            return device_id, idx + str_len
                        else:
                            logger.debug(
                                f"[DECODER] _extract_device_id: Byte 98 extracted invalid device_id (looks like text): '{device_id[:50]}...'"
                            )
                    except Exception as e:
                        logger.debug(f"[DECODER] _extract_device_id: Byte 98 decode failed: {str(e)}")
            idx += 1
        
        # Подход 3: Ищем байт 10 (0x0A) - common field tag для строк в protobuf
        # Сначала ищем после start_idx
        idx = start_idx
        search_limit = min(start_idx + 150, len(data))
        while idx < search_limit:
            if data[idx] == 10:  # 0x0A - часто используется для строк
                tag_idx = idx
                idx += 1
                if idx >= len(data):
                    break
                
                str_len = data[idx]
                idx += 1
                
                if str_len > 200:
                    idx = tag_idx + 1
                    continue
                
                if idx + str_len <= len(data) and str_len > 0:
                    try:
                        device_id_bytes = data[idx:idx + str_len]
                        device_id = device_id_bytes.decode('utf-8', errors='replace').strip('\x00').strip()
                        if device_id and len(device_id) > 2 and self._is_valid_device_id(device_id):
                            logger.debug(
                                f"[DECODER] _extract_device_id: Extracted via byte 10 - device_id='{device_id}'"
                            )
                            return device_id, idx + str_len
                        else:
                            logger.debug(
                                f"[DECODER] _extract_device_id: Byte 10 extracted invalid device_id: '{device_id[:50] if device_id else None}...'"
                            )
                    except:
                        pass
            idx += 1
        
        # Подход 4: Ищем device_id ДО start_idx (возможно он там)
        # Пробуем поискать в начале данных
        if start_idx > 0:
            search_before_start = max(0, start_idx - 100)
            logger.debug(
                f"[DECODER] _extract_device_id: Trying to search before start_idx "
                f"(from {search_before_start} to {start_idx})"
            )
            
            # Подход 4a: Прямое чтение строки до байта 16 (граница)
            # Видим в логах: data_before_start содержит "spaces/j5ZV3BSRHZEB/devices/227" + байт 16
            # Сначала пробуем декодировать все данные до start_idx и найти паттерн "spaces/" или "/devices/"
            try:
                # Декодируем все данные до start_idx чтобы найти строку
                before_data = data[:start_idx]
                before_str = before_data.decode('utf-8', errors='ignore')
                
                # Ищем паттерн "spaces/" или "/devices/"
                if 'spaces/' in before_str:
                    spaces_idx = before_str.find('spaces/')
                    # Ищем конец - либо байт 16, либо следующий непечатаемый символ
                    remaining = before_str[spaces_idx:]
                    # Ищем где заканчивается правильный device_id (до текста или бинарных символов)
                    device_id_candidate = None
                    
                    # Пробуем найти конец через байт 16 в исходных данных
                    str_start_bytes = before_data.find(b'spaces/')
                    if str_start_bytes >= 0:
                        # Ищем байт 16 после начала строки
                        for boundary_idx in range(str_start_bytes, start_idx):
                            if data[boundary_idx] == 16:
                                device_id_bytes = data[str_start_bytes:boundary_idx]
                                device_id_candidate = device_id_bytes.decode('utf-8', errors='replace').strip('\x00').strip()
                                break
                        
                        # Если не нашли байт 16, пробуем найти конец через паттерн "/devices/NUMBER"
                        if not device_id_candidate and '/devices/' in before_str:
                            devices_pos = before_str.find('/devices/', str_start_bytes)
                            if devices_pos >= 0:
                                # После /devices/ должно быть число, затем может быть байт 16 или текст
                                device_num_start = devices_pos + len('/devices/')
                                # Ищем где заканчивается число
                                for i in range(device_num_start, min(device_num_start + 20, len(before_str))):
                                    if i < len(before_data) and (before_data[i] == 16 or not before_str[i].isdigit() and before_str[i] not in '/\\-_@.'):
                                        if before_data[i] == 16:
                                            device_id_bytes = data[str_start_bytes:i]
                                            device_id_candidate = device_id_bytes.decode('utf-8', errors='replace').strip('\x00').strip()
                                            break
                                if not device_id_candidate:
                                    # Просто берем до первого неправильного символа после устройства
                                    remaining_str = before_str[str_start_bytes:]
                                    if '/devices/' in remaining_str:
                                        parts = remaining_str.split('/devices/', 1)
                                        if len(parts) == 2:
                                            device_path = parts[0] + '/devices/'
                                            device_num_raw = parts[1]
                                        # Берем только число из номера устройства
                                        device_num = ''
                                        for char in device_num_raw:
                                            if char.isdigit():
                                                device_num += char
                                            elif char == '\x10' or ord(char) == 16:  # Байт 16
                                                break
                                            else:
                                                break
                                        if device_num:
                                            device_id_candidate = device_path + '/devices/' + device_num
                    
                    if device_id_candidate:
                        # Очищаем от мусора
                        clean_device_id = ''.join(c for c in device_id_candidate if c.isprintable() or c in '/\\-_@.')
                        if clean_device_id and self._is_valid_device_id(clean_device_id):
                            logger.debug(
                                f"[DECODER] _extract_device_id: Found via string search BEFORE start_idx - device_id='{clean_device_id}'"
                            )
                            return clean_device_id, start_idx  # Возвращаем start_idx как позицию конца
            except Exception as e:
                logger.debug(f"[DECODER] _extract_device_id: String search failed: {str(e)}")
            
            # Подход 4b: Ищем байт 16 как границу и пробуем разные стартовые позиции
            search_start_positions = [0]
            for offset in [10, 20, 30, 50, 100]:
                pos = max(0, start_idx - offset)
                if pos < start_idx and pos not in search_start_positions:
                    search_start_positions.append(pos)
            
            for str_start in search_start_positions:
                if str_start >= start_idx:
                    continue
                    
                # Ищем байт 16 после str_start
                for boundary_idx in range(str_start, start_idx):
                    if data[boundary_idx] == 16:  # Граница
                        str_end = boundary_idx
                        
                        if str_end > str_start and str_end - str_start < 300 and str_end - str_start > 10:
                            try:
                                device_id_bytes = data[str_start:str_end]
                                device_id = device_id_bytes.decode('utf-8', errors='replace').strip('\x00').strip()
                                
                                if device_id and ('spaces/' in device_id or '/devices/' in device_id):
                                    if self._is_valid_device_id(device_id):
                                        logger.debug(
                                            f"[DECODER] _extract_device_id: Found via boundary byte 16 "
                                            f"(from {str_start} to {str_end}) - device_id='{device_id}'"
                                        )
                                        return device_id, str_end
                                    elif '/devices/' in device_id:
                                        # Пробуем очистить
                                        parts = device_id.split('/devices/')
                                        if len(parts) == 2:
                                            device_path = parts[0] + '/devices/'
                                            device_num = ''.join(c for c in parts[1] if c.isalnum() or c in '/\\-_@.')[:20]
                                            if device_num:
                                                clean_device_id = device_path + device_num
                                                if self._is_valid_device_id(clean_device_id):
                                                    logger.debug(
                                                        f"[DECODER] _extract_device_id: Found and cleaned - device_id='{clean_device_id}'"
                                                    )
                                                    return clean_device_id, str_end
                            except Exception as e:
                                logger.debug(f"[DECODER] _extract_device_id: Boundary decode failed: {str(e)}")
                # Не break здесь, пробуем все позиции
            
            # Подход 4c: Ищем байт 10 или 98 до start_idx
            for tag_byte in [10, 98]:
                idx = search_before_start
                while idx < start_idx:
                    if data[idx] == tag_byte:
                        tag_idx = idx
                        idx += 1
                        if idx >= len(data):
                            break
                        
                        str_len = data[idx]
                        idx += 1
                        
                        if str_len > 200 or str_len == 0:
                            idx = tag_idx + 1
                            continue
                        
                        if idx + str_len <= len(data) and idx + str_len <= start_idx:  # Убеждаемся что не выходим за границу
                            try:
                                device_id_bytes = data[idx:idx + str_len]
                                device_id = device_id_bytes.decode('utf-8', errors='replace').strip('\x00').strip()
                                if device_id and self._is_valid_device_id(device_id):
                                    logger.debug(
                                        f"[DECODER] _extract_device_id: Found via byte {tag_byte} "
                                        f"BEFORE start_idx at index {tag_idx} - device_id='{device_id}'"
                                    )
                                    return device_id, idx + str_len
                            except:
                                pass
                    idx += 1
        
        logger.warning(
            f"[DECODER] _extract_device_id: All approaches failed. "
            f"Start_idx={start_idx}, data_length={len(data)}, "
            f"first_30_bytes={list(data[start_idx:start_idx+30]) if start_idx + 30 <= len(data) else list(data[start_idx:])}, "
            f"data_before_start={list(data[max(0, start_idx-30):start_idx]) if start_idx > 0 else []}"
        )
        return None, start_idx
    
    def _is_valid_device_id(self, device_id: str) -> bool:
        """
        Проверяет, является ли строка валидным device_id.
        device_id обычно короткий, без пробелов, и не похож на текст сообщения.
        
        Args:
            device_id: Строка для проверки
        
        Returns:
            True если похоже на device_id, False если похоже на текст или мусор
        """
        if not device_id:
            return False
        
        # Проверка на непечатаемые/поврежденные символы
        # device_id должен содержать в основном печатаемые ASCII/UTF-8 символы
        printable_count = sum(1 for c in device_id if c.isprintable() or c in '/\\-_')
        if len(device_id) > 0:
            printable_ratio = printable_count / len(device_id)
            # Если менее 70% символов печатаемые - это мусор
            if printable_ratio < 0.7:
                return False
        
        # Проверка на слишком много нечитаемых символов (замены UTF-8)
        # Символ замены UTF-8 (\ufffd) обычно появляется при неправильном декодировании
        replacement_char = '\ufffd'  # Unicode replacement character
        replacement_char_count = device_id.count(replacement_char)
        if replacement_char_count > len(device_id) * 0.3:  # Более 30% - мусор
            return False
        
        # Также проверяем на другие нечитаемые символы (контрольные символы кроме пробела и табуляции)
        control_chars = sum(1 for c in device_id if ord(c) < 32 and c not in '\n\r\t')
        if control_chars > len(device_id) * 0.2:  # Более 20% контрольных символов - мусор
            return False
        
        # device_id не должен быть слишком длинным (обычно < 200 символов)
        if len(device_id) > 200:
            return False
        
        # device_id должен содержать хотя бы некоторые буквы, цифры или допустимые символы
        # Проверяем, есть ли хотя бы одна буква/цифра/слеш
        has_valid_chars = any(c.isalnum() or c in '/\\-_@.' for c in device_id)
        if not has_valid_chars:
            return False
        
        # device_id не должен содержать много пробелов или выглядеть как предложение
        # Проверяем количество пробелов - если их много относительно длины, это текст
        space_count = device_id.count(' ')
        if len(device_id) > 20 and space_count > len(device_id) // 10:
            return False
        
        # device_id обычно не заканчивается на знаки препинания, характерные для текста
        text_endings = ['.', '!', '?', ',', ';', ':', '@']
        if len(device_id) > 10 and device_id[-1] in text_endings and space_count > 0:
            # Если заканчивается на знак препинания и содержит пробелы - скорее всего текст
            return False
        
        # device_id обычно содержит буквы/цифры/слеши, но не должен выглядеть как предложение
        # Если содержит много слов подряд (более 2-3 слов для коротких строк), это текст
        words = device_id.split()
        if len(words) > 3 and len(device_id) < 100:
            return False
        
        # Проверка на последовательность одинаковых символов или паттерны мусора
        # Если более 50% символов одинаковые (кроме допустимых), это подозрительно
        if len(device_id) > 3:
            char_counts = {}
            for c in device_id:
                char_counts[c] = char_counts.get(c, 0) + 1
            max_char_count = max(char_counts.values())
            if max_char_count > len(device_id) * 0.5 and max_char_count > 3:
                # Исключаем случаи, когда повторяются допустимые символы
                most_common_char = max(char_counts, key=char_counts.get)
                if most_common_char not in '/\\-_@.':
                    return False
        
        return True
    
    def _extract_message_id(self, data: bytes, start_idx: int) -> Tuple[Optional[int], Optional[int]]:
        """
        Извлекает message_id и version через паттерны
        
        Args:
            data: Данные для извлечения
            start_idx: Начальный индекс
        
        Returns:
            Кортеж (message_id, version)
        """
        for pattern in self.MESSAGE_ID_PATTERNS:
            idx = self._find_pattern(data, pattern, start_idx)
            if idx is not None:
                # После паттерна идет message_id (little-endian)
                pattern_end = idx + len(pattern)
                if pattern_end + 4 <= len(data):
                    # Читаем 4 байта как little-endian uint32
                    try:
                        message_id = struct.unpack('<I', data[pattern_end:pattern_end + 4])[0]
                        # Version обычно идет после message_id
                        if pattern_end + 8 <= len(data):
                            version = struct.unpack('<I', data[pattern_end + 4:pattern_end + 8])[0]
                            return message_id, version
                        return message_id, 1
                    except Exception as e:
                        logger.warning(f"Failed to extract message_id: {str(e)}")
        
        # Если паттерны не найдены, пытаемся найти сообщение другим способом
        # Ищем байт 24 (tag для message_id)
        for i in range(start_idx, min(start_idx + 100, len(data))):
            if data[i] == 24:
                # Пытаемся извлечь varint или следующее значение
                if i + 5 <= len(data):
                    try:
                        # Пробуем прочитать как varint или как фиксированное значение
                        message_id = struct.unpack('<I', data[i + 1:i + 5])[0]
                        return message_id, 1
                    except:
                        pass
        
        return None, 1
    
    def _extract_text(self, data: bytes, search_from_idx: int) -> Optional[str]:
        """
        Извлекает текст из protobuf данных.
        Структура: после device_id идет field tag 16 (varint), затем field tag 24 (timestamp varint),
        затем field tag 50, длина (байт), текст в UTF-8
        
        Args:
            data: Данные для извлечения
            search_from_idx: Индекс с которого начинать поиск (после device_id)
        
        Returns:
            Извлеченный текст или None
        """
        logger.debug(
            f"[DECODER] _extract_text: search_from_idx={search_from_idx}, "
            f"data_length={len(data)}"
        )
        
        # Ищем field tag 50 (текст) - правильный находится после field tag 24 (timestamp)
        # Ищем строго после search_from_idx (после device_id)
        text_start = None
        
        # Ищем field tag 24 (timestamp) после search_from_idx
        for i in range(search_from_idx, len(data) - 1):
            if data[i] == 24:  # Field tag 24 (timestamp)
                # Читаем varint timestamp (может быть несколько байт)
                ts_idx = i + 1
                for j in range(5):  # Максимум 5 байт для varint
                    if ts_idx >= len(data):
                        break
                    byte_val = data[ts_idx]
                    ts_idx += 1
                    if (byte_val & 0x80) == 0:  # Последний байт varint
                        break
                
                # После timestamp ищем field tag 50 (в пределах следующих 10 байт обычно)
                if ts_idx < len(data):
                    search_start = ts_idx
                    search_end = min(ts_idx + 10, len(data))  # Ограничиваем поиск - text field должен быть сразу после timestamp
                    for k in range(search_start, search_end):
                        if data[k] == 50:  # field tag 50
                            text_start = k + 1
                            logger.debug(
                                f"[DECODER] _extract_text: Found field tag 50 at index {k} "
                                f"(after timestamp at {i}, search_from={search_from_idx})"
                            )
                            break
                    if text_start:
                        break
        
        # Если не нашли через timestamp после search_from_idx, пробуем найти field tag 50 напрямую после search_from_idx
        # (но только если он выглядит разумно)
        if text_start is None:
            for i in range(search_from_idx, len(data) - 1):
                if data[i] == 50:  # field tag 50
                    # Проверяем что следующая длина разумная (не слишком большая)
                    if i + 1 < len(data):
                        potential_len = data[i + 1]
                        if 0 < potential_len <= 200:  # Разумная длина текста
                            text_start = i + 1
                            logger.debug(
                                f"[DECODER] _extract_text: Found field tag 50 at index {i} "
                                f"(fallback, after search_from={search_from_idx}, len={potential_len})"
                            )
                            break
        
        if text_start is None:
            logger.warning(
                f"[DECODER] _extract_text: Field tag 50 not found. "
                f"Data_length={len(data)}, first_20_bytes={list(data[:20])}"
            )
            return None
        
        # Читаем длину строки (обычно прямой байт, так как длина текста < 128)
        if text_start >= len(data):
            logger.warning(f"[DECODER] _extract_text: No data after field tag 50")
            return None
        
        str_len = data[text_start]
        text_str_start = text_start + 1
        
        # Проверяем разумность длины
        if str_len == 0 or str_len > 200:  # Текст обычно не более 200 байт
            logger.debug(
                f"[DECODER] _extract_text: Invalid length {str_len}, "
                f"maybe varint needed or wrong field tag"
            )
            return None
        
        logger.debug(
            f"[DECODER] _extract_text: str_len={str_len}, "
            f"text_str_start={text_str_start}, "
            f"text_bytes_preview={list(data[text_str_start:text_str_start+min(str_len, 20)])}"
        )
        
        # Извлекаем текст напрямую по длине
        if text_str_start + str_len <= len(data):
            try:
                text_bytes = data[text_str_start:text_str_start + str_len]
                text = text_bytes.decode('utf-8', errors='replace')
                
                # Очищаем текст от возможного мусора (control characters кроме пробела/табуляции)
                text_clean = ''.join(c for c in text if c.isprintable() or c in '\n\r\t')
                text_clean = text_clean.strip()
                
                logger.debug(
                    f"[DECODER] _extract_text: Extracted - "
                    f"raw_length={len(text)}, clean_length={len(text_clean)}, "
                    f"text_preview='{text_clean[:50]}...'"
                )
                
                if text_clean:  # Проверяем, что не пустая строка после очистки
                    return text_clean
            except Exception as e:
                logger.warning(f"[DECODER] _extract_text: Failed to decode text: {str(e)}")
        
        logger.warning(
            f"[DECODER] _extract_text: Failed to extract text. "
            f"text_str_start={text_str_start}, str_len={str_len}, "
            f"data_remaining={len(data) - text_str_start}"
        )
        return None
    
    def _extract_lang_id(self, data: bytes, start_idx: int) -> Optional[int]:
        """
        Извлекает lang_id (после паттерна [64, 0, 72] или [64, 0, 80])
        
        Args:
            data: Данные для извлечения
            start_idx: Начальный индекс
        
        Returns:
            lang_id или None
        """
        patterns = [
            [64, 0, 72],
            [64, 0, 80]
        ]
        
        for pattern in patterns:
            idx = self._find_pattern(data, pattern, start_idx)
            if idx is not None:
                pattern_end = idx + len(pattern)
                if pattern_end < len(data):
                    # lang_id обычно идет как varint или как фиксированное значение
                    try:
                        if pattern_end + 1 <= len(data):
                            lang_id = data[pattern_end]
                            return lang_id
                    except:
                        pass
        
        return None
    
    def _find_pattern(self, data: bytes, pattern: list, start_idx: int = 0) -> Optional[int]:
        """
        Находит паттерн байтов в данных
        
        Args:
            data: Данные для поиска
            pattern: Паттерн для поиска (список байтов)
            start_idx: Начальный индекс поиска
        
        Returns:
            Индекс начала паттерна или None
        """
        if len(pattern) == 0:
            return start_idx
        
        for i in range(start_idx, len(data) - len(pattern) + 1):
            match = True
            for j, byte_val in enumerate(pattern):
                if i + j >= len(data) or data[i + j] != byte_val:
                    match = False
                    break
            if match:
                return i
        
        return None


# Глобальный экземпляр сервиса декодирования
decoder_service = DecoderService()

