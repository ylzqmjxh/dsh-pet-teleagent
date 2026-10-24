# -*- coding: utf-8 -*-
"""个人项目更新区（个人化改造 P6）：版本展示 + 仓库最新动态。

不做安装包自动更新（个人项目无安装包资产）：「获取最新动态」拉取个人
GitHub 仓库的最近提交与最新 Release 说明展示；「打开仓库页」直达仓库。
版本管理采用 SemVer + Git Tag/Release，与 teleagent-changes.json 时间戳
条目经 appVersion 字段关联。不写入 Config。
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import __version__, updater
from .settings_about import build_info_section

#: 个人化改造 P8：提交说明的展示截断长度（字符）
_COMMIT_MESSAGE_LIMIT = 48


def _format_commit_time(iso_date: str) -> str:
    """ISO8601（GitHub API 的 author.date，UTC）→ 本地时间“MM-DD HH:MM”；解析失败返回空串。"""
    text = str(iso_date or "").strip()
    if not text:
        return ""
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return moment.astimezone().strftime("%m-%d %H:%M")
    except ValueError:
        return ""


def _format_commit_line(commit: dict) -> str:
    """一条提交 → 人话展示行：日期时间 + 说明（截断）；不显示哈希（对使用者无意义）。"""
    message = str(commit.get("message") or "")
    if len(message) > _COMMIT_MESSAGE_LIMIT:
        message = message[:_COMMIT_MESSAGE_LIMIT].rstrip() + "…"
    when = _format_commit_time(commit.get("date"))
    return f"{when}  {message}".strip()


class UpdatePage(QWidget):
    """版本展示与仓库动态；不写入 Config，避免把一次性命令变成设置项。"""

    check_finished = Signal(object)

    def __init__(self, config, *, include_chat: bool = True, parent=None):
        super().__init__(parent)
        self.config = config
        # include_chat 仅为兼容旧调用签名保留（个人化后不再区分构建变体）
        self.include_chat = bool(include_chat)
        self.release: dict | None = None
        self._busy = False
        self._build_ui()
        self.check_finished.connect(self._on_check_finished)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        intro = QLabel(
            f"当前版本 v{__version__}（个人定制版）。项目动态来自个人仓库 "
            "dsh-pet-teleagent 的 GitHub 提交与 Release。",
            self,
        )
        intro.setWordWrap(True)
        intro.setObjectName("updateIntro")
        layout.addWidget(intro)

        status_card = QFrame(self)
        status_card.setObjectName("updateStatusCard")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(16, 14, 16, 14)
        status_layout.setSpacing(8)
        self.version_label = QLabel(f"当前版本  v{__version__}（个人定制版）", status_card)
        self.version_label.setObjectName("updateCurrentVersion")
        self.status_label = QLabel("尚未获取动态", status_card)
        self.status_label.setObjectName("updateStatus")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.version_label)
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_card)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.check_button = QPushButton("获取最新动态", self)
        self.check_button.setObjectName("checkUpdateButton")
        self.check_button.setToolTip("拉取个人仓库的最近提交与最新 Release 说明")
        self.check_button.clicked.connect(self.fetch_activity)
        self.manual_button = QPushButton("打开仓库页", self)
        self.manual_button.setObjectName("manualUpdateButton")
        self.manual_button.setEnabled(True)
        self.manual_button.setToolTip("打开个人仓库 dsh-pet-teleagent")
        self.manual_button.clicked.connect(self.open_repo_page)
        action_row.addWidget(self.check_button)
        action_row.addWidget(self.manual_button)
        action_row.addStretch(1)
        layout.addLayout(action_row)

        notes_card = QFrame(self)
        notes_card.setObjectName("updateNotesCard")
        notes_layout = QVBoxLayout(notes_card)
        notes_layout.setContentsMargins(16, 14, 16, 14)
        notes_layout.setSpacing(6)
        notes_title = QLabel("最新动态", notes_card)
        notes_title.setObjectName("updateNotesTitle")
        self.notes_label = QLabel("点击「获取最新动态」查看仓库最近提交。", notes_card)
        self.notes_label.setObjectName("updateNotes")
        self.notes_label.setWordWrap(True)
        self.notes_label.setTextInteractionFlags(
            self.notes_label.textInteractionFlags()
            | Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.notes_label.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        notes_layout.addWidget(notes_title)
        notes_layout.addWidget(self.notes_label)
        layout.addWidget(notes_card)
        # 个人化改造 P3：项目信息分区（关联个人 GitHub 仓库）
        layout.addWidget(build_info_section(self))
        layout.addStretch(1)

    def fetch_activity(self) -> None:
        if self._busy:
            return
        self._busy = True
        self._set_state("正在获取最新动态…", busy=True)

        def worker() -> None:
            try:
                commits = updater.latest_commits(limit=5)
                release = updater.latest_release()
            except Exception as exc:  # noqa: BLE001
                logging.exception("获取仓库动态失败")
                self.check_finished.emit(exc)
                return
            self.check_finished.emit({"commits": commits, "release": release})

        threading.Thread(target=worker, daemon=True, name="pet-settings-activity").start()

    def _on_check_finished(self, result) -> None:
        self._busy = False
        if isinstance(result, Exception) or not isinstance(result, dict):
            self.release = None
            self._set_state("获取动态失败：网络不可达或接口限流，稍后再试。", busy=False)
            return
        commits = result.get("commits") or []
        release = result.get("release") or None
        self.release = release
        if commits:
            lines = [_format_commit_line(c) for c in commits]
            text = "\n".join(lines)
            if release and updater.is_newer(str(release.get("version") or "")):
                text = (f"发现新版本 v{release.get('version')}（见 Release 说明）：\n"
                        + str(release.get("notes") or "") + "\n\n" + text)
                self._set_state(f"有新版本 v{release.get('version')} 可查看。", busy=False)
            else:
                self._set_state(f"当前 v{__version__}，仓库最近动态如下。", busy=False)
        else:
            text = "暂无提交记录（仓库为空或网络不可达）。"
            self._set_state("未拉取到提交记录。", busy=False)
        self.notes_label.setText(text)

    def open_repo_page(self) -> None:
        # 个人化改造 P4/P6：打开个人仓库页（有新 Release 时直达其说明页）
        url = str((self.release or {}).get("html_url") or updater.REPO_URL)
        QDesktopServices.openUrl(QUrl(url))

    def _set_state(self, text: str, *, busy: bool) -> None:
        self.status_label.setText(text)
        self.check_button.setEnabled(not busy)


__all__ = ["UpdatePage"]