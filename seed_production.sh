#!/bin/bash
# Seed inicial de producción — FuchoMX
# Uso: ADMIN_PASSWORD=tu-password bash seed_production.sh

set -e

BASE_URL="https://fuchomx-production.up.railway.app/api"
ADMIN_EMAIL="contacto@distrito.digital"
ADMIN_PASSWORD="${ADMIN_PASSWORD:?Falta ADMIN_PASSWORD. Usa: ADMIN_PASSWORD=tu-pass bash seed_production.sh}"

echo "==> [1/5] Registrando usuario admin..."
REGISTER_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\",\"display_name\":\"Admin FuchoMX\"}")

REGISTER_STATUS=$(echo "$REGISTER_RESPONSE" | tail -1)
if [ "$REGISTER_STATUS" = "400" ]; then
  echo "     Admin ya existe, continuando con login..."
elif [ "$REGISTER_STATUS" != "200" ]; then
  echo "ERROR al registrar (HTTP $REGISTER_STATUS):"
  echo "$REGISTER_RESPONSE" | head -1
  exit 1
else
  echo "     Admin registrado OK"
fi

echo "==> [2/5] Login..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
if [ -z "$TOKEN" ]; then
  echo "ERROR: no se pudo obtener el token. Respuesta:"
  echo "$LOGIN_RESPONSE"
  exit 1
fi
echo "     Token obtenido OK"

echo "==> [3/5] Seed equipos..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/admin/seed-teams" \
  -H "Authorization: Bearer $TOKEN")
[ "$RESPONSE" = "200" ] && echo "     Equipos creados OK" || { echo "ERROR HTTP $RESPONSE"; exit 1; }

echo "==> [4/5] Seed temporada completa (17 jornadas)..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/admin/seed-season" \
  -H "Authorization: Bearer $TOKEN")
[ "$RESPONSE" = "200" ] && echo "     Temporada creada OK" || { echo "ERROR HTTP $RESPONSE"; exit 1; }

echo "==> [5/5] Seed jugadores..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/admin/seed-players" \
  -H "Authorization: Bearer $TOKEN")
[ "$RESPONSE" = "200" ] && echo "     Jugadores creados OK" || { echo "ERROR HTTP $RESPONSE"; exit 1; }

echo ""
echo "Seed completado. Verifica en:"
echo "  https://fuchomx-production.up.railway.app/api/jornadas/current"
