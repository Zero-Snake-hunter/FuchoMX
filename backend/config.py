from pathlib import Path
from dotenv import load_dotenv
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# API-Football
API_FOOTBALL_KEY = os.environ.get('API_FOOTBALL_KEY')
API_FOOTBALL_BASE = 'https://v3.football.api-sports.io'
API_FOOTBALL_LIGA_MX_ID = 262
API_FOOTBALL_SEASON = 2025  # Temporada Clausura 2026 = season 2025

# JWT
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 días

ADMIN_EMAIL = "contacto@distrito.digital"

# Email (Resend)
RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://fucho.com.mx')
