"""Screen grabbing via Qt screens (PyQt5)."""

from __future__ import annotations

import numpy as np
from PyQt5.QtGui import QGuiApplication, QImage


class ScreenCapturer:
    def __init__(self, monitor_index: int = 0) -> None:
        self.monitor_index = monitor_index

    def grab(self) -> np.ndarray | None:
        screens = QGuiApplication.screens()
        if not screens:
            return None
        index = self.monitor_index if 0 <= self.monitor_index < len(screens) else 0
        pixmap = screens[index].grabWindow(0)
        if pixmap.isNull():
            return None
        image = pixmap.toImage().convertToFormat(QImage.Format_RGB888)
        width = image.width()
        height = image.height()
        bytes_per_line = image.bytesPerLine()
        pointer = image.constBits()
        pointer.setsize(image.byteCount())
        array = (
            np.frombuffer(pointer, np.uint8)
            .reshape((height, bytes_per_line))[:, : width * 3]
            .reshape((height, width, 3))
        )
        return array[:, :, ::-1].copy()  # RGB -> BGR
