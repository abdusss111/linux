# Admin Developer Quick Reference

## 🚨 Before Making ANY Changes - Run These Commands

### Check if Schema/Model is Used Elsewhere:
```bash
# Replace SCHEMA_NAME with actual schema name (e.g., PromptResponse)
grep -r "from.*schemas\.SCHEMA_NAME" src/ --exclude-dir="*admin*"
grep -r "SCHEMA_NAME" src/dapmeet/api/ --exclude="*admin*"

# Replace MODEL_NAME with actual model name (e.g., Prompt)  
grep -r "from.*models\.MODEL_NAME" src/ --exclude-dir="*admin*"
grep -r "MODEL_NAME" src/dapmeet/api/ --exclude="*admin*"
```

### Quick Dependency Check for Common Components:
```bash
# Check prompt schema usage
grep -r "PromptResponse\|PromptCreate\|PromptUpdate" src/dapmeet/api/ --exclude="*admin*"

# Check prompt model usage
grep -r "from dapmeet.models.prompt" src/ --exclude-dir="*admin*"

# Check user model usage  
grep -r "from dapmeet.models.user" src/ --exclude-dir="*admin*"
```

## ✅ Files You CAN Modify

### Admin API Files:
- `src/dapmeet/api/admin.py`
- `src/dapmeet/api/admin_prompts.py`

### Admin Services:
- `src/dapmeet/services/admin_auth.py`

### Admin Migrations:
- `alembic/versions/` (new admin-specific migrations only)

## ❌ Files You CANNOT Modify

### User APIs (FORBIDDEN):
- `src/dapmeet/api/auth.py`
- `src/dapmeet/api/chat.py` 
- `src/dapmeet/api/meetings.py`
- `src/dapmeet/api/user_prompts.py`
- `src/dapmeet/api/whisper.py`
- `src/dapmeet/api/webhook.py`

### Core Services (FORBIDDEN):
- `src/dapmeet/services/auth.py`
- `src/dapmeet/services/email_service.py`
- `src/dapmeet/services/google_auth_service.py`
- `src/dapmeet/services/meetings.py`
- `src/dapmeet/services/whisper.py`

### Infrastructure (FORBIDDEN):
- `src/dapmeet/db/db.py`
- `src/dapmeet/core/deps.py`
- `src/dapmeet/cmd/main.py`

## 🔄 Shared Components (REQUIRE ADMIN PREFIX)

### Currently Shared - Use Admin Prefix if Modifying:
- `src/dapmeet/schemas/prompt.py` → Create `AdminPromptResponse`, etc.
- `src/dapmeet/models/prompt.py` → Create `AdminPrompt` if needed
- `src/dapmeet/services/prompts.py` → Create `AdminPromptService` if needed

## 📝 Quick Templates

### Admin Schema Template:
```python
class AdminSomethingResponse(BaseModel):
    """Admin-specific response with additional metadata"""
    # Copy fields from original schema
    id: int
    name: str
    # Add admin-specific fields
    admin_metadata: Optional[Dict] = None
    usage_stats: Optional[Dict] = None
```

### Admin Endpoint Template:
```python
@router.get("/admin/new-feature")
async def admin_new_feature(
    _: Dict[str, Any] = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    """Admin-only feature description"""
    # Implementation
    return {"result": "success"}
```

### Admin Service Extension:
```python
class AdminSomeService(ExistingService):
    """Extended service with admin capabilities"""
    
    async def admin_specific_method(self):
        # Admin functionality
        pass
```

## 🧪 Pre-Commit Checklist

- [ ] Ran dependency checks for modified schemas/models
- [ ] Used Admin prefix for any shared component modifications  
- [ ] Only modified admin-specific files
- [ ] Tested admin endpoints work
- [ ] No changes to user-facing APIs
- [ ] Database migrations are admin-only

## 🆘 Emergency Commands

### If You Break Something:
```bash
# Revert your changes
git checkout -- src/dapmeet/api/FILENAME.py

# Check what's affected
grep -r "MODIFIED_COMPONENT" src/dapmeet/api/ --exclude="*admin*"
```

### Test Admin Functionality:
```bash
# Run admin-specific tests (if available)
pytest tests/admin/ -v

# Test admin login
curl -X POST "http://localhost:8000/admin/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}'
```

## 🎯 Decision Tree

```
Need to modify a schema/model?
├── Is it used in non-admin files?
│   ├── YES → Create AdminPrefixed version
│   └── NO → Can modify carefully
├── Need new admin endpoint?
│   └── Add to admin.py or admin_prompts.py
├── Need new admin service method?
│   └── Extend existing service or create AdminService
└── Need database changes?
    └── Create admin-specific migration only
```

## 📞 When to Ask for Help

- Need to modify core user functionality
- Database schema changes affecting existing tables
- Cross-service dependencies
- Performance concerns
- Security-related changes

**Remember: When in doubt, create an Admin-prefixed version!**
