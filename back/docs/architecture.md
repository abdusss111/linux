# DapMeet Service Architecture

## Overview

DapMeet is a FastAPI-based meeting transcription and AI analysis service that provides real-time meeting transcription, AI-powered analysis, and comprehensive meeting management. The service is designed with a modern async architecture using PostgreSQL, SQLAlchemy ORM, and integrates with Google Meet, OpenAI Whisper, and various authentication providers.

## System Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Chrome Ext    │    │   Web Client    │    │   Admin Panel   │
│   (Google Meet) │    │   (Frontend)    │    │   (Dashboard)   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼─────────────┐
                    │      FastAPI Server       │
                    │    (dapmeet service)      │
                    └─────────────┬─────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
    ┌─────▼─────┐      ┌─────────▼─────────┐      ┌─────▼─────┐
    │PostgreSQL │      │   External APIs   │      │   Email   │
    │ Database  │      │ (OpenAI, Google)  │      │ Service   │
    └───────────┘      └───────────────────┘      └───────────┘
```

## Core Components

### 1. Application Entry Point

**File**: `src/dapmeet/cmd/main.py`

- **FastAPI Application**: Main application instance with CORS middleware
- **Lifespan Management**: HTTP client lifecycle management
- **Path Configuration**: Dynamic path setup for module imports
- **Health Endpoints**: Basic health check endpoints

### 2. Database Layer

#### Database Configuration
**File**: `src/dapmeet/db/db.py`

- **Dual Engine Support**: Sync and async SQLAlchemy engines
- **Connection Pooling**: Optimized pool settings for production
- **SSL Support**: Automatic SSL configuration for production databases
- **Environment-driven**: Configuration via `DATABASE_URL` and `DATABASE_URL_ASYNC`

#### Models (`src/dapmeet/models/`)

##### User Model (`user.py`)
```python
class User(Base):
    id: str                    # Google ID or phone-based ID
    email: str                 # User email (nullable for phone auth)
    phone_number: str          # Phone number (nullable for Google auth)
    name: str                  # User display name
    auth_provider: str         # "google" or "phone"
    created_at: datetime
    
    # Relationships
    meetings: List[Meeting]
    prompts: List[Prompt]
```

##### Meeting Model (`meeting.py`)
```python
class Meeting(Base):
    unique_session_id: str     # Primary key: "{meeting_id}-{user_id}[-YYYY-MM-DD]"
    meeting_id: str           # Original meeting ID
    user_id: str              # Foreign key to User
    title: str                # Meeting title
    created_at: datetime
    
    # Relationships
    user: User
    participants: List[User]   # Many-to-many via meeting_participants
    chat_history: List[ChatMessage]
    segments: List[TranscriptSegment]
```

##### TranscriptSegment Model (`segment.py`)
```python
class TranscriptSegment(Base):
    id: int                   # Auto-increment primary key
    session_id: str           # Foreign key to Meeting
    google_meet_user_id: str  # Speaker identifier from Google Meet
    speaker_username: str     # Display name of speaker
    timestamp: datetime       # When the segment was spoken
    text: str                 # Transcribed text
    version: int              # Version for segment updates
    message_id: str           # Optional message identifier
    created_at: datetime
```

##### ChatMessage Model (`chat_message.py`)
```python
class ChatMessage(Base):
    id: int                   # Auto-increment primary key
    session_id: str           # Foreign key to Meeting
    sender: str               # Message sender ("ai", "user", etc.)
    content: str              # Message content
    created_at: datetime
```

##### Prompt Model (`prompt.py`)
```python
class Prompt(Base):
    id: int                   # Auto-increment primary key
    name: str                 # Unique prompt name
    content: str              # Prompt content
    prompt_type: str          # "admin" or "user"
    user_id: str              # Foreign key to User (null for admin prompts)
    is_active: bool           # Whether prompt is active
    created_at: datetime
    updated_at: datetime
```

##### PhoneVerification Model (`phone_verification.py`)
```python
class PhoneVerification(Base):
    id: str                   # Verification ID
    phone_number: str         # Phone number to verify
    verification_code: str    # 6-digit verification code
    is_verified: bool         # Verification status
    attempts: int             # Number of verification attempts
    created_at: datetime
    expires_at: datetime
    verified_at: datetime
```

### 3. API Layer (`src/dapmeet/api/`)

#### API Router Structure
**File**: `src/dapmeet/api/__init__.py`

```python
# API Endpoints Organization
/api/meetings      # Meeting management
/api/chat          # Chat functionality  
/auth              # Authentication
/admin             # Admin functionality
/admin/prompts     # Admin prompt management
/api/prompts       # User prompt management
/api/whisper       # Audio transcription
/webhook           # External webhooks
```

#### Meeting API (`meetings.py`)
- **GET /api/meetings**: List user meetings with pagination
- **POST /api/meetings**: Create or get meeting
- **GET /api/meetings/{meeting_id}**: Get specific meeting with segments
- **DELETE /api/meetings/{meeting_id}**: Delete meeting
- **GET /api/meetings/{meeting_id}/info**: Get recent meeting info (24h window)
- **POST /api/meetings/{meeting_id}/segments**: Add transcript segment

#### Chat API (`chat.py`)
- **GET /api/chat/{session_id}/history**: Get paginated chat history
- **POST /api/chat/{session_id}/messages**: Add single chat message
- **PUT /api/chat/{session_id}/history**: Replace entire chat history
- **DELETE /api/chat/{session_id}/history**: Delete all chat history
- **GET /api/chat/{session_id}/messages/{message_id}**: Get specific message

#### Authentication API (`auth.py`)
- **POST /auth/google**: Google OAuth authentication
- **POST /auth/validate**: Chrome extension authentication validation

#### Whisper API (`whisper.py`)
- **POST /api/whisper/transcribe**: Audio transcription with OpenAI Whisper
  - Supports multiple models (`gpt-4o-mini-transcribe`, `whisper-1`)
  - Optional meeting storage
  - Segment extraction and processing

#### Admin API (`admin.py`)
Comprehensive admin dashboard with:
- **Authentication**: JWT-based admin authentication
- **Dashboard Metrics**: Cached system statistics
- **User Management**: CRUD operations for users
- **Meeting Analytics**: Meeting statistics and filtering
- **System Health**: Database and service monitoring

#### Prompt Management APIs
- **Admin Prompts** (`admin_prompts.py`): Full CRUD for admin prompts
- **User Prompts** (`user_prompts.py`): User-scoped prompt management with read-only access to admin prompts

#### Webhook API (`webhook.py`)
- **POST /webhook/email**: External email sending webhook
- **GET /webhook/health**: Webhook service health check

### 4. Schema Layer (`src/dapmeet/schemas/`)

#### Data Transfer Objects (DTOs)

##### Authentication Schemas (`auth.py`)
```python
class CodePayload(BaseModel):
    code: str

class PhoneAuthRequest(BaseModel):
    phone_number: str

class PhoneVerificationRequest(BaseModel):
    phone_number: str
    verification_code: str
```

##### Meeting Schemas (`meetings.py`)
```python
class MeetingCreate(BaseModel):
    id: str
    title: str

class MeetingOut(BaseModel):
    unique_session_id: str
    meeting_id: str
    user_id: str
    title: str
    segments: List[TranscriptSegmentOut]
    created_at: datetime
    speakers: List[str]

class MeetingListResponse(BaseModel):
    meetings: List[MeetingOutList]
    total: int
    limit: int
    offset: int
    has_more: bool
```

##### Message Schemas (`messages.py`)
```python
class ChatMessageCreate(BaseModel):
    sender: str
    content: str

class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    sender: str
    content: str
    created_at: datetime

class ChatHistoryResponse(BaseModel):
    session_id: str
    total_messages: int
    messages: List[ChatMessageResponse]
```

##### Prompt Schemas (`prompt.py`)
```python
class PromptCreate(BaseModel):
    name: str
    content: str
    prompt_type: str
    is_active: bool

class PromptResponse(BaseModel):
    id: int
    name: str
    content: str
    prompt_type: str
    user_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 5. Service Layer (`src/dapmeet/services/`)

#### Authentication Services

##### Google Authentication (`google_auth_service.py`)
- **OAuth Flow**: Authorization code to access token exchange
- **Token Validation**: Google access token validation with audience verification
- **User Management**: Find or create user from Google user info
- **JWT Generation**: Custom JWT token generation
- **Chrome Extension Support**: Specialized authentication for browser extension

##### Admin Authentication (`admin_auth.py`)
- **Credential Verification**: Environment-based admin authentication
- **JWT Management**: Admin-specific JWT tokens with role claims
- **Authorization**: Admin role verification middleware

##### User Authentication (`auth.py`)
- **JWT Verification**: User token validation and user retrieval
- **User Context**: Current user dependency injection

#### Business Logic Services

##### Meeting Service (`meetings.py`)
```python
class MeetingService:
    async def get_or_create_meeting()      # 24-hour window logic
    async def get_meeting_by_session_id()  # Single meeting retrieval
    async def get_latest_segments_for_session()  # Optimized segment processing
    async def get_meetings_with_speakers() # Paginated meetings with metadata
    async def get_meetings_count()         # Meeting count for pagination
```

Key Features:
- **24-Hour Window Logic**: Automatic meeting session management
- **Segment Deduplication**: Advanced SQL-based segment processing
- **Performance Optimization**: Batch queries and efficient pagination

##### Prompt Service (`prompts.py`)
```python
class PromptService:
    async def create_prompt()              # Create with uniqueness validation
    async def get_prompt_by_id()          # Single prompt retrieval
    async def get_prompt_by_name()        # Name-based lookup
    async def update_prompt()             # Update with ownership checks
    async def delete_prompt()             # Delete with ownership validation
    async def search_prompts()            # Advanced search with pagination
    async def get_user_prompts()          # User-scoped prompts
    async def get_admin_prompts()         # Admin prompts
```

##### Whisper Service (`whisper.py`)
```python
class WhisperService:
    def transcribe_file()                 # OpenAI Whisper integration
```

Features:
- **Multi-Model Support**: `gpt-4o-mini-transcribe` and `whisper-1`
- **Format Handling**: Automatic audio format detection and normalization
- **Segment Processing**: Timestamp-based segment extraction

##### Email Service (`email_service.py`)
```python
class EmailService:
    async def send_email()                # Generic email sending
    async def send_welcome_email()        # Welcome email template
    async def send_custom_email()         # Custom template email
    async def send_simple_email()         # Simple text/HTML email
```

Features:
- **Template Engine**: Jinja2-based email templating
- **SMTP Configuration**: Environment-driven email configuration
- **Welcome Automation**: Automatic welcome emails for new users

### 6. Core Dependencies (`src/dapmeet/core/deps.py`)

```python
async def get_async_db()               # Async database session
def get_db()                          # Sync database session  
def get_http_client()                 # Shared HTTP client
```

## Database Schema

### Entity Relationship Diagram

```
Users (1) ──────── (*) Meetings
  │                     │
  │                     │ (1)
  │                     │
  │                     ▼ (*)
  │              TranscriptSegments
  │                     │
  │                     │ (1)
  │                     │
  │                     ▼ (*)
  │               ChatMessages
  │
  │ (1)
  │
  ▼ (*)
Prompts

MeetingParticipants (Many-to-Many: Users ↔ Meetings)
PhoneVerifications (Independent)
```

### Key Database Features

1. **Async Operations**: Full async/await support with asyncpg driver
2. **Connection Pooling**: Optimized pool configuration for high concurrency
3. **Migration Management**: Alembic-based schema versioning
4. **Performance Indexes**: Strategic indexing for query optimization
5. **Cascade Deletes**: Proper foreign key relationships with cascade rules

## Authentication & Authorization

### Authentication Methods

1. **Google OAuth 2.0**
   - Authorization code flow for web clients
   - Chrome Identity API for browser extensions
   - Audience validation for security

2. **Phone Authentication** (Framework ready)
   - SMS-based verification codes
   - Temporary verification records
   - Attempt limiting and expiration

3. **Admin Authentication**
   - Environment-based credentials
   - Separate JWT secret for admin tokens
   - Role-based access control

### JWT Token Structure

#### User Tokens
```json
{
  "sub": "user_id",
  "email": "user@example.com", 
  "name": "User Name",
  "iat": 1234567890,
  "exp": 1234567890
}
```

#### Admin Tokens
```json
{
  "sub": "admin_username",
  "username": "admin",
  "role": "admin",
  "iat": 1234567890,
  "exp": 1234567890
}
```

## External Integrations

### OpenAI Integration
- **Whisper API**: Audio transcription with multiple model support
- **Model Selection**: Automatic model switching based on requirements
- **Error Handling**: Comprehensive error handling and retry logic

### Google Services
- **OAuth 2.0**: User authentication and authorization
- **User Info API**: Profile information retrieval
- **Token Validation**: Security-focused token verification

### Email Service
- **SMTP Integration**: Configurable SMTP server support
- **Template Engine**: Jinja2-based email templating
- **Welcome Automation**: Automated user onboarding emails

## Performance & Scalability

### Database Optimizations
- **Connection Pooling**: 50 connections with 50 overflow
- **Query Optimization**: Strategic use of indexes and query planning
- **Batch Operations**: Efficient bulk data processing
- **Caching**: In-memory caching for dashboard metrics

### Async Architecture
- **Full Async Support**: End-to-end async/await implementation
- **Concurrent Processing**: Parallel database operations where possible
- **Resource Management**: Proper connection and resource cleanup

### Monitoring & Health Checks
- **Health Endpoints**: Application and database health monitoring
- **Performance Metrics**: Database pool status and system metrics
- **Error Handling**: Comprehensive error logging and handling

## Security Features

### Authentication Security
- **Token Validation**: Comprehensive JWT token validation
- **Audience Verification**: Google token audience validation
- **Role-Based Access**: Admin vs user role separation

### Data Protection
- **Input Validation**: Pydantic-based request validation
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **CORS Configuration**: Proper cross-origin request handling

### Admin Security
- **Separate Authentication**: Independent admin authentication system
- **Environment-Based Secrets**: Secure credential management
- **Access Logging**: Admin action logging capabilities

## Deployment Architecture

### Environment Configuration
```bash
# Database
DATABASE_URL=postgresql://...
DATABASE_URL_ASYNC=postgresql+asyncpg://...

# Authentication
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
NEXTAUTH_SECRET=...

# Admin
ADMIN_USERNAME=...
ADMIN_PASSWORD=...
ADMIN_JWT_SECRET=...

# External Services
OPENAI_API_KEY=...
WEBHOOK_KEY=...

# Email
MAIL_USERNAME=...
MAIL_PASSWORD=...
MAIL_SERVER=...
```

### Docker Configuration
- **Multi-stage Build**: Optimized Docker image
- **Environment Variables**: Runtime configuration
- **Health Checks**: Container health monitoring

### Database Migrations
- **Alembic Integration**: Version-controlled schema changes
- **Migration History**: Tracked database evolution
- **Rollback Support**: Safe schema rollback capabilities

## API Documentation

### OpenAPI/Swagger
- **Automatic Documentation**: FastAPI-generated API docs
- **Interactive Testing**: Built-in API testing interface
- **Schema Validation**: Request/response schema documentation

### Endpoint Categories
1. **Public Endpoints**: Health checks, authentication
2. **User Endpoints**: Meeting management, chat, prompts
3. **Admin Endpoints**: Dashboard, user management, system monitoring
4. **Webhook Endpoints**: External service integration

## Development Guidelines

### Code Organization
- **Layered Architecture**: Clear separation of concerns
- **Dependency Injection**: FastAPI dependency system
- **Type Hints**: Comprehensive type annotations
- **Error Handling**: Consistent error response patterns

### Testing Strategy
- **Unit Tests**: Service layer testing
- **Integration Tests**: API endpoint testing
- **Database Tests**: Model and migration testing
- **Authentication Tests**: Security validation

### Performance Considerations
- **Database Queries**: Optimized query patterns
- **Caching Strategy**: Strategic caching implementation
- **Resource Management**: Proper cleanup and resource handling
- **Monitoring**: Performance metrics and logging

## Future Enhancements

### Planned Features
1. **Real-time Updates**: WebSocket support for live transcription
2. **Advanced AI**: Enhanced meeting analysis and insights
3. **Mobile Support**: Mobile app authentication and API
4. **Enterprise Features**: Advanced admin controls and analytics

### Scalability Improvements
1. **Microservices**: Service decomposition for scale
2. **Message Queues**: Async task processing
3. **Caching Layer**: Redis integration for performance
4. **Load Balancing**: Multi-instance deployment support

This architecture provides a solid foundation for a scalable, secure, and maintainable meeting transcription and analysis service with room for future growth and enhancement.
