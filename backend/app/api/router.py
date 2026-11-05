from fastapi import APIRouter

from app.api.routes import account, admin, auth, dashboard, interviews, officer, resumes

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(resumes.router)
api_router.include_router(interviews.router)
api_router.include_router(dashboard.router)
api_router.include_router(officer.router)
api_router.include_router(admin.router)
api_router.include_router(account.router)
