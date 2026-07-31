# 群聊自动打卡（deepseek-v4-pro_Group-chat-automatically-opens）

源: 社区插件

## 主人改过的关键文件

- `_manifest.json`：`dependencies` 加 `type = "python_package"` 字段（pydantic v2 discriminator 必需）。
- `plugin.py`：`on_config_update` 空回调体内补 `pass`（此前 IndentationError 导致整插件加载失败）。
- `plugin.py`（2026-08-01 review 修复）：
  - 打卡时间比较改为分钟数，避免 `9:00` 字典序漏触发。
  - `_calculate_sleep_time` 解析失败降级到 `check_interval`，不再刷死循环。
  - `_update_group_config` 改为 `.tmp` + `os.replace` 原子写。
- `tests/test_review_fixes.py`：上述三项的回归测试。

## 配置要点

- `groups = []` —— 待主人 `/groupsign add_group` 实际配置打卡群。
- `reminder_time` 建议写 `HH:MM`；实现已兼容无前导零，如 `9:00`。
- 之前**没有 .gitignore**；本仓库新建了完整 Python plugin 模板 + 主人段。

## 接入 & 依赖

- 无外部服务；纯本地调度。
- 本机回归：`python -m pytest tests/test_review_fixes.py -q`（不依赖 maibot_sdk 真包，测试内桩）。

## 关键日志

- `群聊自动打开插件已加载`（修语法后才看到这行）。
- 打卡触发：`到达打卡提醒时间 ... 开始执行打卡`。
- 无效时间：`打卡提醒时间格式无效: ...，降级使用检查间隔 ... 秒`。

## 踩坑

- 早期补丁脚本：`legacy-0x-backup/from-server/fix_groupsign_syntax.py`。
- 空回调体必须 `pass`，否则 `IndentationError`。
- `dependencies` 必须有 `type` discriminator，否则 SDK 校验失败。
- 字符串 `now_str >= reminder_time` 会在 `9:00` 对 `08:30` 之类场景误判；统一用分钟数比较。

## 历史脚注

- 2026-07-28: 从服务器同步到本地仓库（baseline head=`19a1ad0`）；新建 `.gitignore` 与本 CLAUDE.md。
- 2026-08-01: TDD 修 HIGH 时间比较 / 无效 reminder 降级 + MEDIUM 原子写；commit `fix(review): 修复打卡时间比较与配置原子写`。
