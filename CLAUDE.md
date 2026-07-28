# 群聊自动打卡（deepseek-v4-pro_Group-chat-automatically-opens）

源: 社区插件

## 主人改过的关键文件

- `_manifest.json`：`dependencies` 加 `type = "python_package"` 字段（pydantic v2 discriminator 必需）。
- `plugin.py`：`on_config_update` 空回调体内补 `pass`（此前 IndentationError 导致整插件加载失败）。

## 配置要点

- `groups = []` —— 待主人 `/groupsign add_group` 实际配置打卡群。
- 之前**没有 .gitignore**；本仓库新建了完整 Python plugin 模板 + 主人段。

## 接入 & 依赖

- 无外部服务；纯本地调度。

## 关键日志

- `群聊自动打开插件已加载`（修语法后才看到这行）。

## 踩坑

- 早期补丁脚本：`legacy-0x-backup/from-server/fix_groupsign_syntax.py`。
- 空回调体必须 `pass`，否则 `IndentationError`。
- `dependencies` 必须有 `type` discriminator，否则 SDK 校验失败。

## 历史脚注

- 2026-07-28: 从服务器同步到本地仓库（baseline head=`19a1ad0`）；新建 `.gitignore` 与本 CLAUDE.md。
