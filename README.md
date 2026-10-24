# dsh-pet-teleagent

个人定制版桌面桌宠（大肥鱼）——Python + PySide6 实现，基于开源项目 [dsh-pet-indesktop](https://github.com/MerZlin/dsh-pet-indesktop)（MIT License）二次开发，感谢原作者的贡献；版权与许可声明见 [LICENSE](LICENSE)。

在原版基础上做了以下深度定制：

- **TeleAgent 联动**：六态事件总线（thinking/working/attention/error/idle/sleeping）驱动桌宠动画与气泡；自动状态监视器实时同步任务执行状态
- **灵动岛状态同步**：状态灯 + 文字注释（运行中/思考中/刚完成/待命/出错）双通道反映 AI 工作状态（本地补丁 + 岛扩展组件）
- **本地大模型（零 API Key）**：接入 Ollama——对话 `qwen2.5:7b`、识屏视觉 `qwen2.5vl:7b`，数据不出本机
- **更新页本地化**：TeleAgent 变更记录卡片 + 项目信息分区

## 快速开始

```
双击 启动桌宠.bat        # 启动桌宠（同时拉起 TeleAgent 状态监视器）
python -m pet            # 或命令行启动
```

依赖安装（首次或换机）：`pip install -r requirements.txt`

## 目录结构

- `pet/` —— 桌宠主体（PySide6，含本地补丁）
- `assets/` —— 动画素材（106 段 WebM）
- `resources/` —— OCR 模型（PP-OCRv6）等
- `启动桌宠.bat` —— 一键启动
- `teleagent_bridge.py` —— TeleAgent 事件桥接脚本
- `teleagent-changes.json` —— 本地变更记录（设置页「更新」读取展示）
- `README-TeleAgent.md` —— 定制功能的完整说明（联动/岛/本地模型/补丁清单）

## 定制与版本管理

- 本仓库为**个人项目管理仓库**，每次功能更新附带时间戳版本号与变更文档（见 `teleagent-changes.json` 与 `README-TeleAgent.md` 的补丁记录）
- 本地补丁均在源码中带「TeleAgent 本地补丁」或「个人化改造」注释标记，可全局搜索定位

## 许可

MIT License（见 [LICENSE](LICENSE)，保留自上游项目的版权与许可声明）。