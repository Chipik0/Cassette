from __future__ import annotations

from PyQt6.QtGui import QImage

from PyQt6.QtCore import (
    QObject,
    pyqtSignal
)

class TileWorkerSignals(QObject):
    tile_ready = pyqtSignal(int, QImage)