"""群聊自动打卡插件审查修复的回归测试。"""

from __future__ import annotations

import asyncio
import importlib.util
import logging
import sys
import types
from datetime import datetime as RealDateTime
from pathlib import Path
from types import SimpleNamespace

import pytest


# 本机没有 MaiBot SDK；测试只提供导入 plugin.py 所需的最小接口桩。
def _install_sdk_stub() -> None:
    if "maibot_sdk" in sys.modules:
        return

    sdk = types.ModuleType("maibot_sdk")

    class MaiBotPlugin:
        pass

    class PluginConfigBase:
        pass

    def Field(*, default=None, default_factory=None, **kwargs):
        del kwargs
        return default_factory() if default_factory is not None else default

    def Command(*args, **kwargs):
        del args, kwargs

        def decorator(function):
            return function

        return decorator

    sdk.Command = Command
    sdk.Field = Field
    sdk.MaiBotPlugin = MaiBotPlugin
    sdk.PluginConfigBase = PluginConfigBase
    sys.modules["maibot_sdk"] = sdk


_install_sdk_stub()

_PLUGIN_PATH = Path(__file__).resolve().parents[1] / "plugin.py"
_SPEC = importlib.util.spec_from_file_location("groupsign_plugin_under_test", _PLUGIN_PATH)
assert _SPEC is not None and _SPEC.loader is not None
plugin = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = plugin
_SPEC.loader.exec_module(plugin)


class FrozenDateTime(RealDateTime):
    """允许测试固定的当前时间。"""

    current = RealDateTime(2026, 1, 2, 8, 30)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.current
        return cls.current.replace(tzinfo=tz)


class FakeSignPlugin:
    def __init__(self, groups: list[str], reminder_time: str = "09:00"):
        self.config = SimpleNamespace(
            sign=SimpleNamespace(groups=groups, reminder_time=reminder_time)
        )
        self.calls: list[str] = []

    async def send_group_sign_request(self, group_id: str):
        self.calls.append(group_id)
        return True, "ok"


class FakeSender:
    def __init__(self):
        self.messages: list[tuple[str, str]] = []

    async def text(self, message: str, stream_id: str):
        self.messages.append((message, stream_id))


def _make_group_plugin(groups: list[str]):
    target = object.__new__(plugin.GroupSignPlugin)
    target.config = SimpleNamespace(sign=SimpleNamespace(groups=groups))
    target.ctx = SimpleNamespace(send=FakeSender())
    return target


async def _no_sleep(_seconds: float) -> None:
    return None


@pytest.mark.parametrize(
    ("reminder_time", "now", "should_trigger"),
    [
        ("9:00", "08:30", False),
        ("09:00", "08:30", False),
        ("08:30", "08:30", True),
    ],
)
def test_reminder_time_boundaries_are_compared_as_minutes(
    monkeypatch, reminder_time: str, now: str, should_trigger: bool
):
    FrozenDateTime.current = RealDateTime.strptime(now, "%H:%M").replace(
        year=2026, month=1, day=2
    )
    monkeypatch.setattr(plugin, "datetime", FrozenDateTime)
    monkeypatch.setattr(plugin.asyncio, "sleep", _no_sleep)

    fake_plugin = FakeSignPlugin(["123456"], reminder_time)
    manager = plugin.SignTaskManager(fake_plugin)
    asyncio.run(manager._check_and_execute_sign())

    assert bool(fake_plugin.calls) is should_trigger
    assert manager.last_checked is should_trigger


def test_unpadded_reminder_time_triggers_after_the_scheduled_hour(monkeypatch):
    FrozenDateTime.current = RealDateTime(2026, 1, 2, 10, 0)
    monkeypatch.setattr(plugin, "datetime", FrozenDateTime)
    monkeypatch.setattr(plugin.asyncio, "sleep", _no_sleep)

    fake_plugin = FakeSignPlugin(["123456"], "9:00")
    manager = plugin.SignTaskManager(fake_plugin)
    asyncio.run(manager._check_and_execute_sign())

    assert fake_plugin.calls == ["123456"]
    assert manager.last_checked is True


def test_invalid_reminder_time_falls_back_to_check_interval(caplog):
    manager = plugin.SignTaskManager(SimpleNamespace())
    check_interval = 37

    with caplog.at_level(logging.ERROR, logger="group_sign"):
        results = [
            manager._calculate_sleep_time(check_interval, "abc")
            for _ in range(3)
        ]

    assert results == [check_interval] * 3
    assert any("abc" in record.message for record in caplog.records)


def test_update_group_config_writes_via_atomic_replace(tmp_path, monkeypatch):
    config_path = tmp_path / "config.toml"
    config_path.write_text("[sign]\ngroups = []\n", encoding="utf-8")
    monkeypatch.setattr(plugin, "__file__", str(tmp_path / "plugin.py"))

    replacements: list[tuple[str, str]] = []
    real_replace = plugin.os.replace

    def recording_replace(source, destination):
        replacements.append((Path(source).name, Path(destination).name))
        return real_replace(source, destination)

    monkeypatch.setattr(plugin.os, "replace", recording_replace)
    target = _make_group_plugin([])

    asyncio.run(target._update_group_config("stream", "add", "123456"))

    assert replacements == [("config.toml.tmp", "config.toml")]
    assert not (tmp_path / "config.toml.tmp").exists()
    assert 'groups = ["123456"]' in config_path.read_text(encoding="utf-8")
    assert target.config.sign.groups == ["123456"]
