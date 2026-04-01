"""QC Rack Tracking System — PyQt6 desktop application entry point."""
import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from PyQt6.QtGui import QFont

import database
from ok_tab import OKTab
from th_tab import THTab
from lookup_tab import LookupTab
from settings_tab import SettingsTab

STYLESHEET = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Segoe UI", Arial, sans-serif;
}

QTabWidget::pane {
    border: 1px solid #45475a;
    background-color: #1e1e2e;
}
QTabBar::tab {
    background-color: #313244;
    color: #cdd6f4;
    padding: 9px 28px;
    font-size: 13px;
    font-weight: bold;
    border: 1px solid #45475a;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #89b4fa;
    color: #1e1e2e;
}
QTabBar::tab:hover:!selected {
    background-color: #45475a;
}

QLineEdit, QSpinBox {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 4px;
    padding: 4px 8px;
    selection-background-color: #585b70;
}
QLineEdit:focus, QSpinBox:focus {
    border: 2px solid #89b4fa;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #45475a;
    border: none;
    width: 20px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #585b70;
}

QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 5px;
    padding: 6px 16px;
}
QPushButton:hover   { background-color: #45475a; }
QPushButton:pressed { background-color: #585b70; }
QPushButton:disabled {
    background-color: #1e1e2e;
    color: #585b70;
    border-color: #313244;
}

QTableWidget {
    background-color: #181825;
    color: #cdd6f4;
    gridline-color: #313244;
    border: 1px solid #45475a;
    selection-background-color: #585b70;
    alternate-background-color: #1e1e2e;
}
QTableWidget::item { padding: 4px 8px; }
QHeaderView::section {
    background-color: #313244;
    color: #89b4fa;
    padding: 6px;
    border: none;
    border-right: 1px solid #45475a;
    font-weight: bold;
}

QScrollBar:vertical {
    background-color: #313244;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #585b70;
    border-radius: 5px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background-color: #6c7086; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background-color: #313244;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background-color: #585b70;
    border-radius: 5px;
}

QMessageBox { background-color: #1e1e2e; }
QMessageBox QLabel { color: #cdd6f4; }
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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
