"""
Liga MX Apertura 2026 — Equipos, Jornada 1 (resultados reales) y Jornada 2 (fixture real).
Para usar con el endpoint /api/admin/migrate-apertura-2026.

Los 17 equipos que ya jugaban en Clausura 2026 reutilizan su roster real de
real_liga_mx_data.LIGA_MX_TEAMS. Atlante es equipo nuevo en la liga (reemplaza a
Mazatlán en la lista de 18) y no hay roster real disponible en este repo — se
siembra con jugadores placeholder que deben reemplazarse después con datos reales.
"""

from datetime import datetime

from real_liga_mx_data import LIGA_MX_TEAMS

_REUSED_SHORT_NAMES = [
    "AME", "GDL", "CAZ", "TIG", "MTY", "PUM", "SAN", "TOL",
    "LEO", "ATL", "PAC", "TIJ", "NEC", "QRO", "PUE", "JUA", "ASL",
]

_BY_SHORT_NAME = {t["short_name"]: t for t in LIGA_MX_TEAMS}

APERTURA_2026_TEAMS = [_BY_SHORT_NAME[sn] for sn in _REUSED_SHORT_NAMES] + [
    {
        "name": "Atlante",
        "short_name": "ATE",
        "color": "#002B7F",
        # Placeholder — no hay shield real en el repo, reemplazar antes de mostrar en UI final.
        "shield_url": "https://via.placeholder.com/100/002B7F/FFFFFF?text=ATE",
        "players": [
            {"name": "Portero Atlante 1",        "number": 1,  "position": "POR"},
            {"name": "Portero Atlante 2",         "number": 13, "position": "POR"},
            {"name": "Defensa Atlante 1",         "number": 2,  "position": "DEF"},
            {"name": "Defensa Atlante 2",         "number": 3,  "position": "DEF"},
            {"name": "Defensa Atlante 3",         "number": 4,  "position": "DEF"},
            {"name": "Defensa Atlante 4",         "number": 5,  "position": "DEF"},
            {"name": "Mediocampista Atlante 1",   "number": 6,  "position": "MED"},
            {"name": "Mediocampista Atlante 2",   "number": 8,  "position": "MED"},
            {"name": "Mediocampista Atlante 3",   "number": 10, "position": "MED"},
            {"name": "Delantero Atlante 1",       "number": 9,  "position": "DEL"},
            {"name": "Delantero Atlante 2",       "number": 11, "position": "DEL"},
        ],
    },
]

# ──────────────────────────────────────────────
#  JORNADA 1 — Resultados reales (16-18 jul 2026)
#  (home_short, away_short, home_score, away_score, datetime_utc)
#
#  NOTA: dos partidos venían con datos incorrectos/incompletos en el pedido
#  original y se corrigieron tras verificar con fuentes (Infobae, TVAzteca,
#  ElUniversal, Mediotiempo — jul 2026):
#   - El partido de Puebla fue vs Juárez (Juárez 0-1 Puebla), NO vs Tigres.
#   - Tigres perdió 3-1 vs Tijuana (no hay partido "Tigres vs Puebla").
#  Único dato de fecha/hora confirmado por fuente: Tijuana-Tigres, jueves 16
#  jul (CT = UTC-6). El resto de horas de kickoff son PLACEHOLDER para
#  ordenar dentro del rango 16-18 jul dado — no están verificadas por fuente
#  y no afectan el cálculo de puntos (los partidos ya están "finished" con
#  el marcador correcto). Ajustar si se necesita precisión real de horario.
# ──────────────────────────────────────────────
APERTURA_2026_J1_RESULTS = [
    ("TIJ", "TIG", 3, 1, datetime(2026, 7, 17, 1, 0)),   # confirmado: jueves 16 jul 19:00 CT
    ("NEC", "ATE", 2, 1, datetime(2026, 7, 17, 23, 0)),  # placeholder: vie 17 jul
    ("ASL", "CAZ", 2, 1, datetime(2026, 7, 18, 1, 5)),   # placeholder: vie 17 jul
    ("PUM", "PAC", 0, 3, datetime(2026, 7, 18, 1, 5)),   # placeholder: vie 17 jul
    ("GDL", "TOL", 0, 2, datetime(2026, 7, 19, 0, 5)),   # placeholder: sáb 18 jul
    ("MTY", "SAN", 3, 2, datetime(2026, 7, 19, 1, 5)),   # placeholder: sáb 18 jul
    ("ATL", "LEO", 3, 2, datetime(2026, 7, 19, 2, 5)),   # placeholder: sáb 18 jul
    ("JUA", "PUE", 0, 1, datetime(2026, 7, 19, 23, 5)),  # placeholder: sáb 18 jul
    ("QRO", "AME", 0, 1, datetime(2026, 7, 20, 0, 5)),   # placeholder: sáb 18 jul
]

# ──────────────────────────────────────────────
#  JORNADA 2 — Fixture real (21-26 jul 2026)
#  (home_short, away_short, datetime_utc)
#
#  NOTA: el pedido original repetía "Tigres vs San Luis" en dos fechas
#  distintas (vie 24 y sáb 25) — se confirmó vía búsqueda (PorEsto,
#  Mediotiempo, jul 2026) que es un solo partido, viernes 24 jul 19:00 CT.
#  Faltan horarios exactos de Santos-Atlas, Necaxa-Monterrey y
#  Pachuca-Querétaro en el pedido original — se dejaron en horario genérico
#  de fin de semana (12:00 CT) y deben confirmarse/corregirse con
#  /admin/sync-fixtures o edición manual antes de que arranquen.
# ──────────────────────────────────────────────
APERTURA_2026_J2_FIXTURE = [
    ("CAZ", "PUE", datetime(2026, 7, 22,  1, 0)),   # Mar 21 19:00 CT
    ("TOL", "PUM", datetime(2026, 7, 22,  3, 0)),   # Mar 21 21:00 CT
    ("TIG", "ASL", datetime(2026, 7, 25,  1, 0)),   # Vie 24 19:00 CT
    ("TIJ", "LEO", datetime(2026, 7, 25,  3, 0)),   # Vie 24 21:00 CT
    ("ATE", "AME", datetime(2026, 7, 25,  3, 0)),   # Vie 24 21:00 CT
    ("GDL", "JUA", datetime(2026, 7, 25, 23, 7)),   # Sáb 25 17:07 CT
    ("SAN", "ATL", datetime(2026, 7, 26,  0, 0)),   # Sáb 25 — hora aprox., confirmar
    ("NEC", "MTY", datetime(2026, 7, 26, 18, 0)),   # Dom 26 — hora aprox., confirmar
    ("PAC", "QRO", datetime(2026, 7, 26, 18, 0)),   # Dom 26 — hora aprox., confirmar
]
