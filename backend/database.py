from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os

from config import ADMIN_EMAIL

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url, tls=True, tlsAllowInvalidCertificates=True)
db = client[os.environ.get('DB_NAME', 'quiniela_db')]


async def get_active_competition() -> str:
    """Retorna la competición activa (liga_mx | world_cup_2026)."""
    config = await db.config.find_one({"key": "active_competition"})
    return config["value"] if config else "liga_mx"


async def get_admin_user_id():
    """
    _id del usuario admin (ADMIN_EMAIL), o None si no existe. Se usa para
    ocultarlo de rankings, listados de miembros y contadores visibles a
    otros usuarios — el admin sigue pudiendo jugar/crear ligas de prueba,
    solo no debe aparecer en pantallas públicas.
    """
    admin = await db.users.find_one({"email": ADMIN_EMAIL}, {"_id": 1})
    return admin["_id"] if admin else None
