"""
Datos reales de Liga MX — Jugadores, Equipos y Logos
Para usar con el endpoint /api/admin/seed-real-data
"""

LIGA_MX_TEAMS = [
    {
        "name": "Club América",
        "short_name": "AME",
        "color": "#FFD700",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/amy1xs1581857392.png",
        "players": [
            # Porteros
            {"name": "Memo Ochoa",         "number": 13, "position": "POR"},
            {"name": "Óscar Jiménez",      "number": 1,  "position": "POR"},
            # Defensas
            {"name": "Jorge Sánchez",      "number": 2,  "position": "DEF"},
            {"name": "Sebastián Cáceres",  "number": 3,  "position": "DEF"},
            {"name": "Emmanuel Aguilera",  "number": 4,  "position": "DEF"},
            {"name": "Jesús Orozco",       "number": 5,  "position": "DEF"},
            {"name": "Erick Aguirre",      "number": 21, "position": "DEF"},
            {"name": "Miguel Layún",       "number": 17, "position": "DEF"},
            # Medios
            {"name": "Álvaro Fidalgo",     "number": 6,  "position": "MED"},
            {"name": "Richard Sánchez",    "number": 20, "position": "MED"},
            {"name": "Diego Valdés",       "number": 10, "position": "MED"},
            {"name": "Alejandro Zendejas", "number": 7,  "position": "MED"},
            {"name": "Israel Reyes",       "number": 24, "position": "MED"},
            # Delanteros
            {"name": "Henry Martín",       "number": 14, "position": "DEL"},
            {"name": "Julián Quiñones",    "number": 23, "position": "DEL"},
            {"name": "Jonathan Rodríguez", "number": 9,  "position": "DEL"},
            {"name": "Kevin Álvarez",      "number": 22, "position": "DEL"},
            {"name": "Brian Rodríguez",    "number": 11, "position": "DEL"},
        ]
    },
    {
        "name": "Guadalajara",
        "short_name": "GDL",
        "color": "#CC0000",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/mp1box1593452087.png",
        "players": [
            {"name": "Raúl Gudiño",           "number": 1,  "position": "POR"},
            {"name": "Miguel Jiménez",         "number": 13, "position": "POR"},
            {"name": "Gilberto Sepúlveda",     "number": 4,  "position": "DEF"},
            {"name": "Cristian Calderón",      "number": 3,  "position": "DEF"},
            {"name": "Jesús Angulo",           "number": 2,  "position": "DEF"},
            {"name": "Alan Mozo",              "number": 22, "position": "DEF"},
            {"name": "Cade Cowell",            "number": 16, "position": "DEF"},
            {"name": "Fernando Beltrán",       "number": 7,  "position": "MED"},
            {"name": "Cipriano Arteaga",       "number": 8,  "position": "MED"},
            {"name": "Roberto Alvarado",       "number": 25, "position": "MED"},
            {"name": "Sergio Flores",          "number": 18, "position": "MED"},
            {"name": "Ricardo Marín",          "number": 17, "position": "MED"},
            {"name": "Javier Hernández",       "number": 14, "position": "DEL"},
            {"name": "Alexis Vega",            "number": 10, "position": "DEL"},
            {"name": "Ángel Zaldívar",         "number": 9,  "position": "DEL"},
            {"name": "Jesús Orozco Chiquete",  "number": 5,  "position": "DEL"},
            {"name": "Fernando González",      "number": 20, "position": "DEL"},
        ]
    },
    {
        "name": "Cruz Azul",
        "short_name": "CAZ",
        "color": "#0047AB",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/cf4ozx1655760184.png",
        "players": [
            {"name": "Sebastián Jurado",   "number": 1,  "position": "POR"},
            {"name": "José de Jesús Corona","number": 13, "position": "POR"},
            {"name": "Alexis Peña",        "number": 2,  "position": "DEF"},
            {"name": "Adrián Aldrete",     "number": 3,  "position": "DEF"},
            {"name": "Carlos Vargas",      "number": 4,  "position": "DEF"},
            {"name": "Juan Escobar",       "number": 22, "position": "DEF"},
            {"name": "Ignacio Rivero",     "number": 6,  "position": "DEF"},
            {"name": "Luis Romo",          "number": 8,  "position": "MED"},
            {"name": "Carlos Rodríguez",   "number": 16, "position": "MED"},
            {"name": "Rodrigo Huescas",    "number": 24, "position": "MED"},
            {"name": "Uriel Antuna",       "number": 11, "position": "MED"},
            {"name": "Erik Lira",          "number": 19, "position": "MED"},
            {"name": "Ángel Romero",       "number": 10, "position": "DEL"},
            {"name": "Gonzalo Carneiro",   "number": 7,  "position": "DEL"},
            {"name": "Christian Tabó",     "number": 17, "position": "DEL"},
            {"name": "Rotondi Sandoval",   "number": 23, "position": "DEL"},
            {"name": "Rafael Baca",        "number": 5,  "position": "DEL"},
        ]
    },
    {
        "name": "Tigres UANL",
        "short_name": "TIG",
        "color": "#FFD700",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/lh80fx1701423708.png",
        "players": [
            {"name": "Nahuel Guzmán",      "number": 1,  "position": "POR"},
            {"name": "Tiago Volpi",        "number": 25, "position": "POR"},
            {"name": "Luis Rodríguez",     "number": 23, "position": "DEF"},
            {"name": "Jesús Dueñas",       "number": 5,  "position": "DEF"},
            {"name": "Hugo Ayala",         "number": 3,  "position": "DEF"},
            {"name": "Nicolás Díaz",       "number": 4,  "position": "DEF"},
            {"name": "Jerónimo Rodríguez", "number": 2,  "position": "DEF"},
            {"name": "Guido Pizarro",      "number": 8,  "position": "MED"},
            {"name": "Javier Aquino",      "number": 11, "position": "MED"},
            {"name": "Florian Thauvin",    "number": 26, "position": "MED"},
            {"name": "Sebastián Córdova",  "number": 17, "position": "MED"},
            {"name": "Rafael Carioca",     "number": 6,  "position": "MED"},
            {"name": "André-Pierre Gignac","number": 10, "position": "DEL"},
            {"name": "Enner Valencia",     "number": 13, "position": "DEL"},
            {"name": "Diego Lainez",       "number": 18, "position": "DEL"},
            {"name": "Juan Pablo Vigón",   "number": 20, "position": "DEL"},
            {"name": "André Gomes",        "number": 7,  "position": "DEL"},
        ]
    },
    {
        "name": "Monterrey",
        "short_name": "MTY",
        "color": "#003087",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/yglj911721542561.png",
        "players": [
            {"name": "Esteban Andrada",    "number": 1,  "position": "POR"},
            {"name": "Luis Cárdenas",      "number": 13, "position": "POR"},
            {"name": "Stefan Medina",      "number": 2,  "position": "DEF"},
            {"name": "Héctor Moreno",      "number": 15, "position": "DEF"},
            {"name": "Gerardo Arteaga",    "number": 3,  "position": "DEF"},
            {"name": "Alfonso González",   "number": 4,  "position": "DEF"},
            {"name": "Nicolás Sánchez",    "number": 5,  "position": "DEF"},
            {"name": "Maximiliano Meza",   "number": 11, "position": "MED"},
            {"name": "Sergio Canales",     "number": 8,  "position": "MED"},
            {"name": "Jesús Gallardo",     "number": 23, "position": "MED"},
            {"name": "Luis Romo",          "number": 16, "position": "MED"},
            {"name": "Rodrigo Aguirre",    "number": 19, "position": "MED"},
            {"name": "Germán Berterame",   "number": 9,  "position": "DEL"},
            {"name": "Brandon Vázquez",    "number": 10, "position": "DEL"},
            {"name": "Rogelio Funes Mori", "number": 7,  "position": "DEL"},
            {"name": "Juan Pablo Vigón",   "number": 20, "position": "DEL"},
            {"name": "Oliver Meza",        "number": 22, "position": "DEL"},
        ]
    },
    {
        "name": "Pumas UNAM",
        "short_name": "PUM",
        "color": "#003D79",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/o01nvl1695734937.png",
        "players": [
            {"name": "Julio González",     "number": 1,  "position": "POR"},
            {"name": "Alfredo Talavera",   "number": 25, "position": "POR"},
            {"name": "Juan Dinenno",       "number": 9,  "position": "DEL"},
            {"name": "César Huerta",       "number": 11, "position": "DEL"},
            {"name": "Diogo de Oliveira",  "number": 7,  "position": "DEL"},
            {"name": "Eduardo Salvio",     "number": 10, "position": "MED"},
            {"name": "Gabriel Peñalba",    "number": 8,  "position": "MED"},
            {"name": "Higor Meritão",      "number": 6,  "position": "MED"},
            {"name": "Jorge Ruvalcaba",    "number": 17, "position": "MED"},
            {"name": "Eric Lira",          "number": 19, "position": "MED"},
            {"name": "Alan Mozo",          "number": 2,  "position": "DEF"},
            {"name": "Arturo Ortiz",       "number": 4,  "position": "DEF"},
            {"name": "Pablo Bennevendo",   "number": 5,  "position": "DEF"},
            {"name": "Efraín Velarde",     "number": 3,  "position": "DEF"},
            {"name": "Jorge Morán",        "number": 22, "position": "DEF"},
            {"name": "Mário Rondón",       "number": 18, "position": "DEL"},
        ]
    },
    {
        "name": "Santos Laguna",
        "short_name": "SAN",
        "color": "#00A551",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/nq32gy1557078230.png",
        "players": [
            {"name": "Carlos Acevedo",     "number": 1,  "position": "POR"},
            {"name": "Jonathan Orozco",    "number": 13, "position": "POR"},
            {"name": "Omar Campos",        "number": 2,  "position": "DEF"},
            {"name": "Félix Torres",       "number": 4,  "position": "DEF"},
            {"name": "Matheus Dória",      "number": 3,  "position": "DEF"},
            {"name": "Eduardo Coudet",     "number": 5,  "position": "DEF"},
            {"name": "Gerardo Arteaga",    "number": 21, "position": "DEF"},
            {"name": "Diego Valdés",       "number": 8,  "position": "MED"},
            {"name": "Carlos Izquierdoz",  "number": 6,  "position": "MED"},
            {"name": "Harold Preciado",    "number": 11, "position": "MED"},
            {"name": "Ronaldo Cisneros",   "number": 7,  "position": "MED"},
            {"name": "Eduardo Aguirre",    "number": 17, "position": "MED"},
            {"name": "Bryan Angulo",       "number": 9,  "position": "DEL"},
            {"name": "Jorge Sánchez",      "number": 10, "position": "DEL"},
            {"name": "Jonatan Cantillo",   "number": 20, "position": "DEL"},
            {"name": "Javier Correa",      "number": 14, "position": "DEL"},
        ]
    },
    {
        "name": "Toluca",
        "short_name": "TOL",
        "color": "#DC143C",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/y64wy91523913186.png",
        "players": [
            {"name": "Tiago Volpi",        "number": 1,  "position": "POR"},
            {"name": "Renato Paiva",       "number": 13, "position": "POR"},
            {"name": "Rodrigo Salinas",    "number": 2,  "position": "DEF"},
            {"name": "Jean Meneses",       "number": 10, "position": "MED"},
            {"name": "Paulinho",           "number": 9,  "position": "DEL"},
            {"name": "Rubens",             "number": 7,  "position": "DEL"},
            {"name": "Edgar Zaldívar",     "number": 11, "position": "DEL"},
            {"name": "Pablo Barrientos",   "number": 8,  "position": "MED"},
            {"name": "Alexis González",    "number": 6,  "position": "MED"},
            {"name": "Agustín Rogel",      "number": 4,  "position": "DEF"},
            {"name": "Raúl Gudiño",        "number": 25, "position": "POR"},
            {"name": "Carlos González",    "number": 5,  "position": "DEF"},
            {"name": "Álex Bernal",        "number": 3,  "position": "DEF"},
            {"name": "Anderson Santamaría","number": 22, "position": "DEF"},
            {"name": "Ariel Nahuelpán",    "number": 17, "position": "DEL"},
            {"name": "Rodrigo Fernández",  "number": 20, "position": "MED"},
        ]
    },
    {
        "name": "León",
        "short_name": "LEO",
        "color": "#00A551",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/pc9gro1752393439.png",
        "players": [
            {"name": "Rodolfo Cota",       "number": 1,  "position": "POR"},
            {"name": "Pedro Munhoz",       "number": 25, "position": "POR"},
            {"name": "William Tesillo",    "number": 3,  "position": "DEF"},
            {"name": "Stiven Barreiro",    "number": 4,  "position": "DEF"},
            {"name": "Luis Montes",        "number": 10, "position": "MED"},
            {"name": "Víctor Dávila",      "number": 11, "position": "DEL"},
            {"name": "Ángel Mena",         "number": 9,  "position": "DEL"},
            {"name": "Iván Moreno",        "number": 2,  "position": "DEF"},
            {"name": "Fernando Navarro",   "number": 5,  "position": "DEF"},
            {"name": "Jean Meneses",       "number": 7,  "position": "MED"},
            {"name": "Lucas Romero",       "number": 6,  "position": "MED"},
            {"name": "Osvaldo Rodríguez",  "number": 8,  "position": "MED"},
            {"name": "Yairo Moreno",       "number": 17, "position": "MED"},
            {"name": "Joel Campbell",      "number": 16, "position": "DEL"},
            {"name": "Santiago Colombatto","number": 20, "position": "MED"},
            {"name": "Gustavo Alcántara",  "number": 14, "position": "DEL"},
        ]
    },
    {
        "name": "Atlas",
        "short_name": "ATL",
        "color": "#8B0000",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/svvyvw1473541813.png",
        "players": [
            {"name": "Camilo Vargas",      "number": 1,  "position": "POR"},
            {"name": "Aldo Rocha",         "number": 6,  "position": "MED"},
            {"name": "Julián Quiñones",    "number": 11, "position": "DEL"},
            {"name": "Ídolo Anderson",     "number": 25, "position": "POR"},
            {"name": "Jesús Angulo",       "number": 2,  "position": "DEF"},
            {"name": "Diego Barbosa",      "number": 3,  "position": "DEF"},
            {"name": "Gaddi Aguirre",      "number": 4,  "position": "DEF"},
            {"name": "Ligardo Carreón",    "number": 5,  "position": "DEF"},
            {"name": "Frank Fabra",        "number": 22, "position": "DEF"},
            {"name": "Alejandro Irarragorri","number": 8,"position": "MED"},
            {"name": "Bryan Garnica",      "number": 17, "position": "MED"},
            {"name": "Anderson Santamaría","number": 10, "position": "MED"},
            {"name": "Jairo Torres",       "number": 7,  "position": "MED"},
            {"name": "Julio Furch",        "number": 9,  "position": "DEL"},
            {"name": "Mauro Manotas",      "number": 14, "position": "DEL"},
            {"name": "Rodrigo Navia",      "number": 20, "position": "DEL"},
        ]
    },
    {
        "name": "Pachuca",
        "short_name": "PAC",
        "color": "#0047AB",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/k9duyw1747334895.png",
        "players": [
            {"name": "Oscar Ustari",       "number": 1,  "position": "POR"},
            {"name": "Rodolfo Marín",      "number": 13, "position": "POR"},
            {"name": "Kevin Álvarez",      "number": 2,  "position": "DEF"},
            {"name": "Jesús Isijara",      "number": 3,  "position": "DEF"},
            {"name": "Christian Tabo",     "number": 4,  "position": "DEF"},
            {"name": "Gustavo Cabral",     "number": 5,  "position": "DEF"},
            {"name": "Víctor Guzmán",      "number": 8,  "position": "MED"},
            {"name": "Roberto De la Rosa", "number": 6,  "position": "MED"},
            {"name": "Óscar Murillo",      "number": 16, "position": "MED"},
            {"name": "Salomón Rondón",     "number": 9,  "position": "DEL"},
            {"name": "Nicolás Ibáñez",     "number": 11, "position": "DEL"},
            {"name": "Jhon Murillo",       "number": 7,  "position": "DEL"},
            {"name": "Romario Ibarra",     "number": 17, "position": "MED"},
            {"name": "Avilés Hurtado",     "number": 10, "position": "MED"},
            {"name": "Carlos González",    "number": 20, "position": "DEL"},
            {"name": "Diego Rolán",        "number": 14, "position": "DEL"},
        ]
    },
    {
        "name": "Tijuana",
        "short_name": "TIJ",
        "color": "#000000",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/uwxpwp1473541917.png",
        "players": [
            {"name": "Jonathan Orozco",    "number": 1,  "position": "POR"},
            {"name": "Ricardo Gutiérrez",  "number": 13, "position": "POR"},
            {"name": "Damián Torres",      "number": 2,  "position": "DEF"},
            {"name": "José García",        "number": 3,  "position": "DEF"},
            {"name": "Ariel Nahuelpán",    "number": 9,  "position": "DEL"},
            {"name": "Alexis Canelo",      "number": 11, "position": "DEL"},
            {"name": "Fidel Martínez",     "number": 7,  "position": "DEL"},
            {"name": "Jair Pedroza",       "number": 8,  "position": "MED"},
            {"name": "Óscar Ortega",       "number": 6,  "position": "MED"},
            {"name": "Ulises Rivas",       "number": 10, "position": "MED"},
            {"name": "Gabriel Achilier",   "number": 4,  "position": "DEF"},
            {"name": "Ángel Gómez",        "number": 5,  "position": "DEF"},
            {"name": "Néstor Araujo",      "number": 15, "position": "DEF"},
            {"name": "Fernando Hernández", "number": 16, "position": "MED"},
            {"name": "Christian López",    "number": 17, "position": "MED"},
            {"name": "José Guerrero",      "number": 14, "position": "DEL"},
        ]
    },
    {
        "name": "Necaxa",
        "short_name": "NEC",
        "color": "#DC143C",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/7jqidg1601923283.png",
        "players": [
            {"name": "Luis Malagon",       "number": 1,  "position": "POR"},
            {"name": "Hugo González",      "number": 13, "position": "POR"},
            {"name": "Luis Noriega",       "number": 2,  "position": "DEF"},
            {"name": "Óscar Murillo",      "number": 4,  "position": "DEF"},
            {"name": "Brayton Vázquez",    "number": 3,  "position": "DEF"},
            {"name": "Pablo Aguilar",      "number": 5,  "position": "DEF"},
            {"name": "Alexis Vega",        "number": 11, "position": "DEL"},
            {"name": "Brian Rubio",        "number": 9,  "position": "DEL"},
            {"name": "Luis Caicedo",       "number": 8,  "position": "MED"},
            {"name": "José Esquivel",      "number": 6,  "position": "MED"},
            {"name": "Gabriel Torres",     "number": 7,  "position": "MED"},
            {"name": "Rodrigo Nájera",     "number": 10, "position": "MED"},
            {"name": "Rodrigo Prieto",     "number": 17, "position": "MED"},
            {"name": "Marco Bueno",        "number": 14, "position": "DEL"},
            {"name": "Ángel Sepúlveda",    "number": 20, "position": "DEL"},
            {"name": "Isaac Brizuela",     "number": 22, "position": "DEL"},
        ]
    },
    {
        "name": "Querétaro",
        "short_name": "QRO",
        "color": "#003087",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/ev79tu1752393416.png",
        "players": [
            {"name": "Washington Aguerre", "number": 1,  "position": "POR"},
            {"name": "Tiago Cantoro",      "number": 13, "position": "POR"},
            {"name": "Alexis Pena",        "number": 2,  "position": "DEF"},
            {"name": "Matías Catalán",     "number": 4,  "position": "DEF"},
            {"name": "Yonathan Del Valle", "number": 11, "position": "DEL"},
            {"name": "José Rivero",        "number": 9,  "position": "DEL"},
            {"name": "Roberto Alvarado",   "number": 10, "position": "MED"},
            {"name": "Rodrigo López",      "number": 8,  "position": "MED"},
            {"name": "Pablo Barrera",      "number": 7,  "position": "MED"},
            {"name": "Aldo de Nigris",     "number": 5,  "position": "DEF"},
            {"name": "Marco Bueno",        "number": 3,  "position": "DEF"},
            {"name": "Duvier Riascos",     "number": 17, "position": "DEL"},
            {"name": "Fernando Gonzalez",  "number": 6,  "position": "MED"},
            {"name": "Carlos Gutierrez",   "number": 16, "position": "MED"},
            {"name": "Ángel Sepúlveda",    "number": 19, "position": "DEL"},
            {"name": "Diego del Valle",    "number": 20, "position": "DEL"},
        ]
    },
    {
        "name": "Mazatlán",
        "short_name": "MAZ",
        "color": "#663399",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/fgpobf1593446489.png",
        "players": [
            {"name": "Pablo Míguez",       "number": 1,  "position": "POR"},
            {"name": "Rafael García",      "number": 13, "position": "POR"},
            {"name": "Camilo Sanvezzo",    "number": 9,  "position": "DEL"},
            {"name": "Iván Rossi",         "number": 10, "position": "MED"},
            {"name": "Eduardo Herrera",    "number": 7,  "position": "DEL"},
            {"name": "Jorge Mere",         "number": 3,  "position": "DEF"},
            {"name": "Omar Campos",        "number": 2,  "position": "DEF"},
            {"name": "Javier Guemez",      "number": 4,  "position": "DEF"},
            {"name": "Sebastián Alves",    "number": 5,  "position": "DEF"},
            {"name": "Kevin Ramírez",      "number": 8,  "position": "MED"},
            {"name": "Carlos Cisneros",    "number": 6,  "position": "MED"},
            {"name": "Juan Martín Lucero", "number": 11, "position": "DEL"},
            {"name": "Ramiro González",    "number": 17, "position": "MED"},
            {"name": "Páblo Ramírez",      "number": 14, "position": "MED"},
            {"name": "Luis Ruiz",          "number": 18, "position": "DEL"},
            {"name": "Elías Hernández",    "number": 20, "position": "DEL"},
        ]
    },
    {
        "name": "Puebla",
        "short_name": "PUE",
        "color": "#003087",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/h0jgg51593451845.png",
        "players": [
            {"name": "Nicolás Vikonis",    "number": 1,  "position": "POR"},
            {"name": "Ángel Rodríguez",    "number": 13, "position": "POR"},
            {"name": "Maximiliano Araujo", "number": 2,  "position": "DEF"},
            {"name": "Gustavo Ferrareis",  "number": 11, "position": "DEL"},
            {"name": "Guillermo Martínez", "number": 9,  "position": "DEL"},
            {"name": "Jorge Hernández",    "number": 3,  "position": "DEF"},
            {"name": "Lucas Cavallini",    "number": 7,  "position": "DEL"},
            {"name": "Nicolás Freire",     "number": 4,  "position": "DEF"},
            {"name": "Maximiliano Perg",   "number": 5,  "position": "DEF"},
            {"name": "Martín Barragán",    "number": 8,  "position": "MED"},
            {"name": "Rodrigo Dourado",    "number": 6,  "position": "MED"},
            {"name": "Pablo Aguilar",      "number": 10, "position": "MED"},
            {"name": "Jordi Cortizo",      "number": 17, "position": "MED"},
            {"name": "Milton Caraglio",    "number": 14, "position": "DEL"},
            {"name": "Hernán Barcos",      "number": 18, "position": "DEL"},
            {"name": "Omar Fernández",     "number": 20, "position": "MED"},
        ]
    },
    {
        "name": "Juárez",
        "short_name": "JUA",
        "color": "#008000",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/b4oy071567446336.png",
        "players": [
            {"name": "Leonardo Morales",   "number": 1,  "position": "POR"},
            {"name": "Julio Furch",        "number": 9,  "position": "DEL"},
            {"name": "Kevin Castañeda",    "number": 11, "position": "DEL"},
            {"name": "Pablo Aguilar",      "number": 4,  "position": "DEF"},
            {"name": "Santiago Silva",     "number": 25, "position": "POR"},
            {"name": "Facundo Rodríguez",  "number": 3,  "position": "DEF"},
            {"name": "Marco Antonio Rojas","number": 2,  "position": "DEF"},
            {"name": "Luis Fuentes",       "number": 5,  "position": "DEF"},
            {"name": "Juan Palencia",      "number": 8,  "position": "MED"},
            {"name": "Óscar García",       "number": 6,  "position": "MED"},
            {"name": "Brayton Vázquez",    "number": 10, "position": "MED"},
            {"name": "Érik Aguirre",       "number": 7,  "position": "DEL"},
            {"name": "Christian Bermudez", "number": 17, "position": "MED"},
            {"name": "Ramiro González",    "number": 16, "position": "MED"},
            {"name": "Rodrigo Salinas",    "number": 14, "position": "DEL"},
            {"name": "Gabriel Peñalba",    "number": 20, "position": "DEL"},
        ]
    },
    {
        "name": "Atlético San Luis",
        "short_name": "ASL",
        "color": "#DC143C",
        "shield_url": "https://r2.thesportsdb.com/images/media/team/badge/9kgjme1593448412.png",
        "players": [
            {"name": "Alfonso Blanco",     "number": 1,  "position": "POR"},
            {"name": "Guillermo Allison",  "number": 13, "position": "POR"},
            {"name": "Martín Juárez",      "number": 2,  "position": "DEF"},
            {"name": "Ricardo Chávez",     "number": 3,  "position": "DEF"},
            {"name": "Esteban Espíndola",  "number": 9,  "position": "DEL"},
            {"name": "Facundo Waller",     "number": 11, "position": "DEL"},
            {"name": "John Medina",        "number": 4,  "position": "DEF"},
            {"name": "Rodrigo Noya",       "number": 5,  "position": "DEF"},
            {"name": "Andrés Iniesta",     "number": 8,  "position": "MED"},
            {"name": "Ángel Saldivar",     "number": 10, "position": "MED"},
            {"name": "José Abella",        "number": 7,  "position": "MED"},
            {"name": "Pablo Barrientos",   "number": 6,  "position": "MED"},
            {"name": "Alan Cervantes",     "number": 17, "position": "MED"},
            {"name": "Marcelo Díaz",       "number": 16, "position": "MED"},
            {"name": "Omar Govea",         "number": 14, "position": "DEL"},
            {"name": "Claudio Baeza",      "number": 20, "position": "DEL"},
        ]
    },
]

# ──────────────────────────────────────────────
#  CLAUSURA 2026 — Fechas reales de jornadas
# ──────────────────────────────────────────────
from datetime import datetime

CLAUSURA_2026_DATES = {
    1:  datetime(2026, 1, 10),   # Ene 10–12
    2:  datetime(2026, 1, 17),   # Ene 17–19
    3:  datetime(2026, 1, 24),   # Ene 24–26
    4:  datetime(2026, 1, 31),   # Ene 31 – Feb 2
    5:  datetime(2026, 2, 7),    # Feb 7–9
    6:  datetime(2026, 2, 14),   # Feb 14–16
    7:  datetime(2026, 2, 21),   # Feb 21–23
    8:  datetime(2026, 2, 28),   # Feb 28 – Mar 2
    9:  datetime(2026, 3, 7),    # Mar 7–9
    10: datetime(2026, 3, 14),   # Mar 14–16
    11: datetime(2026, 3, 21),   # Mar 21–23
    12: datetime(2026, 4, 4),    # Abr 4–6
    13: datetime(2026, 4, 18),   # Abr 18–20  ← JORNADA ACTUAL
    14: datetime(2026, 4, 25),   # Abr 25–27
    15: datetime(2026, 5, 2),    # May 2–4
    16: datetime(2026, 5, 8),    # May 8–10
    17: datetime(2026, 5, 15),   # May 15–17  ← Última jornada regular
}

# ──────────────────────────────────────────────
#  JORNADA 13 — Partidos reales Clausura 2026
#  (home_name, away_name, datetime_utc)
# ──────────────────────────────────────────────
CLAUSURA_2026_J13_MATCHES = [
    ("Atlético San Luis", "Pumas UNAM",  datetime(2026, 4, 18, 23,  5)),  # Sáb 18 abr 18:05 CT
    ("Mazatlán",          "Querétaro",   datetime(2026, 4, 19,  1,  5)),  # Sáb 18 abr 20:05 CT
    ("Necaxa",            "Tigres UANL", datetime(2026, 4, 19, 22,  5)),  # Dom 19 abr 17:05 CT
    ("Cruz Azul",         "Tijuana",     datetime(2026, 4, 20,  0,  5)),  # Dom 19 abr 19:05 CT
    ("Monterrey",         "Pachuca",     datetime(2026, 4, 20,  0, 10)),  # Dom 19 abr 19:10 CT
    ("Guadalajara",       "Puebla",      datetime(2026, 4, 20,  2,  5)),  # Dom 19 abr 21:05 CT
    ("León",              "Juárez",      datetime(2026, 4, 20,  2, 10)),  # Dom 19 abr 21:10 CT
    ("Club América",      "Toluca",      datetime(2026, 4, 20,  2, 15)),  # Dom 19 abr 21:15 CT
    ("Santos Laguna",     "Atlas",       datetime(2026, 4, 20, 22,  5)),  # Lun 20 abr 17:05 CT
]

# ──────────────────────────────────────────────
#  LIGUILLA CLAUSURA 2026 — Tabla provisional
#  (al 15 de abril 2026, antes de J13)
# ──────────────────────────────────────────────
LIGUILLA_CLAUSURA_2026_TEAMS = [
    {"position": 1, "name": "Pumas UNAM"},
    {"position": 2, "name": "Guadalajara"},
    {"position": 3, "name": "Cruz Azul"},
    {"position": 4, "name": "Pachuca"},
    {"position": 5, "name": "Toluca"},
    {"position": 6, "name": "Atlas"},
    {"position": 7, "name": "Tigres UANL"},
    {"position": 8, "name": "Club América"},
]
