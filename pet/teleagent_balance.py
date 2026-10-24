# -*- coding: utf-8 -*-
"""TeleAgent 星辰积分余额（个人化改造 P12）。

右键「星辰余额」/ 灵动岛卡片的余额数据源：用 TeleAgent 客户端落在本机的
登录凭据查询星辰平台积分明细接口，把剩余积分写入本机缓存文件。

安全纪律（与 DeepSeek 余额同口径，额外收紧）：
- 凭据**只在内存里**：每次查询现读 ``app-auth/token.json`` 现解密
  （Windows DPAPI + AES-256-GCM，纯系统 API、零第三方依赖），明文不落
  任何文件、不上日志、不进异常文案；
- 端点**写死常量**：不接收外部传入的 URL（查询函数无 url 参数），
  不构成开放代理；https 内建证书校验；
- 缓存文件只存余额数字与时间戳，不存凭据。

凭据生命周期：TeleAgent 客户端日常使用会自动续期 token.json，
本模块每次现读现解，因此**只要客户端还能登录，余额查询就一直有效**。
"""
from __future__ import annotations

import base64
import ctypes
import ctypes.wintypes as wt
import json
import os
import time
import urllib.request
from pathlib import Path

# 固定端点（写死：不构成可被注入任意目标的跳板）
BALANCE_API = "https://agent.teleai.com.cn/meter/super-agent/user/portal/points/detail"
_REFERER = "https://agent.teleai.com.cn/meter/teleagent/user/portal/star-bill"
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36")
_TIMEOUT = 10.0
_MAX_RESPONSE_BYTES = 512 * 1024
CACHE_NAME = "teleagent-balance.json"
CACHE_TTL = 24 * 3600.0  # 缓存过期仅用于"是否值得再查"，读卡片永远现读文件


def teleagent_base() -> Path:
    """TeleAgent 数据目录：环境变量优先，默认 ~/.local/share/TeleAgent。"""
    env = os.environ.get("TELEAGENT_HOME", "").strip()
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "TeleAgent"


# ------------------------------------------------------------ 本地凭据解密

def _dpapi_decrypt(data: bytes) -> bytes:
    """CryptUnprotectData（当前用户 scope，crypt32.dll）。"""
    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    blob_in = DATA_BLOB(len(data), ctypes.cast(
        ctypes.create_string_buffer(data, len(data)), ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise OSError("CryptUnprotectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _aes_gcm_decrypt(key: bytes, nonce: bytes, ciphertext: bytes, tag: bytes) -> bytes:
    """AES-256-GCM 解密（bcrypt.dll，系统自带）。

    注意 LPCWSTR 参数必须传宽字符：算法名/属性名传 str（ctypes 自动转
    wchar_t*），ChainingMode 属性值是 UTF-16LE 字节串（含结尾 null）。
    """

    class BCryptAuthInfo(ctypes.Structure):
        _fields_ = [
            ("cbSize", wt.ULONG), ("dwInfoVersion", wt.ULONG),
            ("pbNonce", ctypes.POINTER(ctypes.c_char)), ("cbNonce", wt.ULONG),
            ("pbAuthData", ctypes.POINTER(ctypes.c_char)), ("cbAuthData", wt.ULONG),
            ("pbTag", ctypes.POINTER(ctypes.c_char)), ("cbTag", wt.ULONG),
            ("pbMacContext", ctypes.POINTER(ctypes.c_char)), ("cbMacContext", wt.ULONG),
            ("cbAAD", wt.ULONG), ("cbData", ctypes.c_ulonglong), ("dwFlags", wt.ULONG),
        ]

    bcrypt = ctypes.windll.bcrypt
    h_alg = ctypes.c_void_p()
    rc = bcrypt.BCryptOpenAlgorithmProvider(ctypes.byref(h_alg), "AES", None, 0)
    if rc:
        raise OSError(f"BCryptOpenAlgorithmProvider rc={rc}")
    try:
        gcm_wide = "ChainingModeGCM".encode("utf-16-le") + b"\x00\x00"
        rc = bcrypt.BCryptSetProperty(h_alg, "ChainingMode", gcm_wide, len(gcm_wide), 0)
        if rc:
            raise OSError(f"BCryptSetProperty rc={rc}")
        h_key = ctypes.c_void_p()
        key_buf = ctypes.create_string_buffer(key, len(key))
        rc = bcrypt.BCryptGenerateSymmetricKey(
            h_alg, ctypes.byref(h_key), None, 0, key_buf, len(key), 0)
        if rc:
            raise OSError(f"BCryptGenerateSymmetricKey rc={rc}")
        try:
            tag_buf = ctypes.create_string_buffer(tag, len(tag))
            nonce_buf = ctypes.create_string_buffer(nonce, len(nonce))
            auth = BCryptAuthInfo(
                ctypes.sizeof(BCryptAuthInfo), 1,
                ctypes.cast(nonce_buf, ctypes.POINTER(ctypes.c_char)), len(nonce),
                None, 0,
                ctypes.cast(tag_buf, ctypes.POINTER(ctypes.c_char)), len(tag),
                None, 0, 0, 0, 0)
            out = ctypes.create_string_buffer(len(ciphertext))
            out_len = wt.ULONG(0)
            ct_buf = ctypes.create_string_buffer(ciphertext, len(ciphertext))
            rc = bcrypt.BCryptDecrypt(
                h_key, ct_buf, len(ciphertext), ctypes.byref(auth),
                None, 0, out, len(ciphertext), ctypes.byref(out_len), 0)
            if rc:
                raise OSError(f"BCryptDecrypt rc={rc}")
            return out.raw[:out_len.value]
        finally:
            bcrypt.BCryptDestroyKey(h_key)
    finally:
        bcrypt.BCryptCloseAlgorithmProvider(h_alg, 0)


def _find_token_file() -> Path | None:
    """定位 TeleAgent 登录凭据：users/<用户>/app-auth/token.json（取最新）。"""
    pattern = "users/*/app-auth/token.json"
    candidates = [p for p in teleagent_base().glob(pattern) if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _oscrypt_key() -> bytes:
    """Chromium OSCrypt 主密钥：Local State 的 DPAPI 包裹（v10 专用）。"""
    local_state = teleagent_base() / "Local State"
    data = json.loads(local_state.read_text(encoding="utf-8"))
    enc_key = base64.b64decode(data["os_crypt"]["encrypted_key"])
    if enc_key[:5] != b"DPAPI":
        raise ValueError("OSCrypt 密钥格式异常（非 DPAPI 前缀）")
    return _dpapi_decrypt(enc_key[5:])


def load_credentials() -> tuple[str, str]:
    """现读现解本地凭据 → (x_token, user_id)。明文只在本函数返回值里。"""
    token_file = _find_token_file()
    if token_file is None:
        raise FileNotFoundError("未找到 TeleAgent 登录凭据（token.json）")
    record = json.loads(token_file.read_text(encoding="utf-8"))
    raw = base64.b64decode(record["encryptedToken"])
    if raw[:3] != b"v10":
        raise ValueError(f"凭据版本异常: {raw[:3]!r}")
    plain = _aes_gcm_decrypt(_oscrypt_key(), raw[3:15], raw[15:-16], raw[-16:])
    token = plain.decode("utf-8", errors="strict")
    user_id = _jwt_user_id(token)
    if not user_id:
        raise ValueError("凭据里没有 userId")
    return token, user_id


def _jwt_user_id(token: str) -> str:
    """从 ``<前缀>:<header>.<payload>.<sig>`` 形态的 JWT 变体里取 userId。"""
    body = token.split(":", 1)[-1]
    parts = body.split(".")
    if len(parts) < 2:
        return ""
    payload_b64 = parts[1]
    try:
        payload = json.loads(base64.urlsafe_b64decode(
            payload_b64 + "=" * (-len(payload_b64) % 4)))
    except (ValueError, TypeError):
        return ""
    return str(payload.get("userId") or "")


# ------------------------------------------------------------ 查询与解析

def fetch_balance() -> dict:
    """查询星辰积分余额 → {"balance", "used_rate", "fetched_at"}。

    失败抛异常（文案不带凭据）；成功也**不**在此写缓存（写缓存由调用方
    决定，保持"取数"与"落盘"单一职责）。
    """
    token, user_id = load_credentials()
    req = urllib.request.Request(BALANCE_API, method="GET", headers={
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "content-type": "application/json",
        "Referer": _REFERER,
        "User-Agent": _UA,
        "x-token": token,
        "userid": user_id,
    })
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        body = resp.read(_MAX_RESPONSE_BYTES)
    payload = json.loads(body.decode("utf-8", errors="strict"))
    if int(payload.get("code") or 0) != 200:
        raise RuntimeError(f"接口返回异常 code={payload.get('code')}")
    data = payload.get("data") or {}
    balance = data.get("pointsBalance")
    if not isinstance(balance, (int, float)):
        # 兜底：聚合条目 active[0].balance 与 pointsBalance 同源
        for group in data.get("groups") or []:
            for item in group.get("active") or []:
                if isinstance(item.get("balance"), (int, float)):
                    balance = item["balance"]
                    break
            if isinstance(balance, (int, float)):
                break
    if not isinstance(balance, (int, float)):
        raise RuntimeError("响应里没有余额字段")
    used_rate = ""
    try:
        item = ((data.get("groups") or [{}])[0].get("active") or [{}])[0]
        used_rate = str(item.get("usedRate") or "")
    except (IndexError, KeyError, TypeError):
        pass
    return {"balance": float(balance), "used_rate": used_rate,
            "fetched_at": time.time()}


def format_balance(info: dict) -> str:
    """气泡/卡片播报文案：余额数字为主，带本月使用率（有则带）。"""
    text = f"星辰余额 {info['balance']:.2f} 积分"
    if info.get("used_rate") not in ("", None):
        text += f"（本月已用 {info['used_rate']}%）"
    return text


# ------------------------------------------------------------ 本机缓存

def read_cache(config_dir) -> dict | None:
    """读余额缓存：{"balance", "used_rate", "fetched_at", "text"}；坏文件当没有。"""
    try:
        data = json.loads(
            (Path(config_dir) / CACHE_NAME).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("balance"), (int, float)):
            return None
        info = {"balance": float(data["balance"]),
                "used_rate": str(data.get("used_rate") or ""),
                "fetched_at": float(data.get("fetched_at") or 0)}
        info["text"] = format_balance(info)
        return info
    except (OSError, ValueError, TypeError):
        return None


def write_cache(config_dir, info: dict) -> bool:
    """写余额缓存（只存数字与时间戳，不存任何凭据）；失败返回 False。"""
    try:
        path = Path(config_dir) / CACHE_NAME
        path.write_text(json.dumps({
            "balance": info.get("balance"),
            "used_rate": info.get("used_rate"),
            "fetched_at": info.get("fetched_at"),
        }, ensure_ascii=False), encoding="utf-8")
        return True
    except OSError:
        return False
