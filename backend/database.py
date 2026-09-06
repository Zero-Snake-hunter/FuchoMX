from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url, tls=True, tlsAllowInvalidCertificates=True)
db = client[os.environ.get('DB_NAME', 'quiniela_db')]


async def get_active_competition() -> str:
    """Retorna la competición activa (liga_mx | world_cup_2026)."""
    config = await db.config.find_one({"key": "active_competition"})
    return config["value"] if config else "liga_mx"
