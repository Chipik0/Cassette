from __future__ import annotations

from collections.abc import Callable

from loguru import logger

from PyQt6.QtCore import QSettings
from PyQt6.QtGui  import QResizeEvent

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout
)

from System.Common import (
    Utils,
    Styles,
    Constants
)

from System.Interface import Widgets

from System.Interface.Animation import (
    Lifecycle,
    LoomEngine
)

from System.Interface.Windows import FloatingWindowGPU

# Settings Widget Registry

SETTING_WIDGET_REGISTRY: dict[str, tuple[Callable[[object, dict[str, object]], QWidget], Callable[[QWidget], object]]] = {
    "checkbox": (
        lambda value, configuration: Widgets.CheckboxWithLabel(
            title       = str(configuration["title"]),
            description = str(configuration["description"]),
            default     = bool(configuration["default"]) if value is None else str(value).lower() == "true"
        ),
        lambda widget: widget.isChecked()
    ),

    "slider": (
        lambda value, configuration: Widgets.SliderWithLabel(
            description   = str(configuration["title"]),
            minimum_value = int(configuration["min"]),
            maximum_value = int(configuration["max"]),
            default_value = int(configuration["default"]) if value is None or str(value) == "" else int(value)
        ),
        lambda widget: widget.value()
    ),

    "selector": (
        lambda value, configuration: Widgets.SelectorWithLabel(
            description   = str(configuration["title"]),
            items         = configuration["map"],
            default_text  = str(configuration["default"]) if value is None else None,
            default_value = value
        ),
        lambda widget: widget.current_data()
    ),

    "delay_setup": (
        lambda value, configuration: Widgets.DelaySetupper(
            description = str(configuration["description"]),
            default_ms  = int(configuration["default"]) if value is None or str(value) == "" else int(value)
        ),
        lambda widget: widget.current_value()
    ),

    "tutorial_reset": (
        lambda value, configuration: Widgets.TutorialResetter(
            description = str(configuration["description"]),
            button_text = str(configuration.get("button_text", "Reset"))
        ),
        lambda widget: widget.current_value()
    )
}

def register_setting_widget_type(
        type_identifier: str,
        factory:         Callable[[object, dict[str, object]], QWidget],
        value_getter:    Callable[[QWidget], object]
    ) -> None:

    SETTING_WIDGET_REGISTRY[type_identifier] = (factory, value_getter)

# Animated Page Track

class AnimatedPageTrack(Lifecycle.LoomAnimationMixin, QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.canvas             = QWidget(self)
        self.pages              = []
        self.current_page_index = 0
        self.page_width_px      = 0
        self.page_height_px     = 360

        self.canvas.setStyleSheet("background: transparent;")
        self.setStyleSheet("background: transparent;")
        self.setFixedHeight(self.page_height_px)

        self.scroll_handle = LoomEngine.ui_engine.bind(
            owner      = self,
            name       = "track_scroll",
            base_value = 0.0,
            mix_mode   = LoomEngine.MixMode.REPLACE,
            on_change  = self.on_scroll_offset_changed
        )

    # Animation Handlers

    def on_scroll_offset_changed(self, value: float) -> None:
        offset_x_px = int(round(value))
        self.canvas.move(-offset_x_px, 0)

    # Navigation

    def slide_to_index(self, target_index: int) -> None:
        if target_index == self.current_page_index:
            return

        if not (0 <= target_index < len(self.pages)):
            return

        self.current_page_index = target_index
        target_x_px             = float(target_index * self.page_width_px)

        if not Constants.current_settings.get("floating_window_animations", True):
            self.scroll_handle.set_base(target_x_px)
            self.canvas.move(-int(round(target_x_px)), 0)
            return

        if not self.isVisible() or self.page_width_px <= 0:
            self.scroll_handle.set_base(target_x_px)
            self.canvas.move(-int(round(target_x_px)), 0)
            return

        self.scroll_handle.set_target(
            value           = target_x_px,
            duration_ms     = 300,
            easing_function = LoomEngine.Easing.ease_out_quint
        )

    def set_current_index(self, index: int) -> None:
        if not (0 <= index < len(self.pages)):
            return

        self.current_page_index = index
        target_x_px             = float(index * self.page_width_px)

        self.scroll_handle.set_base(target_x_px)
        self.canvas.move(-int(round(target_x_px)), 0)

    def current_index(self) -> int:
        return self.current_page_index

    # Page Management

    def add_page(self, page_widget: QWidget) -> None:
        page_widget.setParent(self.canvas)
        page_widget.show()

        self.pages.append(page_widget)
        self.update_canvas_geometry()

    def clear_pages(self) -> None:
        for page in self.pages:
            page.deleteLater()

        self.pages.clear()
        self.current_page_index = 0
        self.update_canvas_geometry()

    def set_page_width(self, width_px: int) -> None:
        self.page_width_px = width_px

        self.setFixedWidth(width_px)
        self.update_canvas_geometry()

        current_x_px = float(self.current_page_index * self.page_width_px)
        self.scroll_handle.set_base(current_x_px)
        self.canvas.move(-int(round(current_x_px)), 0)

    def update_canvas_geometry(self) -> None:
        total_pages     = len(self.pages)
        canvas_width_px = total_pages * self.page_width_px

        self.canvas.setGeometry(
            -int(round(self.scroll_handle.value)),
            0,
            canvas_width_px,
            self.page_height_px
        )

        for index, page in enumerate(self.pages):
            page.setGeometry(
                index * self.page_width_px,
                0,
                self.page_width_px,
                self.page_height_px
            )

    def count(self) -> int:
        return len(self.pages)

    def index_of(self, widget: QWidget) -> int:
        if widget not in self.pages:
            return -1

        return self.pages.index(widget)

    # Events

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.update_canvas_geometry()

# Settings Window

class SettingsWindow(FloatingWindowGPU):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "Settings",
            parent                     = parent,
            max_tilt_angle             = 10,
            enable_audioplayer_effects = False
        )

        self.settings         = QSettings("chips047", "Cassette")
        self.pages            = {}
        self.controls         = {}
        self.value_getters    = {}
        self.max_scroll_width = 0

        self.page_selector    = None
        self.page_track       = AnimatedPageTrack(self)
        self.ok_button        = Widgets.NothingButton("Apply!")
        self.cancel_button    = Widgets.ButtonWithOutline("Cancel")

        self.title_label.setFont(Utils.NType(21))

        self.build_layout()
        self.connect_signals()

    # Setup

    def build_layout(self) -> None:
        button_row = QHBoxLayout()
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.ok_button)

        self.content_layout.addWidget(self.page_track)
        self.content_layout.addLayout(button_row)

    def connect_signals(self) -> None:
        self.ok_button.clicked.connect(self.apply_and_close)
        self.cancel_button.clicked.connect(self.on_cancel)

    def setup_page_selector(self, page_names: list[str]) -> None:
        if self.page_selector is not None:
            self.content_layout.removeWidget(self.page_selector)
            self.page_selector.deleteLater()

        self.page_selector = Widgets.Selector(page_names, default_index = 0)
        self.page_selector.setFont(Utils.NType(10))
        self.page_selector.selectionChanged.connect(self.on_page_selection_changed)

        self.content_layout.insertWidget(1, self.page_selector)

    # Navigation

    def on_page_selection_changed(
            self,
            index: int,
            title: str
        ) -> None:

        self.change_page(index)

    def change_page(self, target: int | QWidget) -> None:
        if isinstance(target, QWidget):
            target_index = self.page_track.index_of(target)

        else:
            target_index = target

        if target_index < 0:
            return

        self.page_track.slide_to_index(target_index)

        if self.page_selector is None:
            return

        if self.page_selector.current_index() != target_index:
            self.page_selector.set_current_index(target_index)

    # Pages

    def initialize_settings(self, setting_components: dict[str, list[dict[str, object]]]) -> None:
        page_names = list(setting_components.keys())

        if not page_names:
            return

        self.setup_page_selector(page_names)

        scroll_areas = []

        for page_name, components in setting_components.items():
            self.create_page(page_name, components, scroll_areas)

        self.apply_uniform_width(scroll_areas)

        if self.page_track.count() > 0:
            self.change_page(0)

    def create_page(
            self,
            page_name:    str,
            components:   list[dict[str, object]],
            scroll_areas: list[Widgets.ElasticScrollArea]
        ) -> Widgets.ElasticScrollArea:

        page_area = Widgets.ElasticScrollArea(self, Styles.Colors.Floating.Background)
        page_area.setFixedHeight(360)

        self.pages[page_name] = page_area

        for component_configuration in components:
            key        = str(component_configuration["key"])
            type_name  = str(component_configuration.get("type", ""))
            entry_pair = SETTING_WIDGET_REGISTRY.get(type_name)

            if not entry_pair:
                logger.warning(f"Unsupported setting type: {type_name}")
                continue

            factory, getter = entry_pair
            saved_value     = self.settings.value(key)
            widget          = factory(saved_value, component_configuration)

            if not widget:
                continue

            page_area.add_widget(widget)
            self.controls[key]      = widget
            self.value_getters[key] = getter

        self.page_track.add_page(page_area)
        scroll_areas.append(page_area)

        return page_area

    def apply_uniform_width(self, scroll_areas: list[Widgets.ElasticScrollArea]) -> None:
        for scroll_area in scroll_areas:
            required_width_px = scroll_area.get_required_width()

            if required_width_px > self.max_scroll_width:
                self.max_scroll_width = required_width_px

        for scroll_area in scroll_areas:
            scroll_area.setFixedWidth(self.max_scroll_width)

        self.page_track.set_page_width(self.max_scroll_width)

    # Actions

    def apply_and_close(self) -> None:
        for key, widget in self.controls.items():
            self.save_widget_value(key, widget)

        self.settings.sync()
        Constants.load_settings()

        self.on_ok()

    def save_widget_value(
            self,
            key:    str,
            widget: QWidget
        ) -> None:

        getter = self.value_getters.get(key)

        if not getter:
            return

        self.settings.setValue(key, getter(widget))