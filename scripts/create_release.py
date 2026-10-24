# -*- coding: utf-8 -*-
"""把 RELEASE-NOTES.md 中对应版本段发布为 GitHub Release（上架说明）。

用法: python create_release.py <tag>   如: python create_release.py v1.1.0
已存在同名 Release 时跳过（幂等）。
"""
import json
import re
import sys
import urllib.error
import urllib.request

TOKEN_FILE = r"C:\Users\ylzqm\.local\share\TeleAgent\TeleAgent的工作空间\.temp\github-token.txt"
NOTES = r"C:\soft\dsh-pet-teleagent\RELEASE-NOTES.md"
API = "https://api.github.com/repos/ylzqmjxh/dsh-pet-teleagent/releases"

tag = sys.argv[1] if len(sys.argv) > 1 else "v1.1.0"

# 1) 从 RELEASE-NOTES.md 提取该版本段（## <tag> ... 到下一个 ## 或文件尾）
text = open(NOTES, encoding="utf-8").read()
pattern = rf"^## {re.escape(tag)}\b(.*?)(?=^## |\Z)"
match = re.search(pattern, text, re.S | re.M)
if not match:
    raise SystemExit("RELEASE-NOTES.md 中未找到 %s 段落" % tag)
section = match.group(0).split("\n", 1)[1].strip()
# 首行取标题（## 行内“ — ”后的说明）
title_line = re.search(rf"^## {re.escape(tag)}\s*(.*)$", text, re.M)
subtitle = title_line.group(1).strip().lstrip("—- ").strip() if title_line else ""
name = f"{tag}{' ' + subtitle if subtitle else ''}"

with open(TOKEN_FILE, encoding="utf-8") as f:
    token = f.read().strip()

payload = {
    "tag_name": tag,
    "name": name,
    "body": section,
    "draft": False,
    "prerelease": False,
}
req = urllib.request.Request(
    API,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": f"Bearer {token}",
             "User-Agent": "dsh-pet-teleagent",
             "Accept": "application/vnd.github+json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.load(resp)
    print("RELEASE CREATED:", result.get("html_url"))
except urllib.error.HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")[:300]
    if exc.code == 422 and "already_exists" in body:
        print("RELEASE EXISTS: %s 已发布，跳过" % tag)
    else:
        raise SystemExit("create release failed %s: %s" % (exc.code, body))