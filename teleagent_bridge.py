# -*- coding: utf-8 -*-
"""TeleAgent → dsh-pet 事件桥接器。

把 TeleAgent 的工作状态写入桌宠监听的本地事件总线
（<APPDATA>/dsh-pet-standalone/agent-events/teleagent.jsonl），
让桌面大肥鱼随之切换动画 / 冒泡（需在桌宠「设置 → 联动」里开启 Agent 联动）。

用法：
    python teleagent_bridge.py working                # 显式六态词汇
    python teleagent_bridge.py working --tool bash  # 附带工具名（气泡「正在跑命令」）
    python teleagent_bridge.py --event PreToolUse   # 用事件名（桌宠按内置映射归一）
    python teleagent_bridge.py idle
    python teleagent_bridge.py --list                # 列出可用状态

也可作为模块导入：
    from teleagent_bridge import notify
    notify(state="working", tool="bash")
"""
import argparse
import json
import os
import sys
import time

STATES = {"thinking", "working", "attention", "error", "idle", "sleeping"}


def event_dir() -> str:
    appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(appdata, "dsh-pet-standalone", "agent-events")


def event_file() -> str:
    return os.path.join(event_dir(), "teleagent.jsonl")


def notify(state: str | None = None, event: str | None = None,
           tool: str | None = None, ts: float | None = None) -> str:
    """追加一行 JSON 事件到桌宠监听的总线，返回写入的文件路径。"""
    d = event_dir()
    os.makedirs(d, exist_ok=True)
    if ts is None:
        ts = time.time()
    rec: dict = {"ts": ts, "agent": "teleagent"}
    if event:
        rec["event"] = event
    if state:
        rec["state"] = state
    if tool:
        rec["tool"] = tool.lower()
    path = event_file()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="TeleAgent → dsh-pet 事件桥接")
    ap.add_argument("value", nargs="?", help="六态词汇或事件名")
    ap.add_argument("--state", help="显式状态（优先）")
    ap.add_argument("--event", help="事件名（如 PreToolUse）")
    ap.add_argument("--tool", help="工具名（小写）")
    ap.add_argument("--ts", type=float, help="时间戳（默认当前）")
    ap.add_argument("--list", action="store_true", help="列出可用状态")
    args = ap.parse_args(argv)

    if args.list:
        print("可用状态: " + ", ".join(sorted(STATES)))
        return 0

    state = args.state or (args.value if args.value in STATES else None)
    event = args.event or (args.value if args.value not in STATES else None)
    if not state and not event:
        print("错误：请给出状态或事件名。示例：python teleagent_bridge.py working",
              file=sys.stderr)
        return 2

    path = notify(state=state, event=event, tool=args.tool, ts=args.ts)
    print("已写入: %s" % path)
    print("内容: %s" % json.dumps(
        {"agent": "teleagent", "state": state, "event": event,
         "tool": args.tool, "ts": args.ts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())