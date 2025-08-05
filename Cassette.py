try:
    import os
    import sys
    import subprocess

    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
    
    from System import Styles

except ModuleNotFoundError as e:
    from System import Utils

os.chdir(os.path.dirname(os.path.abspath(__file__)))

app = QApplication(sys.argv)
from System import Utils
app.setWindowIcon(Utils.Icons.WindowIcon)

from System.ProjectMenu import MainMenu
from System.Compositor import CompositorWidget

class ApplicationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cassette")
        self.resize(1280, 800)
        
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.main_menu_widget = MainMenu()
        self.compositor_widget = CompositorWidget()

        self.stack.addWidget(self.main_menu_widget)
        self.stack.addWidget(self.compositor_widget)

        self.main_menu_widget.composition_created.connect(self.show_compositor)
        self.compositor_widget.back_to_main_menu_requested.connect(self.hide_compositor_and_show_main_menu)

        self.stack.setCurrentWidget(self.main_menu_widget)
        self.setStyleSheet(f"background-color: {Styles.Colors.background};")
        self.center_window()

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def fade_out(self, widget):
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)

        self.anim_out = QPropertyAnimation(effect, b"opacity")
        self.anim_out.setDuration(300)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.OutCubic)
        return self.anim_out

    def fade_in(self, widget):
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)

        effect.setOpacity(0.0) 
        
        self.anim_in = QPropertyAnimation(effect, b"opacity")
        self.anim_in.setDuration(400)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.InCubic)
        return self.anim_in

    @pyqtSlot(object)
    def show_compositor(self, composition):
        self.compositor_widget.initialize_compositor(composition.cropped_audiofile_path, composition)
        initial_compositor_geometry = self.stack.geometry()
        offset_y = 200

        self.compositor_widget.setGeometry(initial_compositor_geometry.x(), initial_compositor_geometry.y() + offset_y, initial_compositor_geometry.width(), initial_compositor_geometry.height())
        anim_out = self.fade_out(self.main_menu_widget)

        def on_fade_out_finished():
            Utils.ui_sound("Eject")
            self.stack.setCurrentWidget(self.compositor_widget)
            target_geometry = self.stack.geometry() 

            self.anim_move = QPropertyAnimation(self.compositor_widget, b"geometry")
            self.anim_move.setDuration(700)
            self.anim_move.setStartValue(QRect(initial_compositor_geometry.x(), initial_compositor_geometry.y() + offset_y, initial_compositor_geometry.width(), initial_compositor_geometry.height()))

            self.anim_move.setEndValue(target_geometry) 
            self.anim_move.setEasingCurve(QEasingCurve.OutElastic)

            anim_in = self.fade_in(self.compositor_widget)
            anim_in.start()
            self.anim_move.start(QAbstractAnimation.DeleteWhenStopped)

        anim_out.finished.connect(on_fade_out_finished)
        anim_out.start(QAbstractAnimation.DeleteWhenStopped)
    
    @pyqtSlot()
    def hide_compositor_and_show_main_menu(self):
        anim_out_compositor = self.fade_out(self.compositor_widget)

        def on_fade_out_compositor_finished():
            Utils.ui_sound("Eject")
            self.stack.setCurrentWidget(self.main_menu_widget)

            initial_main_menu_geometry = self.stack.geometry()
            offset_y = 200

            self.main_menu_widget.setGeometry(
                initial_main_menu_geometry.x(),
                initial_main_menu_geometry.y() + offset_y,
                initial_main_menu_geometry.width(),
                initial_main_menu_geometry.height()
            )

            self.anim_move_main_menu = QPropertyAnimation(self.main_menu_widget, b"geometry")
            self.anim_move_main_menu.setDuration(700)
            self.anim_move_main_menu.setStartValue(
                QRect(initial_main_menu_geometry.x(), initial_main_menu_geometry.y() + offset_y,
                      initial_main_menu_geometry.width(), initial_main_menu_geometry.height())
            )
            self.anim_move_main_menu.setEndValue(initial_main_menu_geometry)
            self.anim_move_main_menu.setEasingCurve(QEasingCurve.OutElastic)

            anim_in_main_menu = self.fade_in(self.main_menu_widget)
            anim_in_main_menu.start()
            self.anim_move_main_menu.start(QAbstractAnimation.DeleteWhenStopped)

        anim_out_compositor.finished.connect(on_fade_out_compositor_finished)
        anim_out_compositor.start(QAbstractAnimation.DeleteWhenStopped)
    
    def closeEvent(self, event):
        self.compositor_widget.closeEvent(event)

        subprocess.Popen([
            sys.executable, '-c',
            'import pygame, time; pygame.mixer.init(); s=pygame.mixer.Sound("System/UI/Close.wav"); s.play(); time.sleep(s.get_length());'
        ])

        super().closeEvent(event)

if __name__ == '__main__':
    if os.path.exists("System/Fonts/NDot57.otf"):
        QFontDatabase.addApplicationFont("System/Fonts/NDot57.otf")
    
    if os.path.exists("System/Fonts/NType82.otf"):
        QFontDatabase.addApplicationFont("System/Fonts/NType82.otf")

    main_window = ApplicationWindow()
    main_window.show()
    
    Utils.ui_sound("Start")

    sys.exit(app.exec_())