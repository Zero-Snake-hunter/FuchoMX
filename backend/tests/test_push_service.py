import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId


@pytest.mark.asyncio
async def test_send_batch_llama_expo_api():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("services.push_service.httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        from services.push_service import _send_batch
        await _send_batch(["ExponentPushToken[abc123]"], "Título", "Cuerpo")

        mock_client.post.assert_called_once()
        url = mock_client.post.call_args[0][0]
        kwargs = mock_client.post.call_args[1]
        assert url == "https://exp.host/--/api/v2/push/send"
        assert kwargs["json"][0]["to"] == "ExponentPushToken[abc123]"
        assert kwargs["json"][0]["title"] == "Título"


@pytest.mark.asyncio
async def test_notify_all_users_no_llama_api_sin_tokens():
    with patch("services.push_service.db") as mock_db:
        mock_db.users.find.return_value.to_list = AsyncMock(return_value=[])

        with patch("services.push_service._send_batch") as mock_send:
            from services.push_service import notify_all_users
            await notify_all_users("T", "B")
            mock_send.assert_not_called()


@pytest.mark.asyncio
async def test_notify_users_without_picks_excluye_enviados():
    jornada_id = ObjectId()
    user_sin_picks = ObjectId()
    user_con_picks = ObjectId()

    with patch("services.push_service.db") as mock_db:
        mock_db.quiniela_selections.distinct = AsyncMock(return_value=[user_con_picks])
        mock_db.users.find.return_value.to_list = AsyncMock(return_value=[
            {"_id": user_sin_picks, "push_tokens": ["ExponentPushToken[zzz]"]}
        ])

        with patch("services.push_service._send_batch") as mock_send:
            from services.push_service import notify_jornada_reminder
            await notify_jornada_reminder(jornada_id, week_number=5, reminder_hours=2)

            query = mock_db.users.find.call_args[0][0]
            assert user_con_picks in query["_id"]["$nin"]
            mock_send.assert_called_once()
            tokens_enviados = mock_send.call_args[0][0]
            assert "ExponentPushToken[zzz]" in tokens_enviados


@pytest.mark.asyncio
async def test_send_batch_en_lotes_de_100():
    tokens = [f"ExponentPushToken[t{i}]" for i in range(250)]
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("services.push_service.httpx.AsyncClient") as MockAsyncClient:
        MockAsyncClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockAsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)

        from services.push_service import notify_all_users
        with patch("services.push_service.db") as mock_db:
            mock_db.users.find.return_value.to_list = AsyncMock(return_value=[
                {"push_tokens": tokens}
            ])
            await notify_all_users("T", "B")

        # 250 tokens → 3 llamadas: 100 + 100 + 50
        assert mock_client.post.call_count == 3
