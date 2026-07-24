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
        "shield_url": "https://a.espncdn.com/i/teamlogos/soccer/500/1927.png",
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
#  Reemplazan el roster placeholder/reusado-de-Clausura de los 18 equipos.
#  Fuente verificada en vivo (con confirmación de identidad de equipo antes
#  de extraer en TODOS los casos — varios IDs iniciales venían cruzados a
#  otro equipo o incluso a otro deporte/liga, ver historial de chat):
#   AME=227, GDL=219, CAZ=218, MTY=220, ATE=226, TOL=223, TIG=232, PUM=233,
#   SAN=225, ATL=216, LEO=228, PAC=234, TIJ=10125, NEC=229, QRO=222,
#   PUE=231, JUA=17851, ASL=15720
#  (todos en espn.com.mx/futbol/equipo/plantel/_/id/{id}/mex.{slug})
#  Cruce de verificación: varios jugadores (Isaías Violante-AME, Eugenio
#  Pizzuto/Walter Portales-ATE, Julián Carranza-NEC, Ramiro Árciga/Mourad
#  El Ghezouani-TIJ, Ignacio Maestro Puch-PUE) ya habían aparecido
#  anotando/con tarjeta en los partidos reales de J1 obtenidos de 365Scores.
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
        ("Rodolfo Cota", "POR", 30), ("Alejandro Cardenas", "DEL", 189), ("Ícaro", "MED", 27),
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
        ("Jordan Carrillo", "DEL", 33),
    ],
    "CAZ": [
        ("Andrés Gudiño", "POR", 1), ("Kevin Mier", "POR", 23), ("Emmanuel Ochoa", "POR", 30), ("Bruno Salgado", "POR", 40), ("Roberto Moreno", "POR", 41),
        ("Omar Campos", "DEF", 3), ("Willer Ditta", "DEF", 4), ("Jesús Orozco", "DEF", 5), ("Jorge Rodarte", "DEF", 22),
        ("Gonzalo Piovi", "DEF", 33), ("Josué Díaz", "DEF", 37), ("Diego Ramírez", "DEF", 39),
        ("Érik Lira", "MED", 6), ("Agustín Palavecino", "MED", 8), ("Andrés Montaño", "MED", 10), ("Jeremy Márquez", "MED", 16),
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
    "TOL": [
        ("David Shrem", "POR", 18), ("Luis García", "POR", 22), ("Hugo Gonzalez", "POR", 1),
        ("Brian García", "DEF", None), ("Diego Barbosa", "DEF", 2), ("Antonio Briseño", "DEF", 3), ("Bruno Méndez", "DEF", 4),
        ("Federico Pereira", "DEF", 6), ("Luan", "DEF", 13), ("Jesús Gallardo", "DEF", 20), ("Everardo López", "DEF", 25),
        ("Alek Álvarez", "DEF", 35), ("Luis Navarrete", "DEF", 192), ("Erick Orta", "DEF", 206),
        ("Érick Gutiérrez", "MED", None), ("Víctor Guzmán", "MED", None), ("Franco Romero", "MED", 5), ("Nicolás Castro", "MED", 8),
        ("Jesús Angulo", "MED", 10), ("Marcel Ruiz", "MED", 14), ("Pável Pérez", "MED", 15), ("Santiago Simón", "MED", 19),
        ("Fernando Arce", "MED", 24), ("Jorge Díaz", "MED", 29), ("Francisco Pumpido", "MED", 187), ("José Arroyo", "MED", 207),
        ("Jose Estrada", "MED", 250),
        ("Edgar López", "DEL", None), ("Alexis Vega", "DEL", 9), ("Helinho", "DEL", 11), ("Oswaldo Virgen", "DEL", 23),
        ("Paulinho", "DEL", 26), ("Franco Rossi", "DEL", 27), ("Giovani Bravo", "DEL", 189), ("Carlos Carrillo", "DEL", 191),
    ],
    "TIG": [
        ("Nahuel Guzmán", "POR", 1), ("Antonio Carrera", "POR", 13), ("Carlos Rodríguez", "POR", 25),
        ("Marco Farfan", "DEF", 3), ("Juanjo Purata", "DEF", 4), ("Jesús Garza", "DEF", 14), ("Alan Franco", "DEF", 15),
        ("Fernando Ordóñez", "DEF", 26), ("Jesús Angulo", "DEF", 27), ("Joaquim", "DEF", 28), ("Vladimir Loroña", "DEF", 32),
        ("Rafael Guerrero", "DEF", 33), ("Osvaldo Rodríguez", "DEF", 35), ("Marcelo Salinas Villarreal", "DEF", 193),
        ("César Araujo", "MED", 5), ("Juan Pablo Vigón", "MED", 6), ("Fernando Gorriarán", "MED", 8), ("Juan Brunetta", "MED", 11),
        ("Diego Lainez", "MED", 16), ("Marcelo Flores", "MED", 20), ("Rômulo", "MED", 23), ("Isac Galván", "MED", 198),
        ("Henrique Simeone Koifman", "MED", 204),
        ("Ángel Correa", "DEL", 7), ("André-Pierre Gignac", "DEL", 10), ("Rodrigo Aguirre", "DEL", 17), ("Diego Sánchez", "DEL", 30),
        ("Ozziel Herrera", "DEL", 77), ("Antonio De María Y Campos", "DEL", 205),
    ],
    "PUM": [
        ("Keylor Navas", "POR", 1), ("Miguel Paul", "POR", 32), ("Pablo Lara", "POR", 35),
        ("Pablo Bennevendo", "DEF", 2), ("Rubén Duarte", "DEF", 5), ("Nathan Silva", "DEF", 6), ("Cristian Calderón", "DEF", 12),
        ("Pablo Alfonso Monroy", "DEF", 13), ("Antonio Leone", "DEF", 24), ("Ángel Azuaje", "DEF", 34), ("Álvaro Angulo", "DEF", 77),
        ("Kleber Carranza", "DEF", None),
        ("Rodrigo López", "MED", 7), ("Adalberto Carrasquilla", "MED", 8), ("Ulises Rivas", "MED", 15), ("Sebastián Córdova", "MED", 17),
        ("Victor Arteaga", "MED", 18), ("Jesús Rivas", "MED", 19), ("Santiago Trigos", "MED", 20), ("Ángel Rico", "MED", 26),
        ("Pedro Vite", "MED", 45), ("Dennis Ramirez", "MED", 193), ("Stanley García", "MED", 203), ("Piero Quispe", "MED", None),
        ("Guillermo Martínez", "DEL", 9), ("José Macías", "DEL", 11), ("Uriel Antuna", "DEL", 21), ("Alan Medina", "DEL", 22),
        ("Juninho", "DEL", 23), ("Santiago López", "DEL", 30), ("Robert Morales", "DEL", 31),
    ],
    "SAN": [
        ("Carlos Acevedo", "POR", 1), ("Hector Holguin Perez", "POR", 33),
        ("Bruno Amione", "DEF", 2), ("Mauricio Cuevas", "DEF", 3), ("José Abella", "DEF", 4), ("Emmanuel Echeverría", "DEF", 17),
        ("Franco Pardo", "DEF", 18), ("Kevin Picón", "DEF", 22), ("Felipe Sanchez", "DEF", 25), ("Jonathan Pérez", "DEF", 28),
        ("Juan Echilvestre", "DEF", 185),
        ("Aldo López", "MED", 5), ("Javier Güemez", "MED", 6), ("Salvador Mariscal", "MED", 8), ("Ezequiel Bullaude", "MED", 10),
        ("Carlos Gruezo", "MED", 11), ("Efraín Orona", "MED", 14), ("Joshua Mancha", "MED", 15), ("Francisco Villalba", "MED", 21),
        ("Diego Medina", "MED", 24), ("Ramiro Sordo", "MED", 26), ("Kevin Palacios", "MED", 77),
        ("José Alfonso Ulloa Naranjo", "MED", 192), ("Luis Gómez", "MED", 193), ("Nelson Cedillo", "MED", 195),
        ("Diego González", "DEL", 7), ("Lucas Di Yorio", "DEL", 9), ("Eduardo Aguirre", "DEL", 19), ("Tahiel Jiménez", "DEL", 29),
        ("Lucca Vuoso", "DEL", 254),
    ],
    "ATL": [
        ("Camilo Vargas", "POR", 12), ("Antonio Sánchez", "POR", 22),
        ("Carlos Robles", "DEF", None), ("Milton Valenzuela", "DEF", None), ("Adrián Mora", "DEF", 4), ("Gaddi Aguirre", "DEF", 13),
        ("Paulo Ramírez", "DEF", 15), ("José Lozano", "DEF", 17), ("Rodrigo Schlegel", "DEF", 21), ("Jorge Rodríguez", "DEF", 25),
        ("Manuel Capasso", "DEF", 28), ("Róber", "DEF", 44), ("Luis Blanco", "DEF", 183), ("Jorge San Martín", "DEF", 218),
        ("Luís Esteves", "MED", None), ("Edgar Zaldivar", "MED", 6), ("Ryan Mmaee", "DEL", 8), ("Aldo Rocha", "MED", 26),
        ("Víctor Ríos", "MED", 27), ("Abraham Bass", "MED", 30), ("Jesús Serrato", "MED", 192), ("Jesús Guillén", "MED", 208),
        ("Duk", "DEL", None), ("Gustavo Ferrareis", "DEL", 3), ("Agustín Rodríguez", "DEL", 9), ("Gustavo Del Prete", "DEL", 10),
        ("Arturo González", "MED", 58), ("Sergio Hernandez", "DEL", 199), ("José Martín", "DEL", 203), ("Luis Gamboa", "DEL", 251),
    ],
    "LEO": [
        ("Alfonso Blanco", "POR", None), ("Rodolfo Cota", "POR", None), ("Jordan García", "POR", 1), ("Oscar García", "POR", 23),
        ("Juan Guevara", "DEF", None), ("Luís Cervantes", "DEF", None), ("Valentín Gauthier", "DEF", 2), ("Paolo Medina", "DEF", 3),
        ("Bryan Colula", "DEF", 4), ("Sebastián Vegas", "DEF", 5), ("Iván Moreno", "DEF", 7), ("Rodrigo Echeverría", "DEF", 20),
        ("Christopher Mora", "DEF", 185),
        ("Santiago Colombatto", "MED", None), ("Nicolás Fonseca", "MED", None), ("Edgar Guerra", "MED", None), ("Ángel Estrada", "MED", None),
        ("Fernando Beltrán", "MED", 6), ("Juan Domínguez", "MED", 8), ("Daniel Arcila", "MED", 13), ("Jordi Cortizo", "MED", 16),
        ("Salvador Reyes", "MED", 26), ("José David Ramírez", "MED", 28), ("José Rodríguez", "MED", 29), ("Luis Valadez", "MED", 183),
        ("Jesús Lara", "MED", 203),
        ("Federico Viñas", "DEL", None), ("Ismael Díaz", "DEL", 11), ("Gael García", "DEL", 17), ("Rogelio Funes Mori", "DEL", 18),
        ("José Alvarado", "DEL", 19), ("Sebastian Santos", "MED", 22), ("Diber Cambindo", "DEL", 27),
    ],
    "PAC": [
        ("Carlos Moreno", "POR", 1), ("Jose Eulogio Téllez", "POR", None),
        ("Sergio Barreto", "DEF", 2), ("Eduardo Bauermann", "DEF", 4), ("Mauricio Isais", "DEF", 6), ("Jorge Berlanga", "DEF", 13),
        ("Carlos Sánchez", "DEF", 14), ("Francisco Venegas", "DEF", 15), ("Nicolas Vallejo", "DEL", 21), ("Alan Mozo", "DEF", 22),
        ("Pedro Budib", "DEF", 32), ("Pedro Martínez", "DEF", 35), ("Ari Contreras", "DEF", 185), ("Edwin Soto", "DEF", 195),
        ("Juan Gamez", "DEF", 196), ("Andrés Micolta", "DEF", 222),
        ("Owen González", "MED", None), ("Rodolfo Pizarro", "MED", 7), ("Elías Montiel", "MED", 10), ("Israel Luna", "MED", 15),
        ("Christian Rivera", "MED", 16), ("Alan Bautista", "MED", 26), ("Kenedy", "MED", 29), ("Sergio Rodríguez", "MED", 30),
        ("Adrián Alcaraz", "DEL", None), ("Alexéi Domínguez", "DEL", 8), ("Oussama Idrissi", "DEL", 11), ("Illian Hernandez", "DEL", 19),
        ("Salomón Rondón", "DEL", 23), ("Jonatan Ramirez", "DEL", 139), ("Gael Álvarez", "DEL", 187), ("Daniel Méndez", "DEL", 199),
        ("Cristóbal Hernández", "DEL", 267),
    ],
    "TIJ": [
        ("Antonio Rodríguez", "POR", 2),
        ("Kevin Balanta", "DEF", None), ("Nicolás Diaz", "DEF", None), ("Rafael Fernández", "DEF", 3), ("Unai Bilbao", "DEF", 4),
        ("Kevin Escamilla", "DEF", 5), ("Jesús Gómez", "DEF", 6), ("Jackson Porozo", "DEF", 12), ("Jesus Vega", "DEF", 16),
        ("Oscar Manzanares", "DEF", 25), ("Pablo Nicolás Ortíz", "DEF", 33), ("Alejandro Magallon", "DEF", 188),
        ("Iván Tona", "MED", 8), ("Joe Corona", "MED", 15), ("Gilberto Mora", "MED", 19), ("Ángel Zapata", "MED", 20),
        ("Ignacio Rivero", "MED", 22), ("Aldahir Perez", "MED", 26), ("Domingo Blanco", "MED", 27), ("Frank Thierry Boya", "MED", 34),
        ("German Padilla", "MED", 187),
        ("Adonis Preciado", "DEL", 11), ("Ramiro Árciga", "DEL", 17), ("Mourad El Ghezouani", "DEL", 21), ("Josef Martínez", "DEL", 30),
        ("Yael Padilla", "DEL", 31), ("Christian Castillo", "DEL", 196), ("Joban González", "DEL", 202),
    ],
    "NEC": [
        ("Christopher Josué Andrade Martín", "POR", 1), ("Luis Jiménez", "POR", 12),
        ("Kaiky Naves", "DEF", None), ("Emilio Martínez", "DEF", 2), ("Agustín Oliveros", "DEF", 3), ("Alexis Peña", "DEF", 4),
        ("Diego Ochoa", "DEF", 15), ("Francisco Méndez", "DEF", 20), ("Raúl Martínez", "DEF", 33), ("Carlos Vargas", "DEF", 88),
        ("Daniel Leyva", "MED", 6), ("Lorenzo Faravelli", "MED", 8), ("Javier Ruiz", "MED", 10), ("Juan Torres", "MED", 11),
        ("Mauro Zaleta", "MED", 14), ("Pedro Pedraza", "MED", 16), ("Rogelio Cortéz", "MED", 17), ("Matías Espíndola", "MED", 21),
        ("Miguel Rodríguez", "MED", 99), ("Israel Tello", "MED", 188), ("Arath Moreno", "MED", 197), ("Joshua Palacios", "MED", 210),
        ("Ricardo Alonso", "MED", 232),
        ("Kevin Rosero", "DEL", 7), ("Julián Carranza", "DEL", 9), ("Misael Pedroza", "DEL", 27), ("Ricardo Monreal", "DEL", 30),
        ("Juan Valencia", "DEL", 90),
    ],
    "QRO": [
        ("José Hernández", "POR", 1), ("Luis Garcia", "POR", 24), ("Guillermo Allison", "POR", 25),
        ("Lucas Abascia", "DEF", 2), ("Diego Reyes", "DEF", 9), ("Bayron Duarte", "DEF", 22),
        ("Carlo García", "MED", 4), ("Santiago Homenchenko", "MED", 6), ("Bernardo Parra", "MED", 8), ("Lucas Rodríguez", "MED", 10),
        ("Paulo Victor", "DEF", 12), ("Jean Unjanque", "MED", 14), ("Erik Dueñas", "MED", 18), ("Alejandro Alcala", "MED", 20),
        ("Fernando González Peña", "MED", 21), ("Juan Eduardo Robles", "MED", 23), ("Juan Martínez", "MED", 30),
        ("Mateo Coronel", "MED", 37), ("Victor Lopez", "MED", 47), ("Michael Carcelen", "MED", 55), ("Darío Rodríguez", "MED", 188),
        ("Juan Pablo Cázares", "MED", 190),
        ("Eduardo Pérez", "DEL", 26), ("Ali Avila", "DEL", 31), ("Luis Gutiérrez", "DEL", 33), ("Claudio Robles", "DEL", 187),
        ("Daniel Parra", "DEF", 27), ("Enzo Giménez", "MED", 16), ("Waldo Madrid", "DEL", 29),
    ],
    "PUE": [
        ("Julio González", "POR", 1), ("Ricardo Gutiérrez", "POR", 28), ("Jesus Rodriguez", "POR", 33),
        ("Oscar Villa", "DEF", None), ("Ángel Leyva", "DEF", None), ("Juan Pablo Vargas", "DEF", 4), ("Facundo Almada", "DEF", 5),
        ("Fernando Monarrez", "DEF", 7), ("Eduardo Navarro", "DEF", 13), ("Jose Pachuca", "DEF", 20), ("Alvaro Burgos", "DEF", 195),
        ("Alberto Herrera", "MED", None), ("Mathías Tomás", "MED", None), ("Raúl Castillo", "MED", 10), ("Iker Moreno", "MED", 12),
        ("Alonso Ramirez", "MED", 16), ("Sergio Sanabria", "MED", 21), ("Alejandro Organista", "MED", 24), ("Lucas Camilo", "MED", 34),
        ("Ángel Robles", "DEL", None), ("Omar Moreno", "DEL", None), ("Luifer Hernández", "DEL", 9), ("Emiliano Gomez", "DEL", 11),
        ("Ignacio Maestro Puch", "DEL", 19), ("Kevin Velasco", "DEL", 26), ("Brayan Garnica", "DEL", 27), ("Eduardo Mustre", "DEL", 29),
        ("Carlos Baltazar", "MED", 22),
    ],
    "JUA": [
        ("Sebastián Jurado", "POR", 1), ("Benny Díaz", "POR", 24), ("Guillermo Ruiz", "POR", 27),
        ("Gilberto Sepúlveda", "DEF", None), ("Jesús Murillo", "DEF", 2), ("Alejandro Mayorga", "DEF", 4), ("Oscar Ortega", "DEF", 23),
        ("José García", "DEF", 26), ("Francisco Nevarez", "DEF", 33), ("Bryan Romero", "DEF", 184), ("Ricardo Juárez", "DEF", 198),
        ("Luis Carmona", "DEF", 203),
        ("Lucas Romero", "MED", None), ("Said Godínez", "MED", None), ("Juan Sigala", "MED", None), ("Denzell García", "MED", 5),
        ("Monchu", "MED", 6), ("Guilherme Castilho", "MED", 8), ("Dieter Villalpando", "MED", 10), ("José Luis Rodríguez", "MED", 11),
        ("Raymundo Fulgencio", "MED", 13), ("Homer Martínez", "MED", 18), ("Ricardinho", "MED", 21), ("Javier Aquino", "MED", 22),
        ("Leonardo Silva", "MED", 183), ("Kenneth Martínez", "MED", 186), ("Jan Carmona", "MED", 201), ("Eder López", "MED", 237),
        ("Madson", "DEL", 9), ("Luca Martinez", "DEL", 17), ("Óscar Estupiñán", "DEL", 19), ("Jairo Torres", "DEL", 20),
        ("Ettson Ayón", "DEL", 29), ("Israel Larios", "DEL", 208),
    ],
    "ASL": [
        ("Andrés Sánchez", "POR", 1), ("César López", "POR", 23), ("Gibrán Lajud", "POR", 34),
        ("Román Torres", "DEF", 2), ("Robson Bambu", "DEF", 3), ("Juanpe", "DEF", 6), ("Lucas Esteves", "DEF", 15),
        ("Aldo Cruz", "DEF", 18), ("Benjamín Galindo", "DEF", 30), ("Eduardo Águila", "DEF", 31), ("Luis Alberto Carrillo", "DEF", 188),
        ("Johan Caicedo", "MED", None), ("Roberto Meraz", "MED", 5), ("Benjamín Galdames", "MED", 7),
        ("Sébastien Salles-Lamonge", "MED", 10), ("David Rodriguez", "MED", 11), ("Miguel García", "MED", 14), ("Leonardo Flores", "MED", 20),
        ("Oscar Macías", "MED", 21), ("Rafael Llorente", "DEL", 22), ("Luis Nájera", "MED", 24), ("Sebastián Pérez Bouquet", "MED", 26),
        ("Jesús Medina", "MED", 28), ("Ángel Reyes", "MED", 242),
        ("João Pedro", "DEL", 9), ("Anderson Duarte", "DEL", 17), ("Santiago Muñoz", "DEL", 19), ("Ronaldo Najera", "DEL", 8),
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

# ──────────────────────────────────────────────
#  JORNADAS 3-17 — Fixture real (135 partidos, 9 por jornada), obtenido de
#  365Scores (competition_id=141) agrupando por el campo "roundNum" del
#  propio payload de cada partido (no por rango de fecha adivinado — evita
#  desfases si un partido se recorre a otra fecha dentro de la ventana de
#  la jornada). Verificado: 15 jornadas completas, sin partidos huérfanos,
#  todos los equipos mapean a un short_name conocido.
#  Formato: {week_number: [(game_id_365scores, home_short, away_short, datetime_utc), ...]}
# ──────────────────────────────────────────────
APERTURA_2026_J3_J17_FIXTURES = {
    3: [
        (4735745, "PUE", "GDL", datetime(2026, 8, 1, 1, 0)),
        (4735743, "JUA", "PUM", datetime(2026, 8, 1, 3, 0)),
        (4735744, "ASL", "TIJ", datetime(2026, 8, 1, 3, 0)),
        (4735742, "QRO", "TIG", datetime(2026, 8, 1, 23, 0)),
        (4735740, "ATL", "MTY", datetime(2026, 8, 2, 1, 0)),
        (4735741, "LEO", "PAC", datetime(2026, 8, 2, 1, 0)),
        (4735739, "CAZ", "ATE", datetime(2026, 8, 2, 3, 0)),
        (4735738, "AME", "SAN", datetime(2026, 8, 2, 23, 0)),
        (4735737, "TOL", "NEC", datetime(2026, 8, 3, 1, 0)),
    ],
    4: [
        (4735736, "ATE", "TOL", datetime(2026, 8, 15, 23, 0)),
        (4735735, "MTY", "JUA", datetime(2026, 8, 16, 1, 0)),
        (4735734, "ATL", "TIG", datetime(2026, 8, 16, 3, 0)),
        (4735733, "PUM", "QRO", datetime(2026, 8, 16, 18, 0)),
        (4735732, "AME", "ASL", datetime(2026, 8, 16, 23, 0)),
        (4735731, "SAN", "GDL", datetime(2026, 8, 17, 1, 0)),
        (4735730, "TIJ", "CAZ", datetime(2026, 8, 17, 3, 0)),
        (4735729, "NEC", "LEO", datetime(2026, 8, 18, 1, 0)),
        (4735728, "PAC", "PUE", datetime(2026, 8, 18, 3, 0)),
    ],
    5: [
        (4735722, "TIG", "ATE", datetime(2026, 8, 22, 1, 0)),
        (4735726, "JUA", "AME", datetime(2026, 8, 22, 3, 0)),
        (4735725, "QRO", "TOL", datetime(2026, 8, 22, 23, 0)),
        (4735724, "GDL", "TIJ", datetime(2026, 8, 22, 23, 7)),
        (4735723, "LEO", "MTY", datetime(2026, 8, 23, 1, 0)),
        (4735727, "PUE", "SAN", datetime(2026, 8, 23, 1, 0)),
        (4735721, "CAZ", "ATL", datetime(2026, 8, 23, 3, 0)),
        (4735720, "ASL", "PAC", datetime(2026, 8, 23, 23, 0)),
        (4735719, "PUM", "NEC", datetime(2026, 8, 24, 1, 0)),
    ],
    6: [
        (4735717, "ATE", "LEO", datetime(2026, 8, 29, 1, 0)),
        (4735718, "NEC", "CAZ", datetime(2026, 8, 29, 1, 0)),
        (4735716, "TIJ", "PUM", datetime(2026, 8, 29, 3, 0)),
        (4735714, "PAC", "GDL", datetime(2026, 8, 29, 23, 0)),
        (4735715, "ATL", "QRO", datetime(2026, 8, 29, 23, 0)),
        (4735713, "AME", "PUE", datetime(2026, 8, 30, 1, 0)),
        (4735712, "SAN", "TIG", datetime(2026, 8, 30, 3, 0)),
        (4735711, "TOL", "JUA", datetime(2026, 8, 31, 0, 0)),
        (4735710, "MTY", "ASL", datetime(2026, 8, 31, 2, 0)),
    ],
    7: [
        (4735709, "PUE", "TOL", datetime(2026, 9, 5, 1, 0)),
        (4735708, "JUA", "PAC", datetime(2026, 9, 5, 3, 0)),
        (4735706, "QRO", "MTY", datetime(2026, 9, 5, 23, 0)),
        (4735707, "ASL", "GDL", datetime(2026, 9, 5, 23, 0)),
        (4735703, "AME", "TIJ", datetime(2026, 9, 6, 1, 0)),
        (4735705, "TIG", "NEC", datetime(2026, 9, 6, 1, 0)),
        (4735704, "ATL", "ATE", datetime(2026, 9, 6, 3, 0)),
        (4735702, "PUM", "LEO", datetime(2026, 9, 6, 18, 0)),
        (4735701, "CAZ", "SAN", datetime(2026, 9, 7, 2, 0)),
    ],
    8: [
        (4735698, "NEC", "PUE", datetime(2026, 9, 12, 1, 0)),
        (4735696, "TIJ", "QRO", datetime(2026, 9, 12, 3, 0)),
        (4735697, "ATE", "PAC", datetime(2026, 9, 12, 3, 0)),
        (4735700, "TOL", "ATL", datetime(2026, 9, 12, 17, 0)),
        (4735695, "LEO", "ASL", datetime(2026, 9, 12, 23, 0)),
        (4735699, "CAZ", "AME", datetime(2026, 9, 13, 17, 0)),
        (4735693, "GDL", "PUM", datetime(2026, 9, 14, 0, 0)),
        (4735694, "SAN", "JUA", datetime(2026, 9, 14, 0, 0)),
        (4735692, "MTY", "TIG", datetime(2026, 9, 14, 2, 0)),
    ],
    9: [
        (4735691, "PUE", "ATE", datetime(2026, 9, 19, 1, 0)),
        (4735690, "JUA", "TIG", datetime(2026, 9, 19, 3, 0)),
        (4735688, "ASL", "NEC", datetime(2026, 9, 19, 23, 0)),
        (4735689, "ATL", "PUM", datetime(2026, 9, 19, 23, 0)),
        (4735687, "MTY", "CAZ", datetime(2026, 9, 20, 1, 0)),
        (4735685, "AME", "GDL", datetime(2026, 9, 20, 3, 0)),
        (4735684, "TOL", "SAN", datetime(2026, 9, 21, 0, 0)),
        (4735686, "PAC", "TIJ", datetime(2026, 9, 21, 0, 0)),
        (4735683, "QRO", "LEO", datetime(2026, 9, 21, 2, 0)),
    ],
    10: [
        (4735682, "ATE", "MTY", datetime(2026, 9, 26, 1, 0)),
        (4735681, "TIJ", "ATL", datetime(2026, 9, 26, 3, 0)),
        (4735680, "GDL", "QRO", datetime(2026, 9, 26, 23, 0)),
        (4735676, "TIG", "PUE", datetime(2026, 9, 27, 1, 0)),
        (4735679, "SAN", "PAC", datetime(2026, 9, 27, 1, 0)),
        (4735678, "CAZ", "TOL", datetime(2026, 9, 27, 3, 0)),
        (4735677, "PUM", "ASL", datetime(2026, 9, 27, 18, 0)),
        (4735675, "LEO", "JUA", datetime(2026, 9, 28, 1, 0)),
        (4735674, "NEC", "AME", datetime(2026, 9, 28, 3, 0)),
    ],
    11: [
        (4735671, "PUE", "LEO", datetime(2026, 10, 10, 1, 0)),
        (4735673, "QRO", "ATE", datetime(2026, 10, 10, 1, 0)),
        (4735672, "TIG", "TOL", datetime(2026, 10, 10, 3, 0)),
        (4735670, "JUA", "TIJ", datetime(2026, 10, 10, 23, 0)),
        (4735669, "ATL", "GDL", datetime(2026, 10, 11, 1, 0)),
        (4735668, "AME", "MTY", datetime(2026, 10, 11, 3, 0)),
        (4735666, "ASL", "SAN", datetime(2026, 10, 11, 23, 0)),
        (4735667, "PAC", "NEC", datetime(2026, 10, 11, 23, 0)),
        (4735665, "PUM", "CAZ", datetime(2026, 10, 12, 1, 0)),
    ],
    12: [
        (4735664, "NEC", "ATL", datetime(2026, 10, 17, 1, 0)),
        (4735662, "TIJ", "PUE", datetime(2026, 10, 17, 3, 0)),
        (4735663, "ATE", "PUM", datetime(2026, 10, 17, 3, 0)),
        (4735660, "SAN", "QRO", datetime(2026, 10, 17, 23, 0)),
        (4735661, "GDL", "TIG", datetime(2026, 10, 17, 23, 0)),
        (4735658, "TOL", "ASL", datetime(2026, 10, 18, 1, 0)),
        (4735659, "LEO", "AME", datetime(2026, 10, 18, 1, 0)),
        (4735657, "CAZ", "JUA", datetime(2026, 10, 18, 3, 0)),
        (4735656, "MTY", "PAC", datetime(2026, 10, 19, 1, 0)),
    ],
    13: [
        (4735654, "JUA", "ATE", datetime(2026, 10, 21, 1, 0)),
        (4735655, "ASL", "QRO", datetime(2026, 10, 21, 1, 0)),
        (4735651, "GDL", "NEC", datetime(2026, 10, 21, 3, 0)),
        (4735652, "TIG", "LEO", datetime(2026, 10, 21, 3, 0)),
        (4735649, "TOL", "TIJ", datetime(2026, 10, 22, 1, 0)),
        (4735650, "ATL", "AME", datetime(2026, 10, 22, 1, 0)),
        (4735653, "PUE", "MTY", datetime(2026, 10, 22, 1, 0)),
        (4735646, "SAN", "PUM", datetime(2026, 10, 22, 3, 0)),
        (4735648, "PAC", "CAZ", datetime(2026, 10, 22, 3, 0)),
    ],
    14: [
        (4735647, "NEC", "JUA", datetime(2026, 10, 24, 1, 0)),
        (4735645, "ATE", "ASL", datetime(2026, 10, 24, 3, 0)),
        (4735643, "LEO", "TOL", datetime(2026, 10, 24, 23, 0)),
        (4735644, "MTY", "GDL", datetime(2026, 10, 25, 0, 0)),
        (4735642, "PUM", "TIG", datetime(2026, 10, 25, 3, 0)),
        (4735640, "AME", "PAC", datetime(2026, 10, 25, 23, 0)),
        (4735641, "ATL", "PUE", datetime(2026, 10, 25, 23, 0)),
        (4735639, "QRO", "CAZ", datetime(2026, 10, 26, 1, 0)),
        (4735638, "TIJ", "SAN", datetime(2026, 10, 26, 3, 0)),
    ],
    15: [
        (4735636, "JUA", "QRO", datetime(2026, 10, 31, 1, 0)),
        (4735637, "ASL", "ATL", datetime(2026, 10, 31, 1, 0)),
        (4735634, "PUE", "PUM", datetime(2026, 10, 31, 3, 0)),
        (4735635, "PAC", "TIG", datetime(2026, 10, 31, 23, 0)),
        (4735632, "MTY", "TIJ", datetime(2026, 11, 1, 1, 0)),
        (4735633, "GDL", "ATE", datetime(2026, 11, 1, 1, 0)),
        (4735631, "AME", "TOL", datetime(2026, 11, 1, 3, 0)),
        (4735630, "SAN", "NEC", datetime(2026, 11, 1, 23, 0)),
        (4735629, "CAZ", "LEO", datetime(2026, 11, 2, 1, 0)),
    ],
    16: [
        (4735627, "NEC", "TIJ", datetime(2026, 11, 7, 1, 0)),
        (4735628, "ASL", "JUA", datetime(2026, 11, 7, 1, 0)),
        (4735626, "ATE", "SAN", datetime(2026, 11, 7, 3, 0)),
        (4735624, "TIG", "CAZ", datetime(2026, 11, 7, 23, 0)),
        (4735625, "ATL", "PAC", datetime(2026, 11, 7, 23, 0)),
        (4735623, "TOL", "MTY", datetime(2026, 11, 8, 1, 0)),
        (4735622, "PUM", "AME", datetime(2026, 11, 8, 3, 0)),
        (4735621, "QRO", "PUE", datetime(2026, 11, 9, 0, 0)),
        (4735618, "LEO", "GDL", datetime(2026, 11, 9, 1, 0)),
    ],
    17: [
        (4735620, "PUE", "ASL", datetime(2026, 11, 21, 1, 0)),
        (4735617, "TIJ", "ATE", datetime(2026, 11, 21, 3, 0)),
        (4735619, "JUA", "ATL", datetime(2026, 11, 21, 3, 0)),
        (4735613, "PAC", "TOL", datetime(2026, 11, 21, 23, 0)),
        (4735616, "SAN", "LEO", datetime(2026, 11, 21, 23, 0)),
        (4735612, "PUM", "MTY", datetime(2026, 11, 22, 1, 0)),
        (4735611, "TIG", "AME", datetime(2026, 11, 22, 3, 0)),
        (4735615, "GDL", "CAZ", datetime(2026, 11, 22, 23, 0)),
        (4735614, "QRO", "NEC", datetime(2026, 11, 23, 1, 0)),
    ],
}
