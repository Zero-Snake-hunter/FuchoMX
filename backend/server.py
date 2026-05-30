import logging

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from database import db
from scheduler import shutdown_app, start_scheduler

from routers import achievements as achievements_router
from routers import admin as admin_router
from routers import auth as auth_router
from routers import fantasy as fantasy_router
from routers import leagues as leagues_router
from routers import liguilla as liguilla_router
from routers import live as live_router
from routers import quiniela as quiniela_router
from routers import stats as stats_router
from routers import teams as teams_router

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Quiniela Liga MX API")

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router.router)
api_router.include_router(quiniela_router.router)
api_router.include_router(leagues_router.router)
api_router.include_router(fantasy_router.router)
api_router.include_router(teams_router.router)
api_router.include_router(live_router.router)
api_router.include_router(liguilla_router.router)
api_router.include_router(achievements_router.router)
api_router.include_router(stats_router.router)
api_router.include_router(admin_router.router)


@app.get("/")
async def health_check():
    return {"status": "ok", "app": "FuchoMX"}


@api_router.api_route("/ping", methods=["GET", "HEAD"])
async def ping():
    return {"status": "ok"}


@api_router.get("/health/db")
async def health_db():
    count = await db.users.count_documents({})
    return {"status": "ok", "users": count}


@api_router.get("/")
async def root():
    return {
        "message": "Quiniela Liga MX API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth/*",
            "teams": "/api/teams",
            "jornadas": "/api/jornadas/*",
            "quiniela": "/api/quiniela/*",
            "fantasy": "/api/fantasy/*",
            "players": "/api/players",
            "admin": "/api/admin/*"
        }
    }


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.on_event("startup")(start_scheduler)
app.on_event("shutdown")(shutdown_app)
