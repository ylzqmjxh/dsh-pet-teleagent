# TeleAgent 桌面大肥鱼 · 原版 dsh-pet-indesktop 移植说明

> 从 GitHub 项目 `MerZlin/dsh-pet-indesktop` 原样移植，运行于 TeleAgent 自带环境（Python 3.12 + PySide6）。**忠实还原原版蓝色大肥鱼**，功能全量（动画、三大识屏、AI 对话、歌词、Agent 联动）。

---

## 一、这是什么

一个用 **Python + PySide6** 写成的独立桌面宠物。透明无边框、置顶、可拖动、多角色、106 段 WebM 高清动画、系统托盘，并可选接入 AI。

- **形象**：原版蓝色大肥鱼（未改动素材，`assets/big_blue_fat_fish/`）
- **入口**：`python -m pet`（项目根目录执行）

## 二、快速启动

双击项目根目录的 **`启动桌宠.bat`** 即可。桌宠出现在屏幕右下角，系统托盘出现常驻图标（右键可开菜单）。

手动方式：
```
cd dsh-pet-indesktop
python -m pet
```

> 依赖已在本机安装（PySide6 / onnxruntime / rapidocr / winrt / edge-tts 等）。若换机器，先 `pip install -r requirements.txt`。

## 三、功能速览

| 功能 | 怎么用 | 备注 |
|---|---|---|
| 动画/待机/随机走动 | 自动 | 点击 Q 弹、拖拽甩抛、边缘探头、黄金回旋、孵小肥鱼、拖文件喂食等 |
| 主动识屏（关怀） | 右键 →「主动识屏」开启 + 白名单 | 默认关闭，白名单 + 多重防抖，隐私友好 |
| 看看屏幕（截图问 AI） | 右键 →「看看屏幕」 | 需配置视觉模型 |
| 框选识屏（OCR/翻译/问答） | 右键 →「截图 → 框选识屏」 | 本地 OCR 离线可用，翻译/问答走 AI |
| AI 对话（Chat） | 双击桌宠唤起 / 设置 → AI 与对话 | 需配置模型服务与 API Key |
| 音乐歌词 | 设置 → 歌词显示 | 走 Windows 媒体控制（SMTC） |
| 语音报时/待办提醒 | 设置 → 互动 | 可选 edge-tts 在线语音 |
| **Agent 联动** | 设置 → 联动 → 开启 | 让桌宠感知 AI 的工作状态（见下） |

## 四、TeleAgent 联动（重点）

桌宠内置**本地文件事件总线**：任何 Agent 只要往
`%APPDATA%\dsh-pet-standalone\agent-events\<agent>.jsonl`
追加一行 JSON 事件，桌宠就会按「六态词汇」切换动画、冒泡。

**第一步：开启联动（✅ 已完成）** —— teleagent 已由 TeleAgent 直接写入桌宠全局配置（`%APPDATA%\dsh-pet-standalone\config.json`：`agent_link.teleagent=true` + `custom_agents` 条目），桌宠已重启生效，日志确认「Agent 监视器 [teleagent] 已启动」，事件即发即被消费。换机器重装桌宠时需重新注册（停桌宠→改 config.json→启动），或在「设置 → 联动」确认 TeleAgent 开关已开。

**第二步：手动发事件（可选，特殊场景）** —— 用附带的桥接脚本（注意：常态已被第三步自动监视器覆盖，手动仅用于 attention/error 等主动提示）：

```
# 进入项目目录
python teleagent_bridge.py working --tool bash   # 执行中
python teleagent_bridge.py thinking                # 思考中
python teleagent_bridge.py idle                    # 干完活啦（空闲）
python teleagent_bridge.py error                   # 出错
python teleagent_bridge.py attention               # 需要你看一眼
python teleagent_bridge.py --event PreToolUse      # 也支持事件名
```

桌宠侧反应：`thinking/working` 轮换工作动画；`attention/error` 重要气泡提醒；`idle` 恢复待机并可能弹「干完活啦」。

**第三步（推荐）：自动联动监视器** —— 第一步完成后，常态下无需任何手动操作：
- 「桌宠管家·大肥鱼联动」技能自带 `scripts/teleagent_watcher.py`（pythonw 后台守护），轮询 TeleAgent 会话数据库自动检测任务状态（running 工具→working、思考→thinking、回复落成 25s/静默 90s→idle）并写事件，灵动岛随之实时变色变字
- 单实例锁；日志在 `%APPDATA%\dsh-pet-standalone\teleagent-watcher.log`
- 重启电脑后需重新拉起（或经用户确认配置开机自启）

## 五、建议的 TeleAgent 用法

TeleAgent 在任务开始/工具调用时自动写事件即可让桌宠"看着你干活"。示例（在桥接脚本同目录）：

```
python teleagent_bridge.py working --tool online_search
```

## 六、常见问题

- **桌宠不见了？** 看系统托盘（可能收在"显示隐藏图标"里），双击托盘图标可显隐。
- **自启**：托盘右键 →「开机自启」。
- **多实例**：桌宠为单实例（overlay gate），重复启动会提示已在运行。
- **数据目录**：`%APPDATA%\dsh-pet-standalone\`（配置、日志、agent-events）。

---

## 七、本地补丁记录（升级原项目时需重打）

**补丁 P1：自定义联动 Agent → 灵动岛状态点同步**（20261023T180242Z 打入）

- 目的：让自定义 Agent（teleagent）的六态事件驱动灵动岛状态灯（原版仅 DSH 收敛态驱动岛）
- 改动 1 `pet/agent_link/__init__.py`：
  - `AgentLinkManager` 新增信号 `custom_island_state = Signal(str, str)`（八态词汇）
  - `__init__` 末尾新增 `self._custom_island_prev: dict[str, str] = {}`（边沿记录）
  - `_on_agent_state_event` 增补丁分支：非内置 Agent 时调 `_emit_custom_island_state`
  - 新增 `_CUSTOM_ISLAND_MAP`（thinking→thinking / working→working / attention→waiting_approval / error→error / sleeping→idle / idle→idle）与 `_emit_custom_island_state`（busy→idle 边沿译 `success`，岛自动亮 4s 完成绿点后回落空闲）
- 改动 2 `pet/app.py`：
  - AppShell 订阅 `shared_link.custom_island_state.connect(self._on_custom_island_state)`
  - 新增 `_on_custom_island_state`：与 DSH 共用 `island.set_dsh_state` 入口
- 验证：working→岛蓝色工作点；idle→岛绿色完成点（4s 回落）；已实测截图核验
- 注意：升级 dsh-pet-indesktop 后需按本节重打；改动均有「TeleAgent 本地补丁」注释标记，可搜索定位

**组件 C1：岛状态文字段 teleagent_state**（20261023T181xxxZ 安装，零源码改动）

- 位置：`%APPDATA%\dsh-pet-standalone\island-extensions\teleagent-state\`（`island-component.json` 声明 + `provider.py` 实现，走原项目官方"第三方岛组件"机制）
- 效果：灵动岛胶囊在状态灯旁同步显示状态文字（与状态点双通道）：`运行中 / 思考中 / 待确认 / 出错 / 刚完成(4s) / 待命`
- 取值：provider 读 `agent-events/teleagent.jsonl` 尾行状态（1Hz 采样节拍，最多 1 秒延迟）；busy→idle 边沿后 4 秒内显示「刚完成」，与完成绿点同步回落
- 配置：`config.json` 的 `island_metrics` 含 `"teleagent_state"`；盒宽按样本「待确认」定死（遵守岛宽度白名单纪律）
- 注意：岛若被拖拽停靠到屏幕边缘（dock 细条态）则只显示状态点、不显示段文字——把岛拖回中央区域即恢复胶囊态

**补丁 P2：更新页「本地变更记录 + 项目来源」**（20261023T181832Z 打入）

- 目的：在设置界面「更新」页展示每次本地更新的版本号与内容，并把原作者/上游信息列为来源项
- 改动 1 `pet/update_settings.py`：
  - 新增「TeleAgent 本地变更记录」卡片（更新页内、新版本说明卡之下）：渲染 `项目根/teleagent-changes.json`（版本号 · 日期 · 标题 + 内容说明，文件缺失时如实提示）
  - 挂载新分区 `build_source_section`
- 改动 2 `pet/settings_about.py`：
  - 新增 `PROJECT_SOURCES` 与 `build_source_section`（「项目来源」分区：开源仓库 github.com/MerZlin/dsh-pet-indesktop / 上游 PC2005-cloud/dsh-pet / 技术栈 Python 3 + PySide6 / 本地维护 TeleAgent），行内可点击直达链接
  - `_account_row` 增加可选 `url` 参数（向后兼容，不影响原作者账号行）
- 数据维护：**以后每次本地更新只需在 `teleagent-changes.json` 的 `changes` 数组追加一条**（version/date/title/detail），无需再动源码；设置页（独立进程）每次打开自动加载最新代码与数据
- 注意：设置页是独立进程（`python -m pet --settings`），桌宠主进程无需重启

---

## 交付目录

`dsh-pet-indesktop/`
- `启动桌宠.bat` —— 一键启动
- `teleagent_bridge.py` —— TeleAgent 事件桥接器
- `pet/` —— 桌宠主体（PySide6，含本地补丁 P1/P2）
- `assets/`、`resources/` —— 动画与 OCR 模型

---

## 八、本地大模型（零 API Key 方案）

桌宠的 AI 对话（双击桌宠）与识屏（看看屏幕/框选识屏的视觉问答）已全部指向**本地 Ollama**，无需任何 API Key、数据不出本机：

- **服务**：Ollama 0.40.x（`%LOCALAPPDATA%\Programs\Ollama\`，开机自动启动，端口 11434）
- **对话模型**：`qwen2.5:7b`（4.7GB，OpenAI 兼容端点 `/v1/chat/completions`）
- **视觉模型**：`qwen2.5vl:7b`（6.0GB，识屏问答用）
- **桌宠配置**：`config.json` → `chat.providers["ollama-local"]`（base_url=`http://127.0.0.1:11434`，api_key 留空即不发鉴权头），`active_provider` 已切换为 `ollama-local`；原有 DeepSeek provider（openai-main）保留可随时切回
- **速度参考**：RTX 4060 8GB 首次响应 20~50 秒（含模型加载），热推理更快；识屏截图越大越慢，属正常现象
- **模型管理**：`ollama list` 查看已有模型；`ollama pull <模型>` 新增；`ollama rm <模型>` 删除
- 如需恢复在线模型：桌宠「设置 → AI 与对话」切换 provider，或改 `config.json` 的 `chat.active_provider` 为 `openai-main`（需此前配置过其 API Key）