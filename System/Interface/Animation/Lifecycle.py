from __future__ import annotations

import weakref

from PyQt6.QtGui import (
    QHideEvent,
    QShowEvent
)

from System.Interface.Animation import LoomEngine

class LoomAnimationMixin:
    _engine_acquired: bool

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._engine_acquired = False

        if hasattr(self, "destroyed"):
            weak_self: weakref.ReferenceType[LoomAnimationMixin] = weakref.ref(self)
            self.destroyed.connect(lambda: LoomAnimationMixin._safe_cleanup(weak_self))

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._engine_acquired:
            LoomEngine.ui_engine.acquire()
            self._engine_acquired = True

    def hideEvent(self, event: QHideEvent) -> None:
        super().hideEvent(event)
        if self._engine_acquired:
            LoomEngine.ui_engine.release()
            self._engine_acquired = False

    @staticmethod
    def _safe_cleanup(weak_self: weakref.ReferenceType[LoomAnimationMixin]) -> None:
        object = weak_self()

        if object is not None:
            if object._engine_acquired:
                LoomEngine.ui_engine.release()
                object._engine_acquired = False

            LoomEngine.ui_engine.unbind_owner(object)