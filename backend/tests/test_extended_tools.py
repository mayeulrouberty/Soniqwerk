import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_set_session():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import set_session
        await set_session.ainvoke({"bpm": 174, "time_signature": "4/4", "name": "My Track"})
        mock_send.assert_called_once_with("set_session", {"bpm": 174, "time_signature": "4/4", "name": "My Track"})


@pytest.mark.asyncio
async def test_create_instrument_track():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"track_index": 0}
        from app.agent.tools import create_instrument_track
        await create_instrument_track.ainvoke({"name": "Bass", "instrument": "Drift", "color": "blue"})
        mock_send.assert_called_once_with("create_instrument_track", {"name": "Bass", "instrument": "Drift", "color": "blue"})


@pytest.mark.asyncio
async def test_create_audio_track():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"track_index": 1}
        from app.agent.tools import create_audio_track
        await create_audio_track.ainvoke({"name": "Vocals", "color": ""})
        mock_send.assert_called_once_with("create_audio_track", {"name": "Vocals", "color": ""})


@pytest.mark.asyncio
async def test_delete_track():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import delete_track
        await delete_track.ainvoke({"track_index": 2})
        mock_send.assert_called_once_with("delete_track", {"track_index": 2})


@pytest.mark.asyncio
async def test_set_track_mix():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import set_track_mix
        await set_track_mix.ainvoke({"track_index": 0, "volume": 0.8, "pan": 0.0, "mute": False})
        mock_send.assert_called_once_with("set_track_mix", {"track_index": 0, "volume": 0.8, "pan": 0.0, "mute": False})


@pytest.mark.asyncio
async def test_create_midi_clip():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import create_midi_clip
        await create_midi_clip.ainvoke({"track_index": 0, "slot_index": 0, "length_bars": 2})
        mock_send.assert_called_once_with("create_midi_clip", {"track_index": 0, "slot_index": 0, "length_bars": 2})


@pytest.mark.asyncio
async def test_write_notes():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import write_notes
        notes = [{"pitch": 60, "time": 0.0, "duration": 0.25, "velocity": 100}]
        await write_notes.ainvoke({"track_index": 0, "slot_index": 0, "notes": notes})
        mock_send.assert_called_once_with("write_notes", {"track_index": 0, "slot_index": 0, "notes": notes})


@pytest.mark.asyncio
async def test_set_clip_name():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import set_clip_name
        await set_clip_name.ainvoke({"track_index": 0, "slot_index": 0, "name": "Drop 1 Bass"})
        mock_send.assert_called_once_with("set_clip_name", {"track_index": 0, "slot_index": 0, "name": "Drop 1 Bass"})


@pytest.mark.asyncio
async def test_load_effect():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import load_effect
        await load_effect.ainvoke({"track_index": 0, "effect_name": "Reverb", "position": -1})
        mock_send.assert_called_once_with("load_effect", {"track_index": 0, "effect_name": "Reverb", "position": -1})


@pytest.mark.asyncio
async def test_create_scene():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"scene_index": 0}
        from app.agent.tools import create_scene
        await create_scene.ainvoke({"name": "Drop 1", "scene_index": -1})
        mock_send.assert_called_once_with("create_scene", {"name": "Drop 1", "scene_index": -1})


@pytest.mark.asyncio
async def test_write_automation():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import write_automation
        points = [{"time": 0.0, "value": 0.0}, {"time": 8.0, "value": 1.0}]
        await write_automation.ainvoke({"track_index": 0, "device_index": 0, "param_index": 1, "points": points})
        mock_send.assert_called_once_with("write_automation", {"track_index": 0, "device_index": 0, "param_index": 1, "points": points})


def test_all_tools_list_contains_new_tools():
    from app.agent.tools import ALL_TOOLS
    tool_names = [t.name for t in ALL_TOOLS]
    for expected in [
        "set_session", "create_instrument_track", "create_audio_track",
        "delete_track", "set_track_mix", "create_midi_clip", "write_notes",
        "set_clip_name", "load_effect", "create_scene", "write_automation",
    ]:
        assert expected in tool_names, f"Missing tool: {expected}"
    assert len(ALL_TOOLS) == 17
