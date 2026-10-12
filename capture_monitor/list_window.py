"""采图列表 window and settings dialog (PyQt5)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from capture_monitor.config import Config

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp"}
THUMB_WIDTH = 112
THUMB_HEIGHT = 64


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("设置")
        self._config = config

        form = QFormLayout()

        self.save_dir_edit = QLineEdit(
            config.save_dir if config.save_dir else str(config.resolved_save_dir())
        )
        save_row = QWidget()
        save_layout = QHBoxLayout(save_row)
        save_layout.setContentsMargins(0, 0, 0, 0)
        save_layout.addWidget(self.save_dir_edit)
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self._browse_save_dir)
        save_layout.addWidget(browse_button)
        form.addRow("保存目录", save_row)

        self.reference_edit = QLineEdit(config.reference_image)
        form.addRow("参考图", self.reference_edit)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 1.0)
        self.threshold_spin.setSingleStep(0.05)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(config.match_threshold)
        form.addRow("匹配阈值", self.threshold_spin)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(100, 60000)
        self.interval_spin.setValue(config.capture_interval_ms)
        form.addRow("采集间隔(ms)", self.interval_spin)

        self.confirm_spin = QSpinBox()
        self.confirm_spin.setRange(1, 30)
        self.confirm_spin.setValue(config.min_confirm_frames)
        form.addRow("连续确认帧", self.confirm_spin)

        self.hamming_spin = QSpinBox()
        self.hamming_spin.setRange(0, 64)
        self.hamming_spin.setValue(config.dedup_hamming_threshold)
        form.addRow("去重汉明距离", self.hamming_spin)

        self.diff_spin = QDoubleSpinBox()
        self.diff_spin.setRange(0.0, 1.0)
        self.diff_spin.setSingleStep(0.002)
        self.diff_spin.setDecimals(3)
        self.diff_spin.setValue(config.dedup_max_diff)
        form.addRow("变化阈值(去重)", self.diff_spin)

        self.monitor_spin = QSpinBox()
        self.monitor_spin.setRange(0, 8)
        self.monitor_spin.setValue(config.monitor_index)
        form.addRow("显示器序号", self.monitor_spin)

        self.format_combo = QComboBox()
        self.format_combo.addItems(["png", "jpg"])
        format_index = self.format_combo.findText(str(config.image_format).lower())
        self.format_combo.setCurrentIndex(format_index if format_index >= 0 else 0)
        form.addRow("图像格式", self.format_combo)

        self.hotkey_enabled_check = QCheckBox("启用全局快捷键采图")
        self.hotkey_enabled_check.setChecked(config.hotkey_enabled)
        form.addRow("快捷键", self.hotkey_enabled_check)
        self.hotkey_edit = QLineEdit(config.hotkey)
        form.addRow("按键(如 F9 / Ctrl+Alt+S)", self.hotkey_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _browse_save_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "选择保存目录", self.save_dir_edit.text()
        )
        if directory:
            self.save_dir_edit.setText(directory)

    def result_config(self) -> Config:
        new = Config.from_dict(self._config.to_dict())
        new.save_dir = self.save_dir_edit.text().strip()
        new.reference_image = self.reference_edit.text().strip()
        new.match_threshold = float(self.threshold_spin.value())
        new.capture_interval_ms = int(self.interval_spin.value())
        new.min_confirm_frames = int(self.confirm_spin.value())
        new.dedup_hamming_threshold = int(self.hamming_spin.value())
        new.dedup_max_diff = float(self.diff_spin.value())
        new.monitor_index = int(self.monitor_spin.value())
        new.image_format = str(self.format_combo.currentText())
        new.hotkey = self.hotkey_edit.text().strip() or "F9"
        new.hotkey_enabled = bool(self.hotkey_enabled_check.isChecked())
        return new


class CaptureListWindow(QWidget):
    def __init__(self, config: Config, on_config_changed=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("采图列表")
        self.resize(760, 480)
        self.config = config
        self.on_config_changed = on_config_changed

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["缩略图", "文件名", "时间", "匹配分"])
        self._table.setColumnWidth(0, 120)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.verticalHeader().setDefaultSectionSize(70)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)

        open_button = QPushButton("打开目录")
        open_button.clicked.connect(self._open_dir)
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self.refresh)
        clear_button = QPushButton("清空记录")
        clear_button.clicked.connect(self._clear)
        settings_button = QPushButton("设置")
        settings_button.clicked.connect(self._settings)

        toolbar = QHBoxLayout()
        toolbar.addWidget(open_button)
        toolbar.addWidget(refresh_button)
        toolbar.addWidget(clear_button)
        toolbar.addWidget(settings_button)
        toolbar.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addWidget(self._table)

    def add_capture(self, path, meta: dict | None = None) -> None:
        meta = meta if meta is not None else {}
        name = Path(path).name
        pixmap = QPixmap(path)
        if pixmap.isNull():
            pixmap = None
        else:
            pixmap = pixmap.scaled(
                THUMB_WIDTH, THUMB_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        self._table.insertRow(0)
        if pixmap is not None:
            cell = QLabel()
            cell.setPixmap(pixmap)
            cell.setAlignment(Qt.AlignCenter)
            self._table.setCellWidget(0, 0, cell)
        else:
            self._table.setItem(0, 0, QTableWidgetItem(name))
        self._table.setItem(0, 1, QTableWidgetItem(name))
        timestamp = meta.get("time")
        time_text = (
            datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            if timestamp
            else ""
        )
        self._table.setItem(0, 2, QTableWidgetItem(time_text))
        score = meta.get("score")
        score_text = f"{score:.4f}" if score is not None else ""
        self._table.setItem(0, 3, QTableWidgetItem(score_text))

    def refresh(self) -> None:
        self._table.setRowCount(0)
        directory = self.config.resolved_save_dir()
        if not directory.is_dir():
            return
        files = [
            candidate
            for candidate in directory.iterdir()
            if candidate.is_file() and candidate.suffix.lower() in IMAGE_EXTS
        ]
        files.sort(key=lambda candidate: candidate.stat().st_mtime, reverse=True)
        for path in reversed(files):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                mtime = None
            self.add_capture(str(path), {"time": mtime, "score": None})

    def _open_dir(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.config.resolved_save_dir())))

    def _clear(self) -> None:
        answer = QMessageBox.question(
            self,
            "清空记录",
            "确定要清空列表记录吗？（不会删除任何文件）",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self._table.setRowCount(0)

    def _settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            new = dialog.result_config()
            new.save()
            self.config = new
            self.refresh()
            if self.on_config_changed is not None:
                self.on_config_changed(new)
