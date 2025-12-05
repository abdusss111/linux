from typing import Any, Dict, List, Optional
from datetime import datetime, date
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, and_, func, select, case, extract
import asyncio
import time
from typing import Optional

logger = logging.getLogger(__name__)

from dapmeet.core.deps import get_async_db
from dapmeet.services.admin_auth import (
    get_current_admin,
    verify_admin_credentials,
    create_admin_jwt,
)
from dapmeet.models.user import User
from dapmeet.models.meeting import Meeting
from dapmeet.models.segment import TranscriptSegment
from dapmeet.models.chat_message import ChatMessage
from dapmeet.models.prompt import Prompt
from dapmeet.services.subscription import SubscriptionService
from dapmeet.schemas.subscription import (
    SubscriptionUpdate,
    SubscriptionOut,
    SubscriptionWithHistory,
    SubscriptionHistoryOut
)


router = APIRouter()


# =====================
# Admin Analytics Schemas
# =====================

class AdminAnalyticsDataPoint(BaseModel):
    """Single data point for time-series analytics"""
    date: str
    count: int

class AdminAnalyticsMetadata(BaseModel):
    """Metadata for analytics responses"""
    total_registrations: Optional[int] = None
    total_meetings: Optional[int] = None
    overall_avg_duration: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    group_by: str
    filtered: Optional[bool] = None
    generated_at: Optional[str] = None

class AdminAnalyticsResponse(BaseModel):
    """Standard analytics response format"""
    success: bool = True
    data: List[AdminAnalyticsDataPoint]
    metadata: AdminAnalyticsMetadata

class AdminMeetingDurationDataPoint(BaseModel):
    """Data point for meeting duration analytics"""
    date: str
    avg_duration: float
    min_duration: float
    max_duration: float
    meeting_count: int

class AdminMeetingDurationResponse(BaseModel):
    """Meeting duration analytics response"""
    success: bool = True
    data: List[AdminMeetingDurationDataPoint]
    metadata: AdminAnalyticsMetadata

class AdminDetailedMeeting(BaseModel):
    """Detailed meeting information for admin"""
    meeting_id: str
    unique_session_id: str
    title: Optional[str]
    created_at: datetime
    duration_minutes: Optional[float]
    participant_count: int
    speech_segments_count: int
    chat_messages_count: int
    host_user_id: str
    host_user_name: Optional[str]
    host_user_email: Optional[str]

class AdminPaginationInfo(BaseModel):
    """Pagination information"""
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

class AdminDetailedMeetingsResponse(BaseModel):
    """Detailed meetings list response"""
    success: bool = True
    data: List[AdminDetailedMeeting]
    pagination: AdminPaginationInfo
    filters: Dict[str, Any]

class AdminDashboardMetricsData(BaseModel):
    """Dashboard metrics data"""
    users: int
    meetings: int
    segments: int
    chat_messages: int

class AdminDashboardMetricsResponse(BaseModel):
    """Dashboard metrics response with optional date filtering"""
    success: bool = True
    data: AdminDashboardMetricsData
    metadata: Dict[str, Any]

class AdminDetailedUser(BaseModel):
    """Detailed user information for admin"""
    id: str
    name: Optional[str]
    email: Optional[str]
    created_at: datetime
    meeting_count: int
    message_count: int
    total_meeting_duration: float
    status: str = "active"

class AdminDetailedUsersResponse(BaseModel):
    """Detailed users list response"""
    success: bool = True
    data: List[AdminDetailedUser]
    pagination: AdminPaginationInfo


# =====================
# Caching for Dashboard Metrics
# =====================

# Simple in-memory cache for dashboard metrics (TTL: 60 seconds)
_metrics_cache = {"data": None, "timestamp": 0, "ttl": 60}

def get_cached_metrics() -> Optional[Dict]:
    """Get cached metrics if still valid"""
    if _metrics_cache["data"] and (time.time() - _metrics_cache["timestamp"]) < _metrics_cache["ttl"]:
        return _metrics_cache["data"]
    return None

def set_cached_metrics(data: Dict):
    """Cache metrics data"""
    _metrics_cache["data"] = data
    _metrics_cache["timestamp"] = time.time()


# =====================
# Helper Functions
# =====================

def validate_date_params(start_date: Optional[str], end_date: Optional[str]) -> tuple[Optional[datetime], Optional[datetime]]:
    """Validate and convert date parameters"""
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    if start_dt and end_dt and start_dt > end_dt:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    
    # Validate date range is not excessive (max 2 years)
    if start_dt and end_dt:
        days_diff = (end_dt - start_dt).days
        if days_diff > 730:
            raise HTTPException(status_code=400, detail="Date range cannot exceed 2 years (730 days)")
    
    return start_dt, end_dt

def validate_group_by(group_by: str) -> str:
    """Validate group_by parameter"""
    valid_values = ["day", "week", "month", "year"]
    if group_by not in valid_values:
        return "day"  # Default fallback
    return group_by

def get_date_trunc_format(group_by: str) -> str:
    """Get PostgreSQL DATE_TRUNC format for grouping"""
    formats = {
        "day": "day",
        "week": "week", 
        "month": "month",
        "year": "year"
    }
    return formats.get(group_by, "day")

async def get_meetings_with_duration_batch(db: AsyncSession, meetings: List) -> List[Dict]:
    """
    Add duration, owners, and AI chat interactions to a list of meetings using batch queries for efficiency.
    This prevents N+1 query problem and reduces database connections.
    """
    if not meetings:
        return []
    
    # Extract session IDs from meetings
    session_ids = []
    meeting_lookup = {}
    
    for meeting in meetings:
        try:
            # Handle both Meeting objects and SQLAlchemy Row objects from JOIN
            if hasattr(meeting, '_mapping') or hasattr(meeting, '_fields'):
                # SQLAlchemy Row object from JOIN query (Meeting, User)
                meeting_obj = meeting[0]  # Meeting object
                user_obj = meeting[1] if len(meeting) > 1 else None  # User object
            elif isinstance(meeting, tuple):
                # Regular tuple (Meeting, User)
                meeting_obj = meeting[0]
                user_obj = meeting[1] if len(meeting) > 1 else None
            else:
                # Direct Meeting object
                meeting_obj = meeting
                user_obj = None
            
            # Access unique_session_id from Meeting object
            session_id = meeting_obj.unique_session_id
                
            session_ids.append(session_id)
            meeting_lookup[session_id] = (meeting_obj, user_obj)
        except Exception as e:
            # Log error with more details for debugging
            print(f"Error processing meeting object: {e}")
            print(f"Meeting type: {type(meeting)}")
            if hasattr(meeting, '__dict__'):
                print(f"Meeting attributes: {meeting.__dict__}")
            continue
    
    # Import here to avoid circular dependencies
    from dapmeet.models.meeting import meeting_participants
    
    # Extract unique user_ids for host lookup
    host_user_ids = set()
    for meeting in meeting_lookup.values():
        meeting_obj = meeting[0]
        if meeting_obj.user_id:
            host_user_ids.add(meeting_obj.user_id)
    
    # Batch query to get duration for all meetings at once
    duration_query = select(
        TranscriptSegment.session_id,
        func.min(TranscriptSegment.timestamp).label('first_timestamp'),
        func.max(TranscriptSegment.timestamp).label('last_timestamp')
    ).where(
        TranscriptSegment.session_id.in_(session_ids)
    ).group_by(TranscriptSegment.session_id)
    
    # Batch query to get AI chat message counts
    ai_chat_query = select(
        ChatMessage.session_id,
        func.count(ChatMessage.id).label('ai_chat_count')
    ).where(
        and_(
            ChatMessage.session_id.in_(session_ids),
            ChatMessage.sender == 'ai'
        )
    ).group_by(ChatMessage.session_id)
    
    # Batch query to get meeting participants (owners)
    participants_query = select(
        meeting_participants.c.session_id,
        User.id.label('participant_user_id'),
        User.email.label('participant_email'),
        User.name.label('participant_name')
    ).join(
        User, meeting_participants.c.user_id == User.id
    ).where(
        meeting_participants.c.session_id.in_(session_ids)
    )
    
    # Batch query to get host users (meeting creators)
    host_users_lookup = {}
    if host_user_ids:
        host_users_query = select(
            User.id,
            User.email,
            User.name
        ).where(
            User.id.in_(host_user_ids)
        )
        host_users_result = await db.execute(host_users_query)
        host_users_lookup = {row.id: {"user_id": row.id, "email": row.email, "name": row.name} for row in host_users_result.all()}
    
    # Execute remaining batch queries
    duration_result = await db.execute(duration_query)
    ai_chat_result = await db.execute(ai_chat_query)
    participants_result = await db.execute(participants_query)
    
    # Build lookup dictionaries
    duration_data = {row.session_id: row for row in duration_result.all()}
    ai_chat_data = {row.session_id: row.ai_chat_count for row in ai_chat_result.all()}
    
    # Group participants by session_id
    participants_by_session = {}
    for row in participants_result.all():
        session_id = row.session_id
        if session_id not in participants_by_session:
            participants_by_session[session_id] = []
        participants_by_session[session_id].append({
            "user_id": row.participant_user_id,
            "email": row.participant_email,
            "name": row.participant_name
        })
    
    # Build response with all data
    meetings_with_duration = []
    
    for session_id in session_ids:
        try:
            meeting_obj, user_obj = meeting_lookup[session_id]
            
            # Calculate duration - handle cases where segments might exist but calculation fails
            duration = None
            if session_id in duration_data:
                timestamps = duration_data[session_id]
                if timestamps.first_timestamp and timestamps.last_timestamp:
                    try:
                        duration_seconds = (timestamps.last_timestamp - timestamps.first_timestamp).total_seconds()
                        if duration_seconds >= 0:  # Ensure non-negative duration
                            duration = round(duration_seconds / 60.0, 2)
                        else:
                            duration = 0.0
                    except Exception as e:
                        print(f"Error calculating duration for session {session_id}: {e}")
                        duration = None
            
            # Get AI chat count
            ai_chat_count = ai_chat_data.get(session_id, 0)
            
            # Get participants (owners)
            participants = participants_by_session.get(session_id, [])
            
            # Build meeting dict with direct attribute access
            meeting_dict = {
                "unique_session_id": meeting_obj.unique_session_id,
                "meeting_id": meeting_obj.meeting_id,
                "user_id": meeting_obj.user_id,
                "title": meeting_obj.title,
                "created_at": meeting_obj.created_at,
                "duration_minutes": duration,
                "ai_chat_interactions": ai_chat_count,
                "owners": participants if participants else []
            }
            
            # Get host owner info
            host_owner = None
            if user_obj:
                # Use user_obj from JOIN if available
                meeting_dict.update({
                    "user_email": user_obj.email,
                    "user_name": user_obj.name
                })
                host_owner = {
                    "user_id": user_obj.id,
                    "email": user_obj.email,
                    "name": user_obj.name
                }
            elif meeting_obj.user_id in host_users_lookup:
                # Get from batch query lookup
                host_owner = host_users_lookup[meeting_obj.user_id]
                meeting_dict.update({
                    "user_email": host_owner.get("email"),
                    "user_name": host_owner.get("name")
                })
            
            # Add host to owners if not already present
            if host_owner and host_owner.get("user_id"):
                host_user_id = host_owner.get("user_id")
                if not any(p.get("user_id") == host_user_id for p in meeting_dict["owners"]):
                    meeting_dict["owners"].insert(0, host_owner)
            
            meetings_with_duration.append(meeting_dict)
        except Exception as e:
            # Log error but continue processing
            print(f"Error building meeting dict for session {session_id}: {e}")
            continue
    
    return meetings_with_duration


# =====================
# Authentication
# =====================


class AdminLoginIn(BaseModel):
    username: str
    password: str


class AdminLoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=AdminLoginOut)
def admin_login(data: AdminLoginIn):
    admin_identity = verify_admin_credentials(data.username, data.password)
    token = create_admin_jwt(admin_identity)
    return AdminLoginOut(access_token=token)


@router.post("/logout")
def admin_logout(_: Dict[str, Any] = Depends(get_current_admin)):
    # Stateless JWT — client should discard the token. Endpoint provided for UI symmetry.
    return {"detail": "Logged out"}


# =====================
# Dashboard & Analytics
# =====================


@router.get("/dashboard/metrics")
async def dashboard_metrics(_: Dict[str, Any] = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    """
    Ultra-fast dashboard metrics using PostgreSQL table statistics and caching.
    This avoids expensive COUNT(*) operations on large tables.
    """
    # Check cache first
    cached_data = get_cached_metrics()
    if cached_data:
        return cached_data
    try:
        # Use PostgreSQL's pg_stat_user_tables for approximate counts (much faster)
        # This gives us table statistics without scanning the entire table
        pg_stats_query = text("""
            SELECT 
                COALESCE((SELECT n_tup_ins - n_tup_del FROM pg_stat_user_tables WHERE relname = 'users'), 0) as users_count,
                COALESCE((SELECT n_tup_ins - n_tup_del FROM pg_stat_user_tables WHERE relname = 'meetings'), 0) as meetings_count,
                COALESCE((SELECT n_tup_ins - n_tup_del FROM pg_stat_user_tables WHERE relname = 'chat_messages'), 0) as chat_messages_count
        """)
        
        # Execute the fast statistics query
        stats_result = await db.execute(pg_stats_query)
        stats = stats_result.first()
        
        # For smaller tables (prompts), we can still use exact counts since they're small
        prompts_query = select(
            func.count(case((Prompt.prompt_type == "admin", 1))).label('admin_prompts'),
            func.count(case((Prompt.prompt_type == "user", 1))).label('user_prompts')
        )
        
        prompts_result = await db.execute(prompts_query)
        prompts = prompts_result.first()
        
        # If pg_stat_user_tables returns 0 (stats not available), fall back to exact counts for critical tables
        users_count = stats.users_count if stats.users_count > 0 else await db.scalar(select(func.count(User.id)))
        meetings_count = stats.meetings_count if stats.meetings_count > 0 else await db.scalar(select(func.count(Meeting.unique_session_id)))
        
        result_data = {
            "users": users_count or 0,
            "meetings": meetings_count or 0,
            "chat_messages": stats.chat_messages_count or 0,
            "admin_prompts": prompts.admin_prompts or 0,
            "user_prompts": prompts.user_prompts or 0,
        }
        
        # Cache the result
        set_cached_metrics(result_data)
        return result_data
        
    except Exception as e:
        # Fallback to exact counts if PostgreSQL stats are not available
        print(f"Stats query failed, falling back to exact counts: {e}")
        
        # Parallel execution of smaller counts for better performance
        
        users_count, meetings_count, admin_prompts, user_prompts = await asyncio.gather(
            db.scalar(select(func.count(User.id))),
            db.scalar(select(func.count(Meeting.unique_session_id))),
            db.scalar(select(func.count(Prompt.id)).where(Prompt.prompt_type == "admin")),
            db.scalar(select(func.count(Prompt.id)).where(Prompt.prompt_type == "user"))
        )
        
        # For chat messages, use approximate count if needed
        try:
            messages_approx = await db.execute(text("SELECT reltuples::bigint FROM pg_class WHERE relname = 'chat_messages'"))
            messages_count = messages_approx.scalar() or 0
        except:
            # Fallback: exact count for chat messages (smaller table)
            messages_count = await db.scalar(select(func.count(ChatMessage.id))) or 0
        
        fallback_data = {
            "users": users_count or 0,
            "meetings": meetings_count or 0,
            "chat_messages": messages_count,
            "admin_prompts": admin_prompts or 0,
            "user_prompts": user_prompts or 0,
        }
        
        # Cache the fallback result too
        set_cached_metrics(fallback_data)
        return fallback_data


@router.get("/dashboard/activity-feed")
async def dashboard_activity(_: Dict[str, Any] = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    meetings_result = await db.execute(
        select(Meeting).order_by(Meeting.created_at.desc()).limit(10)
    )
    latest_meetings = meetings_result.scalars().all()
    
    segments_result = await db.execute(
        select(TranscriptSegment).order_by(TranscriptSegment.created_at.desc()).limit(10)
    )
    latest_segments = segments_result.scalars().all()
    
    # Add duration to meetings
    meetings_with_duration = await get_meetings_with_duration_batch(db, latest_meetings)
    
    return {
        "recent_meetings": meetings_with_duration,
        "recent_segments": [
            {
                "id": s.id,
                "session_id": s.session_id,
                "speaker": s.speaker_username,
                "timestamp": s.timestamp,
                "created_at": s.created_at,
            }
            for s in latest_segments
        ],
    }


@router.get("/dashboard/system-health")
def dashboard_system_health(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"status": "ok"}


# Real-time metrics (placeholders — can be wired to real telemetry later)
@router.get("/metrics/users/active")
def metrics_users_active(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"active_users": 0}


@router.get("/metrics/meetings/today")
def metrics_meetings_today(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"meetings_today": 0}


@router.get("/metrics/ai/usage")
def metrics_ai_usage(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"ai_usage": {}}


@router.get("/metrics/system/performance")
def metrics_system_performance(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"latency_ms_p50": 0, "latency_ms_p95": 0}


# =====================
# Analytics Endpoints
# =====================

@router.get("/analytics/users/registrations", response_model=AdminAnalyticsResponse)
async def analytics_user_registrations(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    group_by: str = Query("day", description="Grouping interval: day, week, month, year"),
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Returns time-series data showing user registration counts over time"""
    
    # Validate parameters
    start_dt, end_dt = validate_date_params(start_date, end_date)
    group_by = validate_group_by(group_by)
    date_trunc_format = get_date_trunc_format(group_by)
    
    # Build query
    query = select(
        func.date_trunc(date_trunc_format, User.created_at).label('date'),
        func.count(User.id).label('count')
    )
    
    # Apply date filters
    if start_dt:
        query = query.where(User.created_at >= start_dt)
    if end_dt:
        query = query.where(User.created_at <= end_dt)
    
    query = query.group_by(func.date_trunc(date_trunc_format, User.created_at)).order_by('date')
    
    # Execute query
    result = await db.execute(query)
    data_points = result.all()
    
    # Get total registrations for metadata
    total_query = select(func.count(User.id))
    if start_dt:
        total_query = total_query.where(User.created_at >= start_dt)
    if end_dt:
        total_query = total_query.where(User.created_at <= end_dt)
    
    total_registrations = await db.scalar(total_query)
    
    # Format response
    data = [
        AdminAnalyticsDataPoint(
            date=row.date.strftime('%Y-%m-%d'),
            count=row.count
        )
        for row in data_points
    ]
    
    metadata = AdminAnalyticsMetadata(
        total_registrations=total_registrations,
        start_date=start_date,
        end_date=end_date,
        group_by=group_by
    )
    
    return AdminAnalyticsResponse(data=data, metadata=metadata)


@router.get("/analytics/meetings/counts", response_model=AdminAnalyticsResponse)
async def analytics_meeting_counts(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    group_by: str = Query("day", description="Grouping interval: day, week, month, year"),
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Returns time-series data showing meeting counts over time"""
    
    # Validate parameters
    start_dt, end_dt = validate_date_params(start_date, end_date)
    group_by = validate_group_by(group_by)
    date_trunc_format = get_date_trunc_format(group_by)
    
    # Build query
    query = select(
        func.date_trunc(date_trunc_format, Meeting.created_at).label('date'),
        func.count(func.distinct(Meeting.unique_session_id)).label('count')
    )
    
    # Apply date filters
    if start_dt:
        query = query.where(Meeting.created_at >= start_dt)
    if end_dt:
        query = query.where(Meeting.created_at <= end_dt)
    
    query = query.group_by(func.date_trunc(date_trunc_format, Meeting.created_at)).order_by('date')
    
    # Execute query
    result = await db.execute(query)
    data_points = result.all()
    
    # Get total meetings for metadata
    total_query = select(func.count(func.distinct(Meeting.unique_session_id)))
    if start_dt:
        total_query = total_query.where(Meeting.created_at >= start_dt)
    if end_dt:
        total_query = total_query.where(Meeting.created_at <= end_dt)
    
    total_meetings = await db.scalar(total_query)
    
    # Format response
    data = [
        AdminAnalyticsDataPoint(
            date=row.date.strftime('%Y-%m-%d'),
            count=row.count
        )
        for row in data_points
    ]
    
    metadata = AdminAnalyticsMetadata(
        total_meetings=total_meetings,
        start_date=start_date,
        end_date=end_date,
        group_by=group_by
    )
    
    return AdminAnalyticsResponse(data=data, metadata=metadata)


@router.get("/analytics/meetings/durations", response_model=AdminMeetingDurationResponse)
async def analytics_meeting_durations(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    group_by: str = Query("day", description="Grouping interval: day, week, month, year"),
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Returns time-series data showing average meeting durations over time"""
    
    # Validate parameters
    start_dt, end_dt = validate_date_params(start_date, end_date)
    group_by = validate_group_by(group_by)
    date_trunc_format = get_date_trunc_format(group_by)
    
    # Build complex query to calculate durations from transcript segments
    # First, get duration for each meeting by calculating time difference between first and last segment
    duration_subquery = select(
        Meeting.unique_session_id,
        Meeting.created_at,
        (func.extract('epoch', func.max(TranscriptSegment.timestamp)) - 
         func.extract('epoch', func.min(TranscriptSegment.timestamp))).label('duration_seconds')
    ).select_from(
        Meeting.join(TranscriptSegment, Meeting.unique_session_id == TranscriptSegment.session_id)
    ).group_by(Meeting.unique_session_id, Meeting.created_at).subquery()
    
    # Now group by date and calculate statistics
    query = select(
        func.date_trunc(date_trunc_format, duration_subquery.c.created_at).label('date'),
        func.avg(duration_subquery.c.duration_seconds / 60.0).label('avg_duration'),
        func.min(duration_subquery.c.duration_seconds / 60.0).label('min_duration'),
        func.max(duration_subquery.c.duration_seconds / 60.0).label('max_duration'),
        func.count(duration_subquery.c.unique_session_id).label('meeting_count')
    )
    
    # Apply date filters
    if start_dt:
        query = query.where(duration_subquery.c.created_at >= start_dt)
    if end_dt:
        query = query.where(duration_subquery.c.created_at <= end_dt)
    
    query = query.group_by(func.date_trunc(date_trunc_format, duration_subquery.c.created_at)).order_by('date')
    
    # Execute query
    result = await db.execute(query)
    data_points = result.all()
    
    # Calculate overall average duration for metadata
    overall_avg_query = select(
        func.avg(duration_subquery.c.duration_seconds / 60.0)
    )
    if start_dt:
        overall_avg_query = overall_avg_query.where(duration_subquery.c.created_at >= start_dt)
    if end_dt:
        overall_avg_query = overall_avg_query.where(duration_subquery.c.created_at <= end_dt)
    
    overall_avg_duration = await db.scalar(overall_avg_query)
    
    # Format response
    data = [
        AdminMeetingDurationDataPoint(
            date=row.date.strftime('%Y-%m-%d'),
            avg_duration=round(float(row.avg_duration or 0), 2),
            min_duration=round(float(row.min_duration or 0), 2),
            max_duration=round(float(row.max_duration or 0), 2),
            meeting_count=row.meeting_count
        )
        for row in data_points
    ]
    
    metadata = AdminAnalyticsMetadata(
        overall_avg_duration=round(float(overall_avg_duration or 0), 2),
        start_date=start_date,
        end_date=end_date,
        group_by=group_by
    )
    
    return AdminMeetingDurationResponse(data=data, metadata=metadata)


@router.get("/analytics/meetings/detailed", response_model=AdminDetailedMeetingsResponse)
async def analytics_meetings_detailed(
    start_date: Optional[str] = Query(None, description="Filter by meeting creation date (start)"),
    end_date: Optional[str] = Query(None, description="Filter by meeting creation date (end)"),
    search: Optional[str] = Query(None, description="Search by meeting title or ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field: created_at, duration, participants"),
    sort_order: str = Query("desc", description="Sort direction: asc, desc"),
    all: bool = Query(False, description="Return all meetings without pagination"),
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Returns detailed meeting information with participant counts, durations, and message statistics"""
    
    # Validate parameters
    start_dt, end_dt = validate_date_params(start_date, end_date)
    
    # Validate sort parameters
    valid_sort_fields = ["created_at", "duration", "participants"]
    if sort_by not in valid_sort_fields:
        sort_by = "created_at"
    
    if sort_order not in ["asc", "desc"]:
        sort_order = "desc"
    
    # Import here to avoid circular dependencies
    from dapmeet.models.meeting import meeting_participants
    
    # Build complex query with all required data
    # Subquery for participant counts - use meeting_participants table
    # Count distinct user_ids per session
    participant_subquery = select(
        meeting_participants.c.session_id.label('unique_session_id'),
        func.count(func.distinct(meeting_participants.c.user_id)).label('participant_count')
    ).group_by(meeting_participants.c.session_id).subquery()
    
    # Subquery for segment counts
    segment_subquery = select(
        Meeting.unique_session_id,
        func.count(TranscriptSegment.id).label('segments_count')
    ).select_from(
        Meeting
    ).join(
        TranscriptSegment, Meeting.unique_session_id == TranscriptSegment.session_id, isouter=True
    ).group_by(Meeting.unique_session_id).subquery()
    
    # Subquery for chat message counts
    message_subquery = select(
        Meeting.unique_session_id,
        func.count(ChatMessage.id).label('messages_count')
    ).select_from(
        Meeting
    ).join(
        ChatMessage, Meeting.unique_session_id == ChatMessage.session_id, isouter=True
    ).group_by(Meeting.unique_session_id).subquery()
    
    # Subquery for duration calculation
    duration_subquery = select(
        Meeting.unique_session_id,
        ((func.extract('epoch', func.max(TranscriptSegment.timestamp)) - 
          func.extract('epoch', func.min(TranscriptSegment.timestamp))) / 60.0).label('duration_minutes')
    ).select_from(
        Meeting
    ).join(
        TranscriptSegment, Meeting.unique_session_id == TranscriptSegment.session_id, isouter=True
    ).group_by(Meeting.unique_session_id).subquery()
    
    # Main query
    base_query = select(
        Meeting.meeting_id,
        Meeting.unique_session_id,
        Meeting.title,
        Meeting.created_at,
        Meeting.user_id,
        User.name.label('host_user_name'),
        User.email.label('host_user_email'),
        func.coalesce(participant_subquery.c.participant_count, 0).label('participant_count'),
        func.coalesce(segment_subquery.c.segments_count, 0).label('speech_segments_count'),
        func.coalesce(message_subquery.c.messages_count, 0).label('chat_messages_count'),
        func.coalesce(duration_subquery.c.duration_minutes, 0).label('duration_minutes')
    ).select_from(
        Meeting
    ).join(
        User, Meeting.user_id == User.id
    ).join(
        participant_subquery, Meeting.unique_session_id == participant_subquery.c.unique_session_id, isouter=True
    ).join(
        segment_subquery, Meeting.unique_session_id == segment_subquery.c.unique_session_id, isouter=True
    ).join(
        message_subquery, Meeting.unique_session_id == message_subquery.c.unique_session_id, isouter=True
    ).join(
        duration_subquery, Meeting.unique_session_id == duration_subquery.c.unique_session_id, isouter=True
    )
    
    # Apply filters
    if start_dt:
        base_query = base_query.where(Meeting.created_at >= start_dt)
    if end_dt:
        base_query = base_query.where(Meeting.created_at <= end_dt)
    if search:
        base_query = base_query.where(
            (Meeting.title.ilike(f"%{search}%")) | 
            (Meeting.meeting_id.ilike(f"%{search}%"))
        )
    
    # Get total count for pagination (simplified to avoid complex subquery)
    # Count meetings directly with same filters
    count_query = select(func.count(Meeting.unique_session_id)).select_from(Meeting)
    if start_dt:
        count_query = count_query.where(Meeting.created_at >= start_dt)
    if end_dt:
        count_query = count_query.where(Meeting.created_at <= end_dt)
    if search:
        count_query = count_query.where(
            (Meeting.title.ilike(f"%{search}%")) | 
            (Meeting.meeting_id.ilike(f"%{search}%"))
        )
    total = await db.scalar(count_query)
    
    # Apply sorting
    if sort_by == "created_at":
        sort_column = Meeting.created_at
    elif sort_by == "duration":
        sort_column = duration_subquery.c.duration_minutes
    elif sort_by == "participants":
        sort_column = participant_subquery.c.participant_count
    else:
        sort_column = Meeting.created_at
    
    if sort_order == "desc":
        base_query = base_query.order_by(sort_column.desc().nulls_last())
    else:
        base_query = base_query.order_by(sort_column.asc().nulls_last())
    
    # Apply pagination only if not requesting all records
    if not all:
        offset = (page - 1) * limit
        base_query = base_query.offset(offset).limit(limit)
    
    # Execute query with error handling
    try:
        result = await db.execute(base_query)
        meetings = result.all()
    except Exception as e:
        logger.error(f"Error executing analytics query: {str(e)}", exc_info=True)
        # Try to refresh connection
        await db.rollback()
        # Retry once
        try:
            result = await db.execute(base_query)
            meetings = result.all()
        except Exception as retry_error:
            logger.error(f"Retry also failed: {str(retry_error)}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="Database query failed. Please try again later."
            )
    
    # Calculate pagination metadata
    if all:
        # When returning all records, pagination info reflects the complete dataset
        total_pages = 1
        has_next = False
        has_prev = False
        page = 1
        limit = total
    else:
        total_pages = (total + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
    
    # Format response with all data
    data = [
        AdminDetailedMeeting(
            meeting_id=meeting.meeting_id,
            unique_session_id=meeting.unique_session_id,
            title=meeting.title,
            created_at=meeting.created_at,
            duration_minutes=round(float(meeting.duration_minutes or 0), 2),
            participant_count=meeting.participant_count,
            speech_segments_count=meeting.speech_segments_count,
            chat_messages_count=meeting.chat_messages_count,
            host_user_id=meeting.user_id,
            host_user_name=meeting.host_user_name,
            host_user_email=meeting.host_user_email
        )
        for meeting in meetings
    ]
    
    pagination = AdminPaginationInfo(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )
    
    filters = {
        "start_date": start_date,
        "end_date": end_date,
        "search": search
    }
    
    return AdminDetailedMeetingsResponse(data=data, pagination=pagination, filters=filters)


@router.get("/analytics/dashboard/metrics", response_model=AdminDashboardMetricsResponse)
async def analytics_dashboard_metrics(
    start_date: Optional[str] = Query(None, description="Start date for filtering"),
    end_date: Optional[str] = Query(None, description="End date for filtering"),
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Returns aggregate metrics for the dashboard, optionally filtered by date range"""
    
    # Validate parameters
    start_dt, end_dt = validate_date_params(start_date, end_date)
    
    # Build queries with optional date filtering
    
    # Users count (filtered by registration date if dates provided)
    users_query = select(func.count(User.id))
    if start_dt:
        users_query = users_query.where(User.created_at >= start_dt)
    if end_dt:
        users_query = users_query.where(User.created_at <= end_dt)
    
    # Meetings count (filtered by creation date if dates provided)
    meetings_query = select(func.count(func.distinct(Meeting.unique_session_id)))
    if start_dt:
        meetings_query = meetings_query.where(Meeting.created_at >= start_dt)
    if end_dt:
        meetings_query = meetings_query.where(Meeting.created_at <= end_dt)
    
    # Speech segments count (filtered by meeting creation date)
    segments_query = select(func.count(TranscriptSegment.id)).select_from(
        TranscriptSegment.join(Meeting, TranscriptSegment.session_id == Meeting.unique_session_id)
    )
    if start_dt:
        segments_query = segments_query.where(Meeting.created_at >= start_dt)
    if end_dt:
        segments_query = segments_query.where(Meeting.created_at <= end_dt)
    
    # Chat messages count (filtered by meeting creation date)
    messages_query = select(func.count(ChatMessage.id)).select_from(
        ChatMessage.join(Meeting, ChatMessage.session_id == Meeting.unique_session_id)
    )
    if start_dt:
        messages_query = messages_query.where(Meeting.created_at >= start_dt)
    if end_dt:
        messages_query = messages_query.where(Meeting.created_at <= end_dt)
    
    # Execute all queries in parallel
    users_count, meetings_count, segments_count, messages_count = await asyncio.gather(
        db.scalar(users_query),
        db.scalar(meetings_query),
        db.scalar(segments_query),
        db.scalar(messages_query)
    )
    
    # Format response
    data = AdminDashboardMetricsData(
        users=users_count or 0,
        meetings=meetings_count or 0,
        segments=segments_count or 0,
        chat_messages=messages_count or 0
    )
    
    metadata = {
        "filtered": bool(start_date or end_date),
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    return AdminDashboardMetricsResponse(data=data, metadata=metadata)


@router.get("/analytics/users/detailed", response_model=AdminDetailedUsersResponse)
async def analytics_users_detailed(
    start_date: Optional[str] = Query(None, description="Filter users by registration date"),
    end_date: Optional[str] = Query(None, description="Filter users by registration date"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Returns user list with meeting and message counts"""
    
    # Validate parameters
    start_dt, end_dt = validate_date_params(start_date, end_date)
    
    # Subquery for meeting counts and total duration
    meeting_stats_subquery = select(
        Meeting.user_id,
        func.count(Meeting.unique_session_id).label('meeting_count'),
        func.sum(
            func.coalesce(
                (func.extract('epoch', func.max(TranscriptSegment.timestamp)) - 
                 func.extract('epoch', func.min(TranscriptSegment.timestamp))) / 60.0,
                0
            )
        ).label('total_duration')
    ).select_from(
        Meeting.join(TranscriptSegment, Meeting.unique_session_id == TranscriptSegment.session_id, isouter=True)
    ).group_by(Meeting.user_id).subquery()
    
    # Subquery for message counts
    message_stats_subquery = select(
        Meeting.user_id,
        func.count(ChatMessage.id).label('message_count')
    ).select_from(
        Meeting.join(ChatMessage, Meeting.unique_session_id == ChatMessage.session_id, isouter=True)
    ).group_by(Meeting.user_id).subquery()
    
    # Main query
    base_query = select(
        User.id,
        User.name,
        User.email,
        User.created_at,
        func.coalesce(meeting_stats_subquery.c.meeting_count, 0).label('meeting_count'),
        func.coalesce(message_stats_subquery.c.message_count, 0).label('message_count'),
        func.coalesce(meeting_stats_subquery.c.total_duration, 0).label('total_meeting_duration')
    ).select_from(
        User.join(meeting_stats_subquery, User.id == meeting_stats_subquery.c.user_id, isouter=True)
        .join(message_stats_subquery, User.id == message_stats_subquery.c.user_id, isouter=True)
    )
    
    # Apply filters
    if start_dt:
        base_query = base_query.where(User.created_at >= start_dt)
    if end_dt:
        base_query = base_query.where(User.created_at <= end_dt)
    if search:
        base_query = base_query.where(
            (User.name.ilike(f"%{search}%")) | 
            (User.email.ilike(f"%{search}%"))
        )
    
    # Get total count for pagination
    total = await db.scalar(select(func.count()).select_from(base_query.subquery()))
    
    # Apply pagination and ordering
    offset = (page - 1) * limit
    base_query = base_query.order_by(User.created_at.desc()).offset(offset).limit(limit)
    
    # Execute query
    result = await db.execute(base_query)
    users = result.all()
    
    # Calculate pagination metadata
    total_pages = (total + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    # Format response
    data = [
        AdminDetailedUser(
            id=user.id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            meeting_count=user.meeting_count,
            message_count=user.message_count,
            total_meeting_duration=round(float(user.total_meeting_duration or 0), 2),
            status="active"
        )
        for user in users
    ]
    
    pagination = AdminPaginationInfo(
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )
    
    return AdminDetailedUsersResponse(data=data, pagination=pagination)


# =====================
# User Management
# =====================

async def get_users_count(db: AsyncSession = Depends(get_async_db)):
    return await db.scalar(select(func.count(User.id)))

@router.get("/users")
async def list_users(
    search: Optional[str] = None,
    limit: int = Depends(get_users_count),
    page: int = 1,
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    # Validate parameters
    if page < 1:
        page = 1
    
    
    # Create subquery for meeting counts
    meeting_count_subquery = (
        select(
            Meeting.user_id,
            func.count(Meeting.unique_session_id).label('meeting_count')
        )
        .group_by(Meeting.user_id)
        .subquery()
    )
    
    # Create subquery for message counts
    message_count_subquery = (
        select(
            Meeting.user_id,
            func.count(ChatMessage.id).label('message_count')
        )
        .select_from(Meeting)
        .join(ChatMessage, Meeting.unique_session_id == ChatMessage.session_id, isouter=True)
        .group_by(Meeting.user_id)
        .subquery()
    )
    
    # Build main query with meeting and message counts
    base_stmt = (
        select(
            User.id,
            User.email,
            User.name,
            User.created_at,
            func.coalesce(meeting_count_subquery.c.meeting_count, 0).label('total_meetings'),
            func.coalesce(message_count_subquery.c.message_count, 0).label('total_messages')
        )
        .select_from(User)
        .join(meeting_count_subquery, User.id == meeting_count_subquery.c.user_id, isouter=True)
        .join(message_count_subquery, User.id == message_count_subquery.c.user_id, isouter=True)
    )
    
    if search:
        # Search in both email and name fields
        base_stmt = base_stmt.where(
            (User.email.ilike(f"%{search}%")) | 
            (User.name.ilike(f"%{search}%"))
        )
    
    total = await db.scalar(select(func.count()).select_from(base_stmt.subquery()))
    
    # Calculate offset based on page number
    offset = (page - 1) * limit
    
    users_result = await db.execute(
        base_stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    users = users_result.all()
    
    items = [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "created_at": u.created_at,
            "meeting_count": u.total_meetings,
            "message_count": u.total_messages,
        }
        for u in users
    ]
    
    # Calculate pagination metadata
    total_pages = (total + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "total": total,
        "items": items,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev
    }


@router.get("/users/{user_id}")
async def get_user(user_id: str, _: Dict[str, Any] = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get meeting count for this user
    meeting_count = await db.scalar(
        select(func.count(Meeting.unique_session_id))
        .where(Meeting.user_id == user_id)
    )
    
    # Get message count for this user
    message_count = await db.scalar(
        select(func.count(ChatMessage.id))
        .select_from(Meeting)
        .join(ChatMessage, Meeting.unique_session_id == ChatMessage.session_id, isouter=True)
        .where(Meeting.user_id == user_id)
    )
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at,
        "meeting_count": meeting_count or 0,
        "message_count": message_count or 0,
    }


class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.name is not None:
        user.name = payload.name
    if payload.email is not None:
        user.email = payload.email
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at,
    }


@router.get("/users/{user_id}/activity")
async def user_activity(user_id: str, _: Dict[str, Any] = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(Meeting)
        .where(Meeting.user_id == user_id)
        .order_by(Meeting.created_at.desc())
        .limit(10)
    )
    recent_meetings = result.scalars().all()
    
    return {
        "recent_meetings": [
            {
                "unique_session_id": m.unique_session_id,
                "meeting_id": m.meeting_id,
                "title": m.title,
                "created_at": m.created_at,
            }
            for m in recent_meetings
        ]
    }


@router.get("/users/{user_id}/ai-usage")
def user_ai_usage(user_id: str, _: Dict[str, Any] = Depends(get_current_admin)):
    return {"user_id": user_id, "ai_usage": {}}


@router.get("/users/stats")
async def users_stats(_: Dict[str, Any] = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    total_users = await db.scalar(select(func.count(User.id)))
    return {"total_users": total_users}


@router.get("/users/meetings/stats")
async def all_users_meetings_stats(
    search: Optional[str] = Query(None, description="Search by user email or name"),
    limit: int = Query(100, ge=1, le=500, description="Number of users to return"),
    page: int = Query(1, ge=1, description="Page number"),
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Get meeting statistics for all users"""
    # Build base query with meeting count using subquery
    meeting_subquery = (
        select(
            Meeting.user_id,
            func.count(Meeting.unique_session_id).label('meeting_count')
        )
        .group_by(Meeting.user_id)
        .subquery()
    )
    
    # Build subquery for message counts
    message_subquery = (
        select(
            Meeting.user_id,
            func.count(ChatMessage.id).label('message_count')
        )
        .select_from(Meeting)
        .join(ChatMessage, Meeting.unique_session_id == ChatMessage.session_id, isouter=True)
        .group_by(Meeting.user_id)
        .subquery()
    )
    
    # Join users with their meeting and message counts
    base_stmt = (
        select(
            User.id,
            User.email,
            User.name,
            User.created_at,
            func.coalesce(meeting_subquery.c.meeting_count, 0).label('total_meetings'),
            func.coalesce(message_subquery.c.message_count, 0).label('total_messages')
        )
        .select_from(User)
        .join(meeting_subquery, User.id == meeting_subquery.c.user_id, isouter=True)
        .join(message_subquery, User.id == message_subquery.c.user_id, isouter=True)
    )
    
    # Apply search filter
    if search:
        base_stmt = base_stmt.where(
            (User.email.ilike(f"%{search}%")) | 
            (User.name.ilike(f"%{search}%"))
        )
    
    # Get total count for pagination
    total = await db.scalar(select(func.count()).select_from(base_stmt.subquery()))
    
    # Apply pagination and ordering
    offset = (page - 1) * limit
    exec_result = await db.execute(
        base_stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
    )
    results = exec_result.all()
    
    # Calculate pagination metadata
    total_pages = (total + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    return {
        "filters": {
            "search": search
        },
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        },
        "users": [
            {
                "user_id": result.id,
                "user_email": result.email,
                "user_name": result.name,
                "user_created_at": result.created_at,
                "total_meetings": result.total_meetings,
                "total_messages": result.total_messages
            }
            for result in results
        ]
    }


@router.get("/users/{user_id}/meetings/stats")
async def user_meetings_stats(
    user_id: str,
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Get total meetings count for a specific user"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    total_meetings = await db.scalar(select(func.count(Meeting.unique_session_id)).where(Meeting.user_id == user_id))
    
    # Get message count for this user
    total_messages = await db.scalar(
        select(func.count(ChatMessage.id))
        .select_from(Meeting)
        .join(ChatMessage, Meeting.unique_session_id == ChatMessage.session_id, isouter=True)
        .where(Meeting.user_id == user_id)
    )
    
    return {
        "user_id": user_id,
        "user_email": user.email,
        "user_name": user.name,
        "total_meetings": total_meetings,
        "total_messages": total_messages or 0
    }


@router.get("/users/{user_id}/meetings")
async def user_meetings_filtered(
    user_id: str,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=100, description="Number of meetings to return"),
    page: int = Query(1, ge=1, description="Page number"),
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Filter meetings for one user by date or date interval"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Build query
    base_stmt = select(Meeting).where(Meeting.user_id == user_id)
    
    # Apply date filters
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        base_stmt = base_stmt.where(Meeting.created_at >= start_datetime)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        base_stmt = base_stmt.where(Meeting.created_at <= end_datetime)
    
    # Get total count for pagination
    total = await db.scalar(select(func.count()).select_from(base_stmt.subquery()))
    
    # Apply pagination
    offset = (page - 1) * limit
    exec_result = await db.execute(
        base_stmt.order_by(Meeting.created_at.desc()).offset(offset).limit(limit)
    )
    meetings = exec_result.scalars().all()
    
    # Calculate pagination metadata
    total_pages = (total + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    # Add duration to meetings
    meetings_with_duration = await get_meetings_with_duration_batch(db, meetings)
    
    return {
        "user_id": user_id,
        "user_email": user.email,
        "user_name": user.name,
        "filters": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None
        },
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        },
        "meetings": meetings_with_duration
    }


@router.get("/meetings/filtered")
async def all_meetings_filtered(
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=100, description="Number of meetings to return"),
    page: int = Query(1, ge=1, description="Page number"),
    user_search: Optional[str] = Query(None, description="Search by user email or name"),
    all: bool = Query(False, description="Return all meetings without pagination"),
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Filter all users' meetings by date or date interval with optional user search"""
    # Build query with JOIN to User table for search capability
    base_stmt = select(Meeting, User).join(User, Meeting.user_id == User.id)
    
    # Apply date filters
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        base_stmt = base_stmt.where(Meeting.created_at >= start_datetime)
    
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        base_stmt = base_stmt.where(Meeting.created_at <= end_datetime)
    
    # Apply user search filter
    if user_search:
        base_stmt = base_stmt.where(
            (User.email.ilike(f"%{user_search}%")) | 
            (User.name.ilike(f"%{user_search}%"))
        )
    
    # Get total count for pagination
    total = await db.scalar(select(func.count()).select_from(base_stmt.subquery()))
    
    # Apply pagination and order
    if not all:
        offset = (page - 1) * limit
        exec_result = await db.execute(
            base_stmt.order_by(Meeting.created_at.desc()).offset(offset).limit(limit)
        )
    else:
        exec_result = await db.execute(
            base_stmt.order_by(Meeting.created_at.desc())
        )
    meeting_user_pairs = exec_result.all()
    
    # Calculate pagination metadata
    if all:
        # When returning all records, pagination info reflects the complete dataset
        total_pages = 1
        has_next = False
        has_prev = False
        page = 1
        limit = total
    else:
        total_pages = (total + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
    
    # Add duration to meetings
    meetings_with_duration = await get_meetings_with_duration_batch(db, meeting_user_pairs)
    
    return {
        "filters": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "user_search": user_search
        },
        "pagination": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_prev": has_prev
        },
        "meetings": meetings_with_duration
    }


# =====================
# Meeting Management
# =====================

@router.get("/meetings/stats")
async def meetings_stats(_: Dict[str, Any] = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    total_meetings = await db.scalar(select(func.count(Meeting.unique_session_id)))
    total_segments = await db.scalar(select(func.count(TranscriptSegment.id)))
    return {"total_meetings": total_meetings, "total_segments": total_segments}


# =====================
# AI & Processing Management (placeholders)
# =====================


@router.get("/ai/config")
def ai_config_get(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"models": [], "prompts": []}


class AIConfigUpdate(BaseModel):
    config: Dict[str, Any]


@router.put("/ai/config")
def ai_config_put(payload: AIConfigUpdate, _: Dict[str, Any] = Depends(get_current_admin)):
    return {"updated": payload.config}


@router.get("/ai/models")
def ai_models(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"models": []}


@router.get("/ai/prompts")
def ai_prompts(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"prompts": []}


@router.get("/ai/usage-stats")
def ai_usage_stats(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"usage": {}}


@router.get("/ai/performance")
def ai_performance(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"performance": {}}


@router.get("/ai/token-usage")
def ai_token_usage(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"token_usage": {}}


@router.get("/ai/cost-analysis")
def ai_cost_analysis(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"costs": {}}


# =====================
# System Health & Monitoring
# =====================


@router.get("/system/health")
def system_health(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"status": "ok"}


@router.get("/system/health/database")
async def system_health_db(_: Dict[str, Any] = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    # Simple ping by executing a lightweight query
    await db.execute(text("SELECT 1"))
    return {"database": "ok"}


@router.get("/system/database-pool-status")
async def database_pool_status(_: Dict[str, Any] = Depends(get_current_admin)):
    """Monitor database connection pool status for performance debugging"""
    from dapmeet.db.db import async_engine
    
    if async_engine and hasattr(async_engine, 'pool'):
        pool = async_engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(), 
            "overflow": pool.overflow(),
            "invalid": pool.invalid(),
            "total_capacity": pool.size() + pool.overflow(),
            "utilization_percent": round((pool.checkedout() / (pool.size() + pool.overflow())) * 100, 2) if (pool.size() + pool.overflow()) > 0 else 0
        }
    return {"error": "Async engine or pool not available"}


@router.post("/system/clear-metrics-cache")
async def clear_metrics_cache(_: Dict[str, Any] = Depends(get_current_admin)):
    """Clear the dashboard metrics cache to force fresh data"""
    global _metrics_cache
    _metrics_cache = {"data": None, "timestamp": 0, "ttl": 60}
    return {"message": "Metrics cache cleared successfully"}


@router.get("/system/health/ai-services")
def system_health_ai(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"ai_services": "ok"}


@router.get("/system/health/external-apis")
def system_health_external(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"external_apis": "ok"}


@router.get("/system/performance-metrics")
def system_performance_metrics(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"metrics": {}}


# =====================
# Security & Audit (placeholders)
# =====================


@router.get("/audit/logs")
def audit_logs(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"logs": []}


@router.get("/audit/logs/admin-actions")
def audit_logs_admin(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"admin_actions": []}


@router.get("/audit/logs/errors")
def audit_logs_errors(_: Dict[str, Any] = Depends(get_current_admin)):
    return {"errors": []}


# =====================
# Subscription Management
# =====================


@router.get("/subscriptions/{user_id}", response_model=SubscriptionWithHistory)
async def get_user_subscription(
    user_id: str,
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user subscription with full history"""
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.get_subscription_with_history(user_id)
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found"
        )
    
    # Convert to response format
    from dapmeet.schemas.subscription import PLAN_FEATURES
    features = PLAN_FEATURES[subscription.plan.value]
    
    subscription_out = SubscriptionOut(
        id=subscription.id,
        user_id=subscription.user_id,
        plan=subscription.plan.value,
        status=subscription.status.value,
        start_date=subscription.start_date,
        end_date=subscription.end_date,
        last_updated=subscription.last_updated,
        created_at=subscription.created_at,
        features=features
    )
    
    history_out = [
        SubscriptionHistoryOut(
            id=h.id,
            subscription_id=h.subscription_id,
            old_plan=h.old_plan.value if h.old_plan else None,
            new_plan=h.new_plan.value,
            old_status=h.old_status.value if h.old_status else None,
            new_status=h.new_status.value,
            changed_by=h.changed_by,
            reason=h.reason,
            changed_at=h.changed_at
        )
        for h in subscription.history
    ]
    
    return SubscriptionWithHistory(
        subscription=subscription_out,
        history=history_out
    )


@router.put("/subscriptions/{user_id}", response_model=SubscriptionOut)
async def update_user_subscription(
    user_id: str,
    update_data: SubscriptionUpdate,
    admin: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Update user subscription (admin only)"""
    subscription_service = SubscriptionService(db)
    
    # Verify user exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update subscription
    subscription = await subscription_service.update_subscription(
        user_id=user_id,
        update_data=update_data,
        changed_by=admin.get("sub")  # Admin username/ID
    )
    
    # Convert to response format
    from dapmeet.schemas.subscription import PLAN_FEATURES
    features = PLAN_FEATURES[subscription.plan.value]
    
    return SubscriptionOut(
        id=subscription.id,
        user_id=subscription.user_id,
        plan=subscription.plan.value,
        status=subscription.status.value,
        start_date=subscription.start_date,
        end_date=subscription.end_date,
        last_updated=subscription.last_updated,
        created_at=subscription.created_at,
        features=features
    )


