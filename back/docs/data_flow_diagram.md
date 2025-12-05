# Диаграмма потоков данных - API эндпоинты (без админки)

## Легенда

```
Client → API Endpoint → Auth → Service → Database/External → Response
```

---

## 1. Authentication API (`/auth`)

### 1.1 POST `/auth/google` - Google OAuth аутентификация

```
Client (code)
  ↓
POST /auth/google
  ↓
[No Auth Required]
  ↓
google_auth_service.exchange_code_for_token(code, http_client)
  ↓
  → Google OAuth API (token exchange)
  ↓
google_auth_service.get_google_user_info(access_token, http_client)
  ↓
  → Google User Info API
  ↓
google_auth_service.find_or_create_user(user_info, db)
  ↓
  → Database: SELECT/INSERT User
  ↓
google_auth_service.generate_jwt(user_info)
  ↓
Response: {access_token: JWT, user: user_info}
```

### 1.2 POST `/auth/validate` - Валидация для Chrome Extension

```
Chrome Extension (Bearer: Google Token)
  ↓
POST /auth/validate
  ↓
[No Auth Required - Google Token in Header]
  ↓
Extract Google Token from Authorization header
  ↓
google_auth_service.authenticate_with_google_token(token, db, http_client)
  ↓
  → Google Token Validation API
  ↓
  → Database: SELECT/INSERT User
  ↓
generate_jwt(user)
  ↓
Response: {token: JWT, user: {id, email, name}}
```

---

## 2. Meetings API (`/api/meetings`)

### 2.1 GET `/api/meetings` - Список встреч пользователя

```
Client (JWT Token)
  ↓
GET /api/meetings?limit=50&offset=0
  ↓
get_current_user(token) → Database: SELECT User (cached)
  ↓
MeetingService.get_meetings_with_speakers(user_id, limit, offset)
  ↓
  → Database: SELECT Meeting + JOIN TranscriptSegment (speakers)
  ↓
MeetingService.get_meetings_count(user_id)
  ↓
  → Database: SELECT COUNT(Meeting)
  ↓
Response: {meetings: [...], total, limit, offset, has_more}
```

### 2.2 POST `/api/meetings` - Создание/получение встречи

```
Client (JWT Token, {id, title})
  ↓
POST /api/meetings
  ↓
get_current_user(token) → Database: SELECT User
  ↓
MeetingService.get_or_create_meeting(meeting_data, user)
  ↓
  → Database: 
     - SELECT Meeting (check 24h window)
     - INSERT Meeting (if new or >24h old)
  ↓
Load Meeting with segments (eager loading)
  ↓
Response: MeetingOut (with segments)
```

### 2.3 GET `/api/meetings/{meeting_id}` - Получение встречи с сегментами

```
Client (JWT Token)
  ↓
GET /api/meetings/{meeting_id}
  ↓
get_current_user(token) → Database: SELECT User
  ↓
MeetingService.get_meeting_by_session_id(session_id, user_id)
  ↓
  → Database: SELECT Meeting WHERE unique_session_id = ...
  ↓
MeetingService.get_latest_segments_for_session(session_id)
  ↓
  → Database: SELECT TranscriptSegment (with deduplication logic)
  ↓
Get distinct speakers
  ↓
  → Database: SELECT DISTINCT speaker_username
  ↓
Response: MeetingOut {meeting, segments, speakers}
```

### 2.4 DELETE `/api/meetings/{meeting_id}` - Удаление встречи

```
Client (JWT Token)
  ↓
DELETE /api/meetings/{meeting_id}
  ↓
get_current_user(token) → Database: SELECT User
  ↓
Verify meeting ownership
  ↓
  → Database: SELECT Meeting WHERE user_id = ...
  ↓
Delete meeting (CASCADE deletes segments, chat, participants)
  ↓
  → Database: DELETE Meeting
  ↓
Response: 204 No Content
```

### 2.5 GET `/api/meetings/{meeting_id}/info` - Информация о последней встрече (<24ч)

```
Client (JWT Token)
  ↓
GET /api/meetings/{meeting_id}/info
  ↓
get_current_user(token) → Database: SELECT User
  ↓
Find latest meeting with LIKE pattern
  ↓
  → Database: SELECT Meeting WHERE unique_session_id LIKE ... ORDER BY created_at DESC
  ↓
Check if meeting age < 24 hours
  ↓
Response: MeetingOutList (if <24h) OR 404 (if >=24h)
```

### 2.6 POST `/api/meetings/{meeting_id}/segments` - Добавление сегмента транскрипции

```
Client (JWT Token, TranscriptSegmentCreate)
  ↓
POST /api/meetings/{meeting_id}/segments
  ↓
get_current_user(token) → Database: SELECT User
  ↓
MeetingService.get_meeting_by_session_id(session_id, user_id)
  ↓
  → Database: SELECT Meeting (verify ownership)
  ↓
Create TranscriptSegment
  ↓
  → Database: INSERT TranscriptSegment
  ↓
Response: TranscriptSegmentOut
```

### 2.7 POST `/api/meetings/{meeting_id}/participants` - Синхронизация участников

```
Client (JWT Token, ParticipantsSyncRequest)
  ↓
POST /api/meetings/{meeting_id}/participants
  ↓
get_current_user(token) → Database: SELECT User
  ↓
Verify meeting exists
  ↓
  → Database: SELECT Meeting WHERE unique_session_id LIKE ...
  ↓
mapping_service.save_mapping(meeting_id, device_id, name, variants)
  ↓
  → In-Memory Storage: _mapping[meeting_id][device_id] = {name, variants, updated_at}
  ↓
  → In-Memory Index: _index[meeting_id][variant] = device_id
  ↓
Response: {status: "ok", participants_count: N}
```

### 2.8 GET `/api/meetings/{meeting_id}/participants` - Получение маппинга участников

```
Client (JWT Token)
  ↓
GET /api/meetings/{meeting_id}/participants
  ↓
get_current_user(token) → Database: SELECT User
  ↓
Verify meeting exists
  ↓
  → Database: SELECT Meeting
  ↓
mapping_service.get_mapping(meeting_id)
  ↓
  → In-Memory Storage: Read _mapping[meeting_id]
  ↓
Response: ParticipantsResponse {participants: [...], last_updated}
```

### 2.9 DELETE `/api/meetings/{meeting_id}/participants` - Очистка маппинга

```
Client (JWT Token)
  ↓
DELETE /api/meetings/{meeting_id}/participants
  ↓
get_current_user(token) → Database: SELECT User
  ↓
Verify meeting exists
  ↓
mapping_service.clear_mapping(meeting_id)
  ↓
  → In-Memory Storage: Delete _mapping[meeting_id] and _index[meeting_id]
  ↓
Response: 204 No Content
```

### 2.10 POST `/api/meetings/{meeting_id}/raw-transcript` - Декодирование RAW транскрипта

```
Client (JWT Token, RawTranscriptRequest {raw_data: base64})
  ↓
POST /api/meetings/{meeting_id}/raw-transcript
  ↓
get_current_user(token) → Database: SELECT User
  ↓
Verify meeting exists
  ↓
  → Database: SELECT Meeting
  ↓
decoder_service.decode_raw_data(raw_data_base64)
  ↓
  → Decode: base64 → bytes → gzip decompress → protobuf parse
  ↓
  → Extract: device_id, message_id, text, version, lang_id
  ↓
mapping_service.find_name_by_device_id(meeting_id, device_id)
  ↓
  → In-Memory Storage: Search _mapping and _index
  ↓
message_cache_service.is_duplicate(...)
  ↓
  → In-Memory Cache: Check for duplicate message_id/device_id/text
  ↓
Create TranscriptSegment
  ↓
  → Database: INSERT TranscriptSegment
  ↓
message_cache_service.cache_message(...)
  ↓
  → In-Memory Cache: Store message_id/device_id/text
  ↓
Response: RawTranscriptResponse {success, decoded, saved}
```

---

## 3. Chat API (`/api/chat`)

### 3.1 GET `/api/chat/{session_id}/history` - История чата с пагинацией

```
Client (JWT Token)
  ↓
GET /api/chat/{session_id}/history?page=1&size=50
  ↓
get_current_user(token) → Database: SELECT User
  ↓
verify_meeting_access(session_id, user, db)
  ↓
  → Database: SELECT Meeting WHERE unique_session_id = ...
  ↓
Get total count
  ↓
  → Database: SELECT COUNT(ChatMessage) WHERE session_id = ...
  ↓
Get paginated messages
  ↓
  → Database: SELECT ChatMessage WHERE session_id = ... ORDER BY created_at ASC LIMIT/OFFSET
  ↓
Response: ChatHistoryResponse {session_id, total_messages, messages: [...]}
```

### 3.2 POST `/api/chat/{session_id}/messages` - Добавление сообщения

```
Client (JWT Token, ChatMessageCreate {sender, content})
  ↓
POST /api/chat/{session_id}/messages
  ↓
get_current_user(token) → Database: SELECT User
  ↓
verify_meeting_access(session_id, user, db)
  ↓
  → Database: SELECT Meeting
  ↓
Create ChatMessage
  ↓
  → Database: INSERT ChatMessage
  ↓
Response: ChatMessageResponse
```

### 3.3 PUT `/api/chat/{session_id}/history` - Замена всей истории чата

```
Client (JWT Token, ChatHistoryBulkRequest {messages: [...]})
  ↓
PUT /api/chat/{session_id}/history
  ↓
get_current_user(token) → Database: SELECT User
  ↓
verify_meeting_access(session_id, user, db)
  ↓
Delete existing messages
  ↓
  → Database: DELETE ChatMessage WHERE session_id = ...
  ↓
Insert new messages
  ↓
  → Database: INSERT ChatMessage (bulk)
  ↓
Response: ChatHistoryResponse {session_id, total_messages, messages: [...]}
```

### 3.4 DELETE `/api/chat/{session_id}/history` - Удаление всей истории

```
Client (JWT Token)
  ↓
DELETE /api/chat/{session_id}/history
  ↓
get_current_user(token) → Database: SELECT User
  ↓
verify_meeting_access(session_id, user, db)
  ↓
Delete all messages
  ↓
  → Database: DELETE ChatMessage WHERE session_id = ...
  ↓
Response: 204 No Content
```

### 3.5 GET `/api/chat/{session_id}/messages/{message_id}` - Получение конкретного сообщения

```
Client (JWT Token)
  ↓
GET /api/chat/{session_id}/messages/{message_id}
  ↓
get_current_user(token) → Database: SELECT User
  ↓
verify_meeting_access(session_id, user, db)
  ↓
Get message
  ↓
  → Database: SELECT ChatMessage WHERE id = ... AND session_id = ...
  ↓
Response: ChatMessageResponse
```

---

## 4. User Prompts API (`/api/prompts`)

### 4.1 POST `/api/prompts` - Создание промпта пользователя

```
Client (JWT Token, PromptCreate {name, content, is_active})
  ↓
POST /api/prompts
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.create_prompt(prompt_data, user_id)
  ↓
  → Database: INSERT Prompt (prompt_type="user", user_id=current_user.id)
  ↓
Response: PromptResponse
```

### 4.2 GET `/api/prompts` - Список промптов пользователя

```
Client (JWT Token)
  ↓
GET /api/prompts?page=1&limit=50
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.get_user_prompts(user_id, page, limit)
  ↓
  → Database: SELECT Prompt WHERE user_id = ... AND prompt_type = "user" (paginated)
  ↓
Response: PromptListResponse {prompts, total, page, limit, total_pages, has_next, has_prev}
```

### 4.3 GET `/api/prompts/names` - Список имен промптов

```
Client (JWT Token)
  ↓
GET /api/prompts/names
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.get_user_prompt_names(user_id)
  ↓
  → Database: SELECT Prompt.name WHERE user_id = ... AND prompt_type = "user"
  ↓
Response: ["prompt_name1", "prompt_name2", ...]
```

### 4.4 GET `/api/prompts/{prompt_id}` - Получение промпта по ID

```
Client (JWT Token)
  ↓
GET /api/prompts/{prompt_id}
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.get_prompt_by_id(prompt_id)
  ↓
  → Database: SELECT Prompt WHERE id = ...
  ↓
Verify ownership (prompt.user_id == current_user.id)
  ↓
Response: PromptResponse OR 403 Forbidden
```

### 4.5 GET `/api/prompts/by-name/{prompt_name}` - Получение промпта по имени

```
Client (JWT Token)
  ↓
GET /api/prompts/by-name/{prompt_name}
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.get_prompt_by_name(prompt_name)
  ↓
  → Database: SELECT Prompt WHERE name = ...
  ↓
Verify ownership
  ↓
Response: PromptResponse OR 403 Forbidden
```

### 4.6 PUT `/api/prompts/{prompt_id}` - Обновление промпта

```
Client (JWT Token, PromptUpdate {content?, is_active?})
  ↓
PUT /api/prompts/{prompt_id}
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.get_prompt_by_id(prompt_id)
  ↓
  → Database: SELECT Prompt
  ↓
Verify ownership
  ↓
PromptService.update_prompt(prompt_id, prompt_data, user_id)
  ↓
  → Database: UPDATE Prompt WHERE id = ... AND user_id = ...
  ↓
Response: PromptResponse
```

### 4.7 DELETE `/api/prompts/{prompt_id}` - Удаление промпта

```
Client (JWT Token)
  ↓
DELETE /api/prompts/{prompt_id}
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.get_prompt_by_id(prompt_id)
  ↓
Verify ownership
  ↓
PromptService.delete_prompt(prompt_id, user_id)
  ↓
  → Database: DELETE Prompt WHERE id = ... AND user_id = ...
  ↓
Response: 204 No Content
```

### 4.8 GET `/api/prompts/stats/count` - Количество промптов пользователя

```
Client (JWT Token)
  ↓
GET /api/prompts/stats/count
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.get_user_prompts(user_id, page=1, limit=1)
  ↓
  → Database: SELECT COUNT(Prompt) WHERE user_id = ...
  ↓
Response: {total_user_prompts: N}
```

### 4.9 GET `/api/prompts/admin-prompts` - Получение админских промптов (read-only)

```
Client (JWT Token)
  ↓
GET /api/prompts/admin-prompts?page=1&limit=50
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.get_admin_prompts(page, limit)
  ↓
  → Database: SELECT Prompt WHERE prompt_type = "admin" (paginated)
  ↓
Response: PromptListResponse {prompts, total, page, limit, ...}
```

### 4.10 GET `/api/prompts/admin-prompts/{prompt_id}` - Получение админского промпта по ID

```
Client (JWT Token)
  ↓
GET /api/prompts/admin-prompts/{prompt_id}
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.get_prompt_by_id(prompt_id)
  ↓
  → Database: SELECT Prompt WHERE id = ...
  ↓
Verify prompt_type == "admin"
  ↓
Response: PromptResponse OR 404
```

### 4.11 GET `/api/prompts/admin-prompts/by-name/{prompt_name}` - Получение админского промпта по имени

```
Client (JWT Token)
  ↓
GET /api/prompts/admin-prompts/by-name/{prompt_name}
  ↓
get_current_user(token) → Database: SELECT User
  ↓
PromptService.get_prompt_by_name(prompt_name)
  ↓
  → Database: SELECT Prompt WHERE name = ...
  ↓
Verify prompt_type == "admin"
  ↓
Response: PromptResponse OR 404
```

---

## 5. Whisper API (`/api/whisper`)

### 5.1 POST `/api/whisper/transcribe` - Транскрибация аудио

```
Client (JWT Token, audio file, params)
  ↓
POST /api/whisper/transcribe?model=...&with_segments=...&meeting_id=...
  ↓
get_current_user(token) → Database: SELECT User
  ↓
Read and validate file (max 25MB)
  ↓
WhisperService.transcribe_file(data, filename, model, response_format, prompt)
  ↓
  → OpenAI Whisper API (POST /v1/audio/transcriptions)
  ↓
If with_segments=true:
  - Parse segments from verbose_json
  - If meeting_id provided:
    - MeetingService.get_or_create_meeting(...)
    - Create TranscriptSegment for each segment
    - Database: INSERT TranscriptSegment (bulk)
  ↓
Response: {
  text: "...",
  segments: [...],
  model_used: "...",
  meeting_session_id: "...",
  segments_saved: N
}
```

### 5.2 POST `/api/whisper/segments/` - Ингestion чанка аудио

```
Client (JWT Token, multipart form: audio, meetingId, timestamp, segmentId, source)
  ↓
POST /api/whisper/segments/
  ↓
get_current_user(token) → Database: SELECT User
  ↓
Read and validate file (max 25MB)
  ↓
WhisperService.transcribe_file(data, filename, model="gpt-4o-mini-transcribe")
  ↓
  → OpenAI Whisper API
  ↓
If text is empty:
  → Response: {stored: false, reason: "empty_transcript"}
  ↓
MeetingService.get_or_create_meeting(meetingId, user)
  ↓
  → Database: SELECT/INSERT Meeting
  ↓
Determine speaker based on source:
  - MIC → user.name or user.email
  - TAB → "Другие"
  ↓
Create TranscriptSegment
  ↓
  → Database: INSERT TranscriptSegment
  ↓
Response: {
  meeting_session_id: "...",
  segment_id: "...",
  stored: true,
  chars: N,
  model_used: "..."
}
```

### 5.3 POST `/api/whisper/transcribe-v2` - Транскрибация с автосозданием встречи

```
Client (JWT Token, audio file, title?)
  ↓
POST /api/whisper/transcribe-v2?prompt=...
  ↓
get_current_user(token) → Database: SELECT User
  ↓
Read and validate file (max 100MB)
  ↓
Generate meeting_id: "transcribe-{timestamp}"
  ↓
Generate meeting_title: provided title OR "Meeting - {date}"
  ↓
WhisperService.transcribe_file(data, filename, model="whisper-1", response_format="verbose_json")
  ↓
  → OpenAI Whisper API
  ↓
Parse segments from verbose_json
  ↓
MeetingService.get_or_create_meeting(meeting_id, user)
  ↓
  → Database: SELECT/INSERT Meeting
  ↓
For each segment:
  - Calculate timestamp (base_ts + segment.start)
  - Create TranscriptSegment
  - Database: INSERT TranscriptSegment (bulk)
  ↓
Get complete meeting with segments
  ↓
  → Database: SELECT Meeting + SELECT TranscriptSegment
  ↓
Response: MeetingOut {meeting, segments, speakers}
```

---

## 6. Webhook API (`/webhook`)

### 6.1 POST `/webhook/email` - Отправка приветственного email

```
External Service (X-Webhook-Key header)
  ↓
POST /webhook/email {email, user_name?}
  ↓
verify_webhook_key(x_webhook_key)
  ↓
  → Check: x_webhook_key == WEBHOOK_KEY (env var)
  ↓
email_service.send_welcome_email(user_email, user_name)
  ↓
  → SMTP Server (send email)
  ↓
Response: WebhookEmailResponse {
  success: true,
  message: "...",
  email_sent_to: "...",
  timestamp: "..."
}
```

### 6.2 GET `/webhook/health` - Health check

```
Client
  ↓
GET /webhook/health
  ↓
[No Auth Required]
  ↓
Response: {
  status: "healthy",
  service: "webhook",
  timestamp: "..."
}
```

---

## Общие компоненты потока данных

### Аутентификация (get_current_user)

```
JWT Token (Bearer)
  ↓
jwt.decode(token, JWT_SECRET)
  ↓
Extract user_id from payload
  ↓
Check in-memory cache (5 min TTL)
  ↓
If cache miss:
  → Database: SELECT User WHERE id = ...
  → Update cache
  ↓
Return User object
```

### Meeting Service - 24-часовое окно

```
meeting_data.id + user.id → base_session_id
  ↓
Find latest meeting with LIKE pattern
  ↓
  → Database: SELECT Meeting WHERE unique_session_id LIKE "{base_session_id}%"
  ↓
If meeting exists:
  - Calculate age = now - meeting.created_at
  - If age < 24h: return existing meeting
  - If age >= 24h: create new with suffix "-YYYY-MM-DD"
  ↓
If no meeting: create new (no suffix)
  ↓
  → Database: INSERT Meeting
```

### Mapping Service - In-Memory Storage

```
Structure:
_mapping[meeting_id][device_id] = {
  name: str,
  variants: List[str],
  updated_at: datetime
}

_index[meeting_id][variant] = device_id

Operations:
- save_mapping: Store device_id → name mapping
- find_name_by_device_id: Search by device_id or variants
- clear_mapping: Delete all mappings for meeting
- get_mapping: Get all mappings for meeting
```

### Decoder Service - Protobuf Decoding

```
base64 string
  ↓
base64.b64decode() → bytes
  ↓
gzip.decompress() → decompressed bytes
  ↓
Parse protobuf structure:
  - Find message_id patterns
  - Extract device_id (string field)
  - Extract message_id (varint)
  - Extract text (string field)
  - Extract version (varint)
  - Extract lang_id (optional varint)
  ↓
Return: {
  device_id: str,
  message_id: int | None,
  text: str,
  version: int,
  lang_id: int | None
}
```

### Message Cache Service - Duplicate Detection

```
Structure:
_cache[meeting_id][message_id][device_id] = {
  text: str,
  version: int,
  timestamp: datetime
}

Operations:
- is_duplicate: Check if message_id/device_id/text/version already exists
- cache_message: Store message for duplicate detection
```

---

## Внешние сервисы

### Google OAuth API
- Token exchange: `POST https://oauth2.googleapis.com/token`
- User info: `GET https://www.googleapis.com/oauth2/v2/userinfo`
- Token validation: `GET https://www.googleapis.com/oauth2/v1/tokeninfo`

### OpenAI Whisper API
- Transcription: `POST https://api.openai.com/v1/audio/transcriptions`
- Models: `gpt-4o-mini-transcribe`, `whisper-1`
- Formats: `json`, `text`, `verbose_json`

### SMTP Server
- Email sending via configured SMTP server
- Templates: Jinja2-based email templates

---

## База данных - Основные таблицы

### Users
- `id` (PK)
- `email`, `phone_number`, `name`
- `auth_provider`, `created_at`

### Meetings
- `unique_session_id` (PK): "{meeting_id}-{user_id}[-YYYY-MM-DD]"
- `meeting_id`, `user_id` (FK), `title`, `created_at`

### TranscriptSegments
- `id` (PK)
- `session_id` (FK → Meeting.unique_session_id)
- `google_meet_user_id`, `speaker_username`
- `timestamp`, `text`, `version`, `message_id`, `created_at`

### ChatMessages
- `id` (PK)
- `session_id` (FK → Meeting.unique_session_id)
- `sender`, `content`, `created_at`

### Prompts
- `id` (PK)
- `name` (unique per user), `content`
- `prompt_type` ("admin" | "user")
- `user_id` (FK, nullable for admin prompts)
- `is_active`, `created_at`, `updated_at`

---

## Кэширование

### User Cache (In-Memory)
- TTL: 5 minutes
- Key: `user_id`
- Value: `(User object, cached_time)`

### Mapping Cache (In-Memory)
- TTL: 24 hours (per meeting)
- Structure: `_mapping[meeting_id][device_id]`
- Index: `_index[meeting_id][variant]`

### Message Cache (In-Memory)
- Purpose: Duplicate detection
- Structure: `_cache[meeting_id][message_id][device_id]`

---

## Обработка ошибок

### HTTP Status Codes
- `200 OK`: Successful GET/PUT
- `201 Created`: Successful POST (resource created)
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing/invalid authentication
- `403 Forbidden`: Access denied (ownership check)
- `404 Not Found`: Resource not found
- `413 Payload Too Large`: File exceeds size limit
- `500 Internal Server Error`: Server error
- `502 Bad Gateway`: External service error (OpenAI, Google)
- `503 Service Unavailable`: Database connection error

### Error Response Format
```json
{
  "detail": "Error message"
}
```

