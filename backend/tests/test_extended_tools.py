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


@pytest.mark.asyncio
async def test_search_samples_tool():
    with patch("app.agent.sample_library.get_library") as mock_lib:
        mock_lib.return_value.search.return_value = [
            {"name": "kick.wav", "path": "/samples/kick.wav"}
        ]
        from app.agent.tools import search_samples
        result = await search_samples.ainvoke({"query": "kick", "limit": 10})
        assert result["count"] == 1
        assert result["samples"][0]["name"] == "kick.wav"


@pytest.mark.asyncio
async def test_load_sample_tool():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        from app.agent.tools import load_sample
        await load_sample.ainvoke({"track_index": 0, "sample_path": "/samples/kick.wav"})
        mock_send.assert_called_once_with("load_sample", {
            "track_index": 0, "sample_path": "/samples/kick.wav"
        })


@pytest.mark.asyncio
async def test_get_device_parameters_tool():
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"params": [{"index": 0, "name": "Osc", "value": 0.5, "min": 0.0, "max": 1.0}]}
        from app.agent.tools import get_device_parameters
        result = await get_device_parameters.ainvoke({"track_index": 0, "device_index": 0})
        mock_send.assert_called_once_with("get_device_parameters", {"track_index": 0, "device_index": 0})
        assert "params" in result


@pytest.mark.asyncio
async def test_save_device_preset_tool():
    params = [{"index": 0, "name": "Osc", "value": 0.5, "min": 0.0, "max": 1.0}]
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = [
            {"params": params},
            {"devices": [{"name": "Drift", "index": 0}]},
        ]
        with patch("app.agent.preset_store.save_preset", return_value="/tmp/test.json"):
            from app.agent.tools import save_device_preset
            result = await save_device_preset.ainvoke({
                "name": "Test", "track_index": 0, "device_index": 0
            })
            assert result["success"] is True


@pytest.mark.asyncio
async def test_load_device_preset_tool():
    preset_data = {
        "name": "Test",
        "params": [{"index": 0, "name": "Osc", "value": 0.5, "min": 0.0, "max": 1.0}]
    }
    with patch("app.agent.tools._safe_send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}
        with patch("app.agent.preset_store.load_preset", return_value=preset_data):
            from app.agent.tools import load_device_preset
            result = await load_device_preset.ainvoke({
                "name": "Test", "track_index": 1, "device_index": 0
            })
            assert result["success"] is True
            assert result["params_restored"] == 1


@pytest.mark.asyncio
async def test_list_device_presets_tool():
    with patch("app.agent.preset_store.list_presets", return_value=[
        {"name": "Test", "device_name": "Drift", "created_at": "2026-03-12"}
    ]):
        from app.agent.tools import list_device_presets
        result = await list_device_presets.ainvoke({})
        assert result["count"] == 1
        assert result["presets"][0]["name"] == "Test"


def test_all_tools_list_contains_new_tools():
    from app.agent.tools import ALL_TOOLS
    tool_names = [t.name for t in ALL_TOOLS]
    for expected in [
        "set_session", "create_instrument_track", "create_audio_track",
        "delete_track", "set_track_mix", "create_midi_clip", "write_notes",
        "set_clip_name", "load_effect", "create_scene", "write_automation",
        "search_samples", "load_sample",
        "get_device_parameters", "save_device_preset", "load_device_preset", "list_device_presets",
    ]:
        assert expected in tool_names, f"Missing tool: {expected}"
    assert len(ALL_TOOLS) == 23
