# Admin Developer Rules and Guidelines

## Overview
This document establishes strict rules for developers working exclusively on admin APIs. These rules ensure system integrity and prevent breaking changes to the existing user-facing functionality.

## Core Principles

### 1. **ADMIN-ONLY SCOPE**
- You are **ONLY** allowed to work on admin-related functionality
- Admin endpoints are prefixed with `/admin/` 
- Admin files are located in:
  - `src/dapmeet/api/admin.py`
  - `src/dapmeet/api/admin_prompts.py`
  - `src/dapmeet/services/admin_auth.py`

### 2. **FORBIDDEN MODIFICATIONS**
You are **STRICTLY PROHIBITED** from modifying:

#### Core User APIs
- `src/dapmeet/api/auth.py`
- `src/dapmeet/api/chat.py`
- `src/dapmeet/api/meetings.py`
- `src/dapmeet/api/user_prompts.py`
- `src/dapmeet/api/whisper.py`
- `src/dapmeet/api/webhook.py`

#### Core Services (Non-Admin)
- `src/dapmeet/services/auth.py`
- `src/dapmeet/services/email_service.py`
- `src/dapmeet/services/google_auth_service.py`
- `src/dapmeet/services/meetings.py`
- `src/dapmeet/services/whisper.py`

#### Database and Core Infrastructure
- `src/dapmeet/db/db.py`
- `src/dapmeet/core/deps.py`
- `src/dapmeet/cmd/main.py`
- `alembic/` directory (except for admin-specific migrations)

#### Router Registration
- `src/dapmeet/api/__init__.py` (except adding new admin routers)

## Schema and Model Rules

### 3. **SHARED SCHEMA/MODEL MODIFICATION RULES**

#### Before Modifying ANY Existing Schema or Model:
1. **MANDATORY DEPENDENCY CHECK**: Use these commands to check if the schema/model is used elsewhere:
   ```bash
   # Check for imports of the schema/model
   grep -r "from.*schemas\.SCHEMA_NAME" src/
   grep -r "from.*models\.MODEL_NAME" src/
   
   # Check for usage in non-admin files
   grep -r "SCHEMA_NAME\|MODEL_NAME" src/dapmeet/api/ --exclude="*admin*"
   grep -r "SCHEMA_NAME\|MODEL_NAME" src/dapmeet/services/ --exclude="*admin*"
   ```

2. **IF USED IN NON-ADMIN CODE**: 
   - **DO NOT MODIFY** the existing schema/model
   - **CREATE A NEW ADMIN VERSION** with `Admin` prefix
   - Example: `PromptResponse` → `AdminPromptResponse`

3. **IF ONLY USED IN ADMIN CODE**:
   - You may modify it carefully
   - Ensure all admin endpoints still work after changes

### 4. **ADMIN PREFIX NAMING CONVENTION**

When creating admin-specific versions of existing schemas/models:

#### Schema Examples:
```python
# Original (DO NOT MODIFY if used elsewhere)
class PromptResponse(BaseModel):
    id: int
    name: str
    content: str

# Admin version (CREATE THIS)
class AdminPromptResponse(BaseModel):
    id: int
    name: str
    content: str
    admin_metadata: Optional[Dict] = None  # Admin-specific fields
```

#### Model Examples:
```python
# If you need admin-specific model behavior
class AdminPrompt(Base):
    __tablename__ = "admin_prompts"  # Different table if needed
    # ... admin-specific fields
```

### 5. **CURRENT SHARED COMPONENTS STATUS**

#### Currently Shared (REQUIRE ADMIN PREFIX IF MODIFIED):
- `src/dapmeet/schemas/prompt.py` - Used by both admin and user APIs
- `src/dapmeet/models/prompt.py` - Used by both admin and user APIs
- `src/dapmeet/services/prompts.py` - Used by both admin and user APIs

#### Admin-Only (CAN MODIFY):
- `src/dapmeet/services/admin_auth.py`
- Admin-specific schemas in `admin.py` and `admin_prompts.py`

## Development Workflow

### 6. **MANDATORY PRE-DEVELOPMENT CHECKS**

Before starting any task:

1. **Identify all components you need to modify**
2. **For each component, run dependency checks**:
   ```bash
   # Example for prompt schema
   grep -r "from dapmeet.schemas.prompt" src/ --exclude-dir="*admin*"
   grep -r "PromptResponse\|PromptCreate\|PromptUpdate" src/dapmeet/api/ --exclude="*admin*"
   ```
3. **If ANY non-admin usage found**: Create admin-prefixed versions
4. **Document your changes** in commit messages

### 7. **SAFE MODIFICATION PATTERNS**

#### ✅ ALLOWED:
```python
# Creating new admin endpoints
@router.post("/admin/new-feature")
async def new_admin_feature():
    pass

# Creating admin-specific schemas
class AdminUserResponse(BaseModel):
    # Admin-specific user data
    pass

# Modifying admin-only files
# - admin.py
# - admin_prompts.py  
# - admin_auth.py
```

#### ❌ FORBIDDEN:
```python
# Modifying shared schemas used by user APIs
class PromptResponse(BaseModel):  # DON'T MODIFY IF USED ELSEWHERE
    new_field: str  # This breaks user APIs!

# Changing core models
class User(Base):  # NEVER MODIFY
    admin_field: str  # This affects all user functionality!

# Modifying non-admin services
class AuthService:  # FORBIDDEN
    def new_method(self):  # This affects user authentication!
```

### 8. **TESTING REQUIREMENTS**

Before submitting any changes:

1. **Test admin functionality works**
2. **Verify user APIs still work** (if you modified shared components)
3. **Run existing tests** to ensure no breakage
4. **Test database migrations** work correctly

### 9. **DATABASE CHANGES**

#### For Admin-Specific Tables:
- Create new migration files in `alembic/versions/`
- Use descriptive names: `YYYY_MM_DD_HHMM_admin_feature_name.py`
- Only modify admin-related tables

#### For Existing Tables:
- **NEVER** drop or rename existing columns used by user APIs
- **ONLY** add new optional columns if absolutely necessary
- Always add `nullable=True` for new columns

### 10. **CODE REVIEW CHECKLIST**

Before submitting code:

- [ ] No modifications to user-facing APIs
- [ ] No modifications to core services (non-admin)
- [ ] Dependency checks performed for all modified schemas/models
- [ ] Admin prefixes used for shared component modifications
- [ ] All admin endpoints tested
- [ ] No breaking changes to existing functionality
- [ ] Database migrations are admin-specific only

## Emergency Procedures

### If You Accidentally Break Something:

1. **Immediately revert your changes**
2. **Check what user APIs are affected**
3. **Create admin-prefixed versions instead**
4. **Test thoroughly before resubmitting**

### If You Need to Modify Core Functionality:

1. **STOP** - This is likely outside your scope
2. **Consult with the team lead**
3. **Document why the change is necessary**
4. **Get explicit approval before proceeding**

## Examples

### ✅ Good: Creating Admin-Specific Schema
```python
# In admin_prompts.py
class AdminPromptDetailResponse(BaseModel):
    """Admin-specific prompt response with additional metadata"""
    id: int
    name: str
    content: str
    prompt_type: str
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    # Admin-specific fields
    usage_count: int
    last_used: Optional[datetime]
    admin_notes: Optional[str]
```

### ✅ Good: Adding Admin Endpoint
```python
# In admin.py
@router.get("/prompts/analytics")
async def get_prompt_analytics(
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Admin-only prompt analytics"""
    # Implementation here
```

### ❌ Bad: Modifying Shared Schema
```python
# DON'T DO THIS if PromptResponse is used in user_prompts.py
class PromptResponse(BaseModel):
    id: int
    name: str
    content: str
    admin_metadata: Dict  # This breaks user APIs!
```

### ✅ Good: Admin Service Extension
```python
# Create new admin-specific service methods
class AdminPromptService(PromptService):
    """Extended prompt service with admin capabilities"""
    
    async def get_prompt_analytics(self):
        # Admin-specific functionality
        pass
```

## Summary

**Remember**: Your role is to enhance admin functionality without breaking existing user features. When in doubt, create admin-specific versions with the `Admin` prefix rather than modifying shared components.

**Key Mantra**: "If it's used outside admin APIs, create an Admin-prefixed version instead of modifying it."
