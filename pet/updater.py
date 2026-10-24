# -*- coding: utf-8 -*-
"""个人仓库动态查询（个人化改造 P6）。

联网查询个人 GitHub 仓库（ylzqmjxh/dsh-pet-teleagent）的最新 Release 与
最近提交，供设置页「更新」区与右键菜单展示项目动态。

个人项目不做安装包自动更新：上游的下载/校验/启动安装器链已随个人化移除
（个人仓库无安装包资产，源码运行模式亦无意义）。版本管理采用 SemVer
（语义化版本）+ Git Tag/Release：代码版本号（pet/__init__.py）为唯一真源，
每次发布同步打 tag 推送 GitHub，与 teleagent-changes.json 的时间戳条目
通过 appVersion 字段关联。

匿名调用公开仓库 API（无需 token）；GitHub 匿名限流 60 次/小时，个人使用充裕。
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import __version__

APP_VERSION = __version__
REPO = 'ylzqmjxh/dsh-pet-teleagent'
RELEASE_API = f'https://api.github.com/repos/{REPO}/releases/latest'
COMMITS_API = f'https://api.github.com/repos/{REPO}/commits'
REPO_URL = f'https://github.com/{REPO}'
RELEASES_URL = f'{REPO_URL}/releases'
_USER_AGENT = 'dsh-pet-teleagent'

# ---------------------------------------------------------------------------
# HTTPS 安全工具（个人化改造 P6 保留：角色包下载 pack_download.py 在用）
# ---------------------------------------------------------------------------
_TRUSTED_ASSET_HOSTS = {
    'github.com',
    'objects.githubusercontent.com',
    'github-releases.githubusercontent.com',
    'release-assets.githubusercontent.com',
    'cdn.jsdelivr.net',
    'fastly.jsdelivr.net',
    'gcore.jsdelivr.net',
    # GitHub 加速镜像（分件下载的回退线路；内容身份由 sha256 校验兜底，
    # 镜像本身不需要可信——投毒只会摘要不过、换下一条）
    'gh-proxy.com',
    'mirror.ghproxy.com',
}
_MAX_MANIFEST_BYTES = 2 * 1024 * 1024


class _TrustedRedirect(urllib.request.HTTPRedirectHandler):
    """逐跳校验重定向：初始 URL 过白名单不够——重定向目标也必须 https +
    白名单主机，不许被跳板带到别的源。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _trusted_https_url(newurl):
            raise urllib.error.HTTPError(
                req.full_url, code, f"重定向目标不在可信白名单: {newurl}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def trusted_urlopen(req_or_url, *, timeout: float):
    """带**逐跳重定向校验**的 urlopen（素材包下载的统一出口）。"""
    return urllib.request.build_opener(_TrustedRedirect()).open(req_or_url, timeout=timeout)


def _trusted_https_url(url: str) -> bool:
    try:
        parsed = urllib.parse.urlparse(str(url))
    except ValueError:
        return False
    if parsed.scheme.lower() != 'https' or not parsed.hostname:
        return False
    host = parsed.hostname.lower().rstrip('.')
    if host in _TRUSTED_ASSET_HOSTS:
        if host == 'github.com':
            return f'/{REPO}/' in parsed.path or parsed.path.startswith(f'/{REPO}/releases/')
        return True
    return False


def _safe_filename(name: str) -> str:
    value = Path(str(name)).name
    value = re.sub(r'[^A-Za-z0-9._() -]+', '_', value).strip(' .')
    return value or 'dsh-pet-download'


def _fetch_json(url: str, timeout: float = 5.0):
    """GET 一个 JSON；失败返回 None（记 debug 日志，不抛穿）。"""
    req = urllib.request.Request(url, headers={
        'User-Agent': _USER_AGENT,
        'Accept': 'application/vnd.github+json',
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except Exception as exc:
        logging.debug("GitHub API 请求失败 %s: %s", url, exc)
        return None


def latest_release(timeout: float = 5.0) -> dict | None:
    """个人仓库最新 Release：{version, html_url, notes}；未发布/失败返回 None。"""
    release = _fetch_json(RELEASE_API, timeout)
    if isinstance(release, dict) and release.get('tag_name'):
        return {
            'version': str(release['tag_name']).lstrip('vV'),
            'html_url': str(release.get('html_url') or RELEASES_URL),
            'notes': str(release.get('body') or ''),
        }
    return None


def latest_commits(limit: int = 5, timeout: float = 8.0) -> list[dict]:
    """最近提交列表（新→旧）：[{sha, message, date, url}]；失败返回 []。"""
    try:
        limit = max(1, min(int(limit), 10))
    except (TypeError, ValueError):
        limit = 5
    data = _fetch_json(f'{COMMITS_API}?per_page={limit}', timeout)
    if not isinstance(data, list):
        return []
    out: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        commit = item.get('commit') if isinstance(item.get('commit'), dict) else {}
        author = commit.get('author') if isinstance(commit.get('author'), dict) else {}
        message = str(commit.get('message') or '')
        out.append({
            'sha': str(item.get('sha') or '')[:7],
            'message': message.splitlines()[0] if message else '',
            'date': str(author.get('date') or ''),
            'url': str(item.get('html_url') or REPO_URL),
        })
    return out


def version_parts(tag: str) -> list[int]:
    """SemVer 比较用的数字段列表（'v1.2.3' → [1, 2, 3]）。"""
    out: list[int] = []
    for seg in str(tag).lstrip('vV').split('.'):
        digits = ''
        for ch in seg:
            if ch.isdigit():
                digits += ch
            else:
                break
        out.append(int(digits) if digits else 0)
    return out


def is_newer(latest_tag: str, current: str = APP_VERSION) -> bool:
    """远端 Release 是否比当前运行版本新（SemVer 数字段比较）。"""
    return version_parts(latest_tag) > version_parts(current)


__all__ = [
    'APP_VERSION', 'REPO', 'REPO_URL', 'RELEASES_URL',
    'latest_release', 'latest_commits', 'version_parts', 'is_newer',
]