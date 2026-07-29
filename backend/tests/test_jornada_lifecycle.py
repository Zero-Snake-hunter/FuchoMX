"""
Tests de regresión para el ciclo de vida de jornadas — cubren bugs reales
de la sesión del 26-27 de julio 2026:

1. Cerrar una jornada "upcoming" (con matches huérfanos marcados "finished"
   por error) NO debe aplicar penalizaciones — causa raíz de J3-J12
   penalizadas con ~360 registros de puntos inválidos (ver
   scoring_penalties.py y routers/admin_migrations.py::purge_invalid_penalties).
2. apply_jornada_close_adjustments debe rechazar cualquier jornada cuyo
   start_date todavía no llegue (el guard real que arregla el bug de arriba).
3. Solo puede haber una jornada con is_active=true por competition al
   mismo tiempo (routers/admin.py::activate_jornada la hace cumplir).
4. El auto-heal de /jornadas/current (routers/teams.py::get_current_jornada)
   debe preferir week_number más alto sobre created_at más reciente cuando
   hay más de una jornada is_active=true por error.

Usa mongomock-motor (mock async-compatible de Motor/PyMongo) en vez de
AsyncMock/MagicMock manual porque estas funciones hacen varias queries
encadenadas (find/insert/update/count sobre múltiples colecciones) — con
mongomock-motor corren contra un Mongo en memoria de verdad, en vez de
tener que precalcular a mano el resultado de cada llamada como en
tests/test_push_service.py (que sí usa el patrón patch+AsyncMock porque
sus funciones hacen 1-2 queries simples).
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from bson import ObjectId
from mongomock_motor import AsyncMongoMockClient


@pytest.fixture
def mongo_db():
    """DB en memoria fresca por test — evita estado compartido entre tests."""
    client = AsyncMongoMockClient()
    return client["test_jornada_lifecycle"]


# ============================================================
# 1 y 2: apply_jornada_close_adjustments — guards de start_date/status
# ============================================================
class TestApplyJornadaCloseAdjustmentsGuards:

    @pytest.mark.asyncio
    async def test_upcoming_jornada_no_penaliza_matches_huerfanos(self, mongo_db):
        """
        Reproduce el bug real: una jornada "upcoming" cuyo start_date todavía
        no llega, pero que tiene matches huérfanos de otra temporada marcados
        "finished" (retagueados por error, ver deep-clean-jornadas). Antes del
        fix, esto disparaba penalizaciones por "no seleccionar" — J3-J12
        quedaron con ~360 registros de puntos inválidos.
        """
        from scoring_penalties import apply_jornada_close_adjustments

        user_id = ObjectId()
        await mongo_db.users.insert_one({
            "_id": user_id, "email": "nuevo@test.com",
            "created_at": datetime.utcnow() - timedelta(days=1),
            "total_points": 0, "fantasy_total_points": 0,
        })

        jornada = {
            "_id": ObjectId(),
            "week_number": 5,
            "competition": "liga_mx",
            "status": "upcoming",
            "start_date": datetime.utcnow() + timedelta(days=3),  # todavía no llega
        }
        # Matches huérfanos ya marcados "finished" por error de datos.
        matches = [
            {"_id": ObjectId(), "status": "finished", "home_score": 1, "away_score": 0},
            {"_id": ObjectId(), "status": "finished", "home_score": 2, "away_score": 2},
        ]

        with patch("scoring_penalties.db", mongo_db):
            result = await apply_jornada_close_adjustments(jornada, matches)

        assert result["applied"] is False
        assert "start_date" in result["reason"]

        # La parte que importa: cero efectos secundarios en la DB.
        points_count = await mongo_db.points_log.count_documents({})
        assert points_count == 0, "No debe crear ningún points_log para una jornada que no ha empezado"

        user = await mongo_db.users.find_one({"_id": user_id})
        assert user["total_points"] == 0
        assert user["fantasy_total_points"] == 0

    @pytest.mark.asyncio
    async def test_rechaza_start_date_futuro(self, mongo_db):
        """El guard debe rechazar la jornada sin importar el status exacto,
        mientras start_date sea futuro o esté ausente."""
        from scoring_penalties import apply_jornada_close_adjustments

        matches = [{"_id": ObjectId(), "status": "finished"}]

        with patch("scoring_penalties.db", mongo_db):
            # start_date futuro
            jornada_futura = {
                "_id": ObjectId(), "week_number": 1, "competition": "liga_mx",
                "status": "in_progress", "start_date": datetime.utcnow() + timedelta(hours=1),
            }
            result_futura = await apply_jornada_close_adjustments(jornada_futura, matches)
            assert result_futura["applied"] is False

            # start_date ausente
            jornada_sin_fecha = {
                "_id": ObjectId(), "week_number": 2, "competition": "liga_mx",
                "status": "upcoming",
            }
            result_sin_fecha = await apply_jornada_close_adjustments(jornada_sin_fecha, matches)
            assert result_sin_fecha["applied"] is False

    @pytest.mark.asyncio
    async def test_acepta_start_date_pasado_sin_usuarios(self, mongo_db):
        """Con start_date ya pasado y todos los matches finished, sí debe
        aplicar (aunque no haya nada que penalizar porque no hay usuarios)."""
        from scoring_penalties import apply_jornada_close_adjustments

        jornada = {
            "_id": ObjectId(), "week_number": 5, "competition": "liga_mx",
            "status": "in_progress", "start_date": datetime.utcnow() - timedelta(days=2),
        }
        matches = [{"_id": ObjectId(), "status": "finished"}]

        with patch("scoring_penalties.db", mongo_db):
            result = await apply_jornada_close_adjustments(jornada, matches)

        assert result["applied"] is True
        assert result["quiniela_penalized"] == 0
        assert result["once_penalized"] == 0

    @pytest.mark.asyncio
    async def test_no_cierra_con_matches_pendientes(self, mongo_db):
        """Si algún match de la jornada no está 'finished', no debe evaluarse
        el cierre en absoluto (independiente del guard de start_date)."""
        from scoring_penalties import apply_jornada_close_adjustments

        jornada = {
            "_id": ObjectId(), "week_number": 5, "competition": "liga_mx",
            "status": "in_progress", "start_date": datetime.utcnow() - timedelta(days=2),
        }
        matches = [
            {"_id": ObjectId(), "status": "finished"},
            {"_id": ObjectId(), "status": "scheduled"},
        ]

        with patch("scoring_penalties.db", mongo_db):
            result = await apply_jornada_close_adjustments(jornada, matches)

        assert result["applied"] is False
        assert "pendientes" in result["reason"]


# ============================================================
# 3: Solo una jornada is_active=true por competition
# ============================================================
class TestSingleActiveJornadaPerCompetition:

    @pytest.mark.asyncio
    async def test_activate_jornada_desactiva_las_demas_de_la_misma_competition(self, mongo_db):
        from routers.admin import activate_jornada

        comp = "liga_mx"
        stray = await mongo_db.jornadas.insert_one({
            "week_number": 4, "competition": comp, "is_active": True, "status": "in_progress",
        })
        target = await mongo_db.jornadas.insert_one({
            "week_number": 5, "competition": comp, "is_active": False, "status": "upcoming",
        })
        # Jornada activa de OTRA competition — no debe tocarse.
        other_comp = await mongo_db.jornadas.insert_one({
            "week_number": 1, "competition": "world_cup_2026", "is_active": True, "status": "in_progress",
        })

        with patch("routers.admin.db", mongo_db):
            result = await activate_jornada(str(target.inserted_id), current_user={"email": "admin@fuchomx.com"})

        assert result["activated"]["id"] == str(target.inserted_id)

        active_liga_mx = await mongo_db.jornadas.count_documents({"competition": comp, "is_active": True})
        assert active_liga_mx == 1, "Debe quedar exactamente una jornada activa en liga_mx"

        stray_doc = await mongo_db.jornadas.find_one({"_id": stray.inserted_id})
        assert stray_doc["is_active"] is False

        target_doc = await mongo_db.jornadas.find_one({"_id": target.inserted_id})
        assert target_doc["is_active"] is True
        assert target_doc["status"] == "in_progress"

        # La de otra competition no debía verse afectada.
        other_doc = await mongo_db.jornadas.find_one({"_id": other_comp.inserted_id})
        assert other_doc["is_active"] is True


# ============================================================
# 4: Auto-heal de /jornadas/current prefiere week_number sobre created_at
# ============================================================
class TestJornadaCurrentAutoHeal:

    @pytest.mark.asyncio
    async def test_prefiere_week_number_mas_alto_sobre_created_at_reciente(self, mongo_db):
        """
        Reproduce el bug: datos legacy pueden dejar más de una jornada
        is_active=true para la misma competition. La jornada con created_at
        más reciente NO necesariamente es la real — puede ser un documento
        huérfano retagueado por una migración posterior. El criterio correcto
        es quedarse con week_number más alto.
        """
        from routers.teams import get_current_jornada

        now = datetime.utcnow()
        comp = "liga_mx"

        # Jornada "real" (la más avanzada), pero creada hace tiempo.
        real = await mongo_db.jornadas.insert_one({
            "week_number": 8, "competition": comp, "is_active": True,
            "status": "in_progress", "start_date": now - timedelta(days=2),
            "end_date": now + timedelta(days=5),  # futuro: no dispara auto-avance
            "created_at": now - timedelta(days=30),
            "processed": False,
        })
        # Jornada huérfana con created_at más reciente pero week_number menor
        # (ej. retagueada por una migración posterior — no debe ganar). Su
        # end_date se deja en el futuro a propósito: si estuviera en el
        # pasado, el Step 2 de get_current_jornada ("jornada expirada,
        # transita a la siguiente") la sacaría de en medio por una vía
        # totalmente distinta al dedupe de Step 1 que este test quiere
        # verificar, y el test pasaría igual aunque el sort estuviera roto
        # (falso positivo — así se descubrió corriendo un mutation check
        # manual: romper el sort a propósito no hacía fallar el test).
        orphan = await mongo_db.jornadas.insert_one({
            "week_number": 3, "competition": comp, "is_active": True,
            "status": "finished", "start_date": now - timedelta(days=60),
            "end_date": now + timedelta(days=1),
            "created_at": now - timedelta(hours=1),
            "processed": True,
        })

        with patch("routers.teams.db", mongo_db), patch("database.db", mongo_db):
            result = await get_current_jornada()

        assert result["jornada"] is not None
        assert result["jornada"]["week_number"] == 8, \
            "Debe quedarse con week_number más alto, no con created_at más reciente"

        # La huérfana debe quedar auto-corregida a is_active=False.
        orphan_doc = await mongo_db.jornadas.find_one({"_id": orphan.inserted_id})
        assert orphan_doc["is_active"] is False

        real_doc = await mongo_db.jornadas.find_one({"_id": real.inserted_id})
        assert real_doc["is_active"] is True
