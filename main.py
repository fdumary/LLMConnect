import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

QSS = """
QWidget {
    background-color: #0a0a0a;
    color: #f5f5f5;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 14px;
}

QDialog {
    background-color: #111111;
}

QLabel {
    color: #f5f5f5;
}

QToolButton {
    background-color: transparent;
    color: #f5f5f5;
    border: 1px solid #262626;
    border-radius: 12px;
}

QToolButton:hover {
    background-color: #1a1a1a;
    border-color: #333333;
}

QToolButton:pressed {
    background-color: #202020;
}

QTabWidget::pane {
    border: 1px solid #262626;
    border-radius: 16px;
    background: #111111;
}

QTabBar::tab {
    background: #111111;
    color: #a3a3a3;
    padding: 10px 18px;
    border: 1px solid #262626;
    border-bottom: none;
    border-top-left-radius: 12px;
    border-top-right-radius: 12px;
    margin-right: 6px;
}
QTabBar::tab:selected {
    background: #191919;
    color: #f5f5f5;
    border-color: #333333;
}
QTabBar::tab:hover:!selected {
    background: #171717;
    color: #f5f5f5;
}

QTabBar::close-button {
    image: url(icons/close.svg);
    background: transparent;
    margin-right: 8px;
}
QTabBar::close-button:hover {
    background: #2a2a2a;
    border-radius: 999px;
}

QPushButton {
    background-color: #1f1f1f;
    color: #f5f5f5;
    border: 1px solid #262626;
    border-radius: 12px;
    padding: 9px 16px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #252525;
    border-color: #333333;
}
QPushButton:pressed {
    background-color: #2a2a2a;
}

QTextEdit, QListWidget, QComboBox, QLineEdit {
    background-color: #141414;
    border: 1px solid #262626;
    border-radius: 12px;
    padding: 8px;
    color: #f5f5f5;
}

QScrollBar:vertical {
    border: none;
    background: #111111;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #303030;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background: #3a3a3a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
