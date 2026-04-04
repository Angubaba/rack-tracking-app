"""QC Rack Tracking System — PyQt6 desktop application entry point."""
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt5.QtGui import QFont

import database
from ok_tab import OKTab
from th_tab import THTab
from lookup_tab import LookupTab
from settings_tab import SettingsTab

STYLESHEET = """
QWidget {
    background-color: #f8f9fa;
    color: #212529;
    font-family: "Segoe UI", Arial, sans-serif;
}

QTabWidget::pane {
    border: 1px solid #dee2e6;
    background-color: #f8f9fa;
}
QTabBar::tab {
    background-color: #e9ecef;
    color: #495057;
    padding: 9px 28px;
    font-size: 13px;
    font-weight: bold;
    border: 1px solid #dee2e6;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #1971c2;
    color: #ffffff;
}
QTabBar::tab:hover:!selected {
    background-color: #dee2e6;
}

QLineEdit, QSpinBox {
    background-color: #ffffff;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #a5d8ff;
}
QLineEdit:focus, QSpinBox:focus {
    border: 2px solid #1971c2;
}
QLineEdit:read-only {
    background-color: #e7f5ff;
    color: #1864ab;
    border-color: #a5d8ff;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #e9ecef;
    border: none;
    width: 20px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #dee2e6;
}

QPushButton {
    background-color: #e9ecef;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 5px;
    padding: 6px 16px;
}
QPushButton:hover   { background-color: #dee2e6; }
QPushButton:pressed { background-color: #ced4da; }
QPushButton:disabled {
    background-color: #f8f9fa;
    color: #adb5bd;
    border-color: #e9ecef;
}

QTableWidget {
    background-color: #ffffff;
    color: #212529;
    gridline-color: #dee2e6;
    border: 1px solid #dee2e6;
    selection-background-color: #a5d8ff;
    alternate-background-color: #f8f9fa;
}
QTableWidget::item { padding: 4px 8px; }
QHeaderView::section {
    background-color: #e9ecef;
    color: #1971c2;
    padding: 6px;
    border: none;
    border-right: 1px solid #dee2e6;
    border-bottom: 1px solid #dee2e6;
    font-weight: bold;
}

QScrollBar:vertical {
    background-color: #f1f3f5;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #ced4da;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background-color: #adb5bd; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background-color: #f1f3f5;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background-color: #ced4da;
    border-radius: 5px;
}

QMessageBox { background-color: #ffffff; }
QMessageBox QLabel { color: #212529; }
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QC Rack Tracking System")
        self.setMinimumSize(960, 700)

        self._tabs = QTabWidget()
        self._ok_tab       = OKTab()
        self._th_tab       = THTab()
        self._lookup_tab   = LookupTab()
        self._settings_tab = SettingsTab()

        self._tabs.addTab(self._ok_tab,       "  OK RACKS  ")
        self._tabs.addTab(self._th_tab,       "  GOING TO TH  ")
        self._tabs.addTab(self._lookup_tab,   "  LOOKUP  ")
        self._tabs.addTab(self._settings_tab, "  SETTINGS  ")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)

    def _on_tab_changed(self, index: int):
        tab = self._tabs.widget(index)
        if hasattr(tab, "on_activate"):
            tab.on_activate()
        elif index == 2:
            self._lookup_tab.search_input.setFocus()

    def showEvent(self, event):
        super().showEvent(event)
        self._ok_tab.on_activate()


def main():
    database.init_db()

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setFont(QFont("Segoe UI", 11))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
