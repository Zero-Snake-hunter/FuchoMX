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

APERTURA_2026_TEAMS = [dict(_BY_SHORT_NAME[sn]) for sn in _REUSED_SHORT_NAMES] + [
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
#  Rosters reales verificados en ESPN (espn.com.mx) — Apertura 2026.
#  Reemplazan el roster placeholder/reusado-de-Clausura de estos 5 equipos.
#  Fuente verificada en vivo (con confirmación de identidad de equipo antes
#  de extraer, porque los IDs iniciales de ESPN venían cruzados):
#   AME=id/227, GDL=id/219, CAZ=id/218, MTY=id/220, ATE=id/226
#  (todos en espn.com.mx/futbol/equipo/plantel/_/id/{id}/mex.{slug})
#  Cruce de verificación: varios de estos jugadores (Isaías Violante-AME,
#  Eugenio Pizzuto/Walter Portales-ATE) ya habían aparecido anotando/con
#  tarjeta en los partidos reales de J1 obtenidos de 365Scores.
# ──────────────────────────────────────────────
_ESPN_ROSTERS = {
    "AME": [
        ("Norberto Bedolla", "POR", None), ("Ángel Malagón", "POR", 1), ("Fernando Tapia", "POR", 21), ("César Lugo", "POR", 37),
        ("Emilio Lara", "DEF", None), ("Ralph Orquín", "DEF", None), ("Franco Rossano", "DEF", None), ("Israel Reyes", "DEF", 3),
        ("Sebastián Cáceres", "DEF", 4), ("Kevin Álvarez", "DEF", 5), ("Néstor Araujo", "DEF", 14), ("Aaron Mejía", "DEF", 18),
        ("Thiago Espinosa", "DEF", 22), ("Cristian Borja", "DEF", 26), ("Ramón Juárez", "DEF", 29), ("Miguel Vázquez", "DEF", 32),
        ("Miguel Ramírez", "MED", None), ("Dagoberto Espinoza", "MED", None), ("Osvaldo Arriaga", "MED", None),
        ("Alan Cervantes", "MED", 13), ("Rodrigo Dourado", "MED", 17), ("Alexis Gutiérrez", "MED", 20), ("Raphael Veiga", "MED", 23),
        ("Érick Sánchez", "MED", 28), ("Santiago Naveda", "MED", 35), ("Lima", "MED", 45),
        ("Esteban Lozano", "DEL", None), ("Diego Rocío", "DEL", None), ("Brian Rodríguez", "DEL", 7), ("Henry Martín", "DEL", 9),
        ("Alejandro Zendejas", "DEL", 10), ("Víctor Dávila", "DEL", 11), ("Isaías Violante", "DEL", 12), ("Patricio Salas", "DEL", 33),
    ],
    "GDL": [
        ("Raúl Rangel", "POR", 1), ("Óscar Whalley", "POR", 13), ("Eduardo García", "POR", 30), ("Juan Liceaga", "POR", 201),
        ("Luis Gabriel Rey", "DEF", None), ("Miguel Tapias", "DEF", 4), ("Bryan González", "DEF", 5), ("Brian Gutiérrez", "DEF", 11),
        ("Diego Campillo", "DEF", 19), ("José Castillo", "DEF", 21), ("Miguel Gómez", "DEF", 24), ("Leonardo Sepúlveda", "DEF", 27),
        ("Richard Ledezma", "DEF", 37), ("Ángel Chávez", "DEF", 56),
        ("Kevin Castañeda", "MED", None), ("Jordan Carillo", "MED", None), ("Omar Govea", "MED", 6), ("Luis Romo", "MED", 7),
        ("Daniel Aguirre", "MED", 23), ("Hugo Camberos", "MED", 26), ("Fernando González", "MED", 28), ("Diego Latorre", "MED", 198),
        ("Hugo Mata", "MED", 217), ("Cristian Inda", "MED", 225), ("Santiago Sandoval", "MED", 226),
        ("Fidel Barajas", "DEL", None), ("Alan Pulido", "DEL", 9), ("Efraín Álvarez", "DEL", 10), ("Ricardo Marín", "DEL", 17),
        ("Ángel Sepúlveda", "DEL", 20), ("Roberto Alvarado", "DEL", 25), ("Armando González", "DEL", 34), ("Sergio Aguayo", "DEL", 67),
    ],
    "CAZ": [
        ("Andrés Gudiño", "POR", 1), ("Kevin Mier", "POR", 23), ("Emmanuel Ochoa", "POR", 30), ("Bruno Salgado", "POR", 40), ("Roberto Moreno", "POR", 41),
        ("Omar Campos", "DEF", 3), ("Willer Ditta", "DEF", 4), ("Jesús Orozco", "DEF", 5), ("Jorge Rodarte", "DEF", 22),
        ("Gonzalo Piovi", "DEF", 33), ("Josué Díaz", "DEF", 37), ("Diego Ramírez", "DEF", 39),
        ("Érik Lira", "MED", 6), ("Agustín Palavecino", "MED", 8), ("Andrés Montaño", "MED", 10), ("Ángel Márquez", "MED", 16),
        ("Amaury García", "MED", 17), ("Carlos Rodríguez", "MED", 19), ("José Paradela", "MED", 20), ("Emmanuel Sánchez", "MED", 24),
        ("Diego Valdés", "MED", 28), ("Rodolfo Rotondi", "MED", 29), ("Cristian Jiménez", "MED", 32), ("Karol Velázquez", "MED", 35),
        ("Rogelio González", "MED", 36), ("Ariel Castro", "MED", 170), ("Amaury Morales", "MED", 194), ("Iván Silva", "MED", 197),
        ("Bryan Gamboa", "DEL", None), ("Íñigo Cuesta", "DEL", None), ("Nicolás Ibáñez", "DEL", 7), ("Osinachi Ebere", "DEL", 11),
        ("Luka Romero", "DEL", 18), ("Gabriel Fernández", "DEL", 21), ("Mateo Levy", "DEL", 34),
    ],
    "MTY": [
        ("Esteban Andrada", "POR", 1), ("Luis Cárdenas", "POR", 22), ("Santiago Mele", "POR", 25), ("César Ramos", "POR", 31),
        ("Ricardo Chávez", "DEF", 2), ("Gerardo Arteaga", "DEF", 3), ("Víctor Guzmán", "DEF", 4), ("Carlos Salcedo", "DEF", 13),
        ("Daniel Aceves", "DEF", 19), ("Luis Reyes", "DEF", 21), ("Stefan Medina", "DEF", 33), ("César Bustos", "DEF", 34),
        ("Javier Casillas Alavéz", "DEF", 36), ("Carlos Frayde", "DEF", 42),
        ("Orbelín Pineda", "MED", None), ("Fidel Ambríz", "MED", 5), ("Lucas Ocampos", "MED", 7), ("Óliver Torres", "MED", 8),
        ("Diego Rossi", "MED", 9), ("Iker Fimbres", "MED", 11), ("Érick Aguirre", "MED", 14), ("Jesús Corona", "MED", 17),
        ("César Garza", "MED", 18), ("Jorge Rodríguez", "MED", 30), ("Sebastián Rodríguez", "MED", 35), ("José Urías", "MED", 41),
        ("Cristian Reyes", "MED", 194), ("Omar Gálvez", "MED", 246), ("Allen Rojas", "MED", 251),
        ("Luca Orellano", "DEL", 10), ("Roberto de la Rosa", "DEL", 27), ("Uros Djurdjevic", "DEL", 32),
    ],
    "ATE": [
        ("David Ospina", "POR", None), ("Óscar Jiménez", "POR", None), ("Roberto Barragán", "POR", None),
        ("Francisco Reyes", "DEF", None), ("Walter Clar", "DEF", None), ("Eduardo Tercero", "DEF", None), ("Diogo Bagüí", "DEF", None),
        ("Cristóbal Alfaro", "DEF", None), ("Lucho Sánchez", "DEF", 3), ("Nicolás Carrera", "DEF", 6), ("Axl Padilla", "DEF", 23),
        ("Armando Escobar", "DEF", 27), ("Emiliano Espinoza", "DEF", 30),
        ("Jhojan Julio", "MED", None), ("Martín Fernández", "MED", None), ("Gilberto Adame", "MED", None), ("Octavio Vásquez", "MED", None),
        ("Hardy Meza", "MED", 5), ("Maximiliano García", "MED", 13), ("José González", "MED", 16), ("Leonardo Mejía", "MED", 17),
        ("Christian Bermúdez", "MED", 18), ("Javier Ibarra", "MED", 21), ("Luis Calzadilla", "MED", 22), ("Eugenio Pizzuto", "MED", 24),
        ("Edgar Jiménez", "MED", 34),
        ("Walter Portales", "DEL", None), ("Joaquín Moxica", "DEL", None), ("Luis Puente", "DEL", 9), ("Jairon Charcopa", "DEL", 15),
        ("Rubén Coubert", "DEL", 25),
    ],
}

for _team in APERTURA_2026_TEAMS:
    _sn = _team["short_name"]
    if _sn in _ESPN_ROSTERS:
        _team["players"] = [
            {"name": n, "position": pos, "number": num} for (n, pos, num) in _ESPN_ROSTERS[_sn]
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
#
#  ACTUALIZACIÓN: se reemplazaron todos los marcadores/horas por datos reales
#  obtenidos directamente de la API de 365Scores (competition_id=141,
#  gameId por partido — ver game_id abajo), que es la fuente de verdad. Esto
#  corrigió DOS resultados más que venían mal (de la búsqueda web anterior):
#   - Atlético San Luis 2-3 Cruz Azul (Cruz Azul GANÓ, no perdió 2-1 como se
#     tenía antes).
#   - León 2-3 Atlas (León fue LOCAL, no Atlas — el rival y marcador final
#     ya estaban bien, solo el local/visitante estaba invertido).
#  Formato: (game_id_365scores, home_short, away_short, home_score, away_score, datetime_utc)
# ──────────────────────────────────────────────
APERTURA_2026_J1_RESULTS = [
    (4735762, "TIJ", "TIG", 3, 1, datetime(2026, 7, 17,  3, 10)),
    (4735763, "NEC", "ATE", 2, 1, datetime(2026, 7, 17,  1,  0)),
    (4735761, "ASL", "CAZ", 2, 3, datetime(2026, 7, 18,  1,  0)),   # corregido: CAZ ganó
    (4735758, "PUM", "PAC", 0, 3, datetime(2026, 7, 18, 23,  0)),
    (4735757, "GDL", "TOL", 0, 2, datetime(2026, 7, 19,  1,  7)),
    (4735756, "MTY", "SAN", 3, 2, datetime(2026, 7, 19,  1,  5)),
    (4735760, "LEO", "ATL", 2, 3, datetime(2026, 7, 18,  1,  0)),   # corregido: LEO era local
    (4735759, "JUA", "PUE", 0, 1, datetime(2026, 7, 18,  3,  0)),
    (4735755, "QRO", "AME", 0, 1, datetime(2026, 7, 19,  3, 10)),
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

# ──────────────────────────────────────────────
#  JORNADAS 3-17 — Calendario (fechas dadas por Jorge, sin fixture aún)
#  Se crean como "upcoming", sin partidos. El fixture real de cada una se
#  carga cuando esa jornada se activa (mismo patrón que J1/J2).
#  (week_number, start_date_utc, end_date_utc, note)
# ──────────────────────────────────────────────
APERTURA_2026_REMAINING_JORNADAS = [
    (3,  datetime(2026, 7, 31), datetime(2026, 8, 3, 12, 0),  None),
    (4,  datetime(2026, 8, 15), datetime(2026, 8, 18, 12, 0), "post Leagues Cup"),
    (5,  datetime(2026, 8, 21), datetime(2026, 8, 24, 12, 0), None),
    (6,  datetime(2026, 8, 28), datetime(2026, 8, 31, 12, 0), None),
    (7,  datetime(2026, 9, 4),  datetime(2026, 9, 7, 12, 0),  None),
    (8,  datetime(2026, 9, 11), datetime(2026, 9, 14, 12, 0), None),
    (9,  datetime(2026, 9, 18), datetime(2026, 9, 21, 12, 0), None),
    (10, datetime(2026, 9, 25), datetime(2026, 9, 28, 12, 0), None),
    (11, datetime(2026, 10, 9), datetime(2026, 10, 12, 12, 0), None),
    (12, datetime(2026, 10, 16), datetime(2026, 10, 19, 12, 0), None),
    (13, datetime(2026, 10, 20), datetime(2026, 10, 22, 12, 0), "jornada doble"),
    (14, datetime(2026, 10, 23), datetime(2026, 10, 26, 12, 0), None),
    (15, datetime(2026, 10, 30), datetime(2026, 11, 2, 12, 0), None),
    (16, datetime(2026, 11, 6), datetime(2026, 11, 9, 12, 0), None),
    (17, datetime(2026, 11, 20), datetime(2026, 11, 23, 12, 0), None),
]
