# -*- coding: utf-8 -*-
"""Read-only project information shown at the bottom of the Updates page."""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QPushButton, QToolTip, QVBoxLayout, QWidget,
)

from .context_menus.icons import vector_widget_icon
from .settings_widgets import SettingsSection

# --- 个人化改造 P3（20261023T193500Z）：项目信息分区（替代原“作者账号”区） ---
#: 个人仓库地址（占位 ylzqmjxh，上传后统一替换）
REPO_URL = "https://github.com/ylzqmjxh/dsh-pet-teleagent"

PROJECT_INFO = (
    ("技术栈", "Python 3 + PySide6（Qt for Python）", ""),
    ("项目维护", "个人定制版（本地部署与深度定制）", ""),
    ("个人仓库", "github.com/ylzqmjxh/dsh-pet-teleagent", REPO_URL),
)

#: 二次开发致谢（公开合规：MIT LICENSE 保留 + 来源声明）
PROJECT_ACK = (
    "本项目基于开源项目 dsh-pet-indesktop（MIT License）二次开发，"
    "感谢原作者的贡献；版权与许可声明见仓库根目录 LICENSE。"
)


def build_info_section(parent: QWidget | None = None) -> SettingsSection:
    """项目信息分区（个人化改造 P3）：技术栈/维护/个人仓库，可点击直达。"""
    rows = [_account_row(platform, handle, url=url)
            for platform, handle, url in PROJECT_INFO]
    section = SettingsSection("项目信息", rows, parent)
    ack = QLabel(PROJECT_ACK, section)
    ack.setWordWrap(True)
    ack.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
        | Qt.TextInteractionFlag.TextSelectableByKeyboard)
    ack.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
    if hasattr(section, "layout") and section.layout() is not None:
        section.layout().addWidget(ack)
    return section


class InfoRow(QWidget):
    """项目信息行（只读面，与 Config 无关）。

    刻意**不是** ``SettingRow``：这一行没有配置键、没有「已修改 / 回改默认」。
    但搜索只读 ``label`` / ``hint_label`` / ``objectName``
    和祖先组标题（见 ``settings_search._row_text``），所以按同一个形状暴露这两个属性
    就够被索引到，不必为"可搜"改掉这里的排版。
    """

    def __init__(self, platform: str, handle: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(f"authorRow_{platform}")
        self.label = QLabel(platform, self)
        self.hint_label = QLabel(handle, self)


def _account_row(platform: str, handle: str, *, url: str = "") -> QWidget:
    row = InfoRow(platform, handle)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(16, 10, 16, 10)
    layout.setSpacing(12)
    text = QVBoxLayout()
    text.setSpacing(3)
    for label, role in ((row.label, "settingHint"), (row.hint_label, "settingLabel")):
        label.setObjectName(role)
        label.setWordWrap(True)
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        label.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        text.addWidget(label)
    layout.addLayout(text, 1)
    copy = _button(row, "copy", f"复制 {platform} 内容 {handle}")
    copy.clicked.connect(lambda: _copy_account(handle, copy))
    layout.addWidget(copy)
    if url:
        # 直达链接（个人仓库等）
        link = _button(row, "external_link", f"打开 {handle}")
        link.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        layout.addWidget(link)
    return row


def _button(parent: QWidget, icon: str, name: str) -> QPushButton:
    button = QPushButton(parent)
    button.setIcon(vector_widget_icon(button, icon))
    button.setFixedSize(32, 32)
    button.setToolTip(name)
    button.setAccessibleName(name)
    button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def _copy_account(handle: str, button: QPushButton) -> None:
    QApplication.clipboard().setText(handle)
    QToolTip.showText(button.mapToGlobal(QPoint(0, button.height())), "已复制", button)
