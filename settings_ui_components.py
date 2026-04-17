#(вспомогательный модуль)
from PyQt6.QtWidgets import QPushButton, QLineEdit, QCheckBox

def apply_modern_style(widget):
    widget.setStyleSheet("""
        QPushButton {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #3f3f3f;
            padding: 8px 15px;
            border-radius: 2px;
        }
        QPushButton:hover {
            background-color: #3d3d3d;
            border: 1px solid #0078d4;
        }
        QLineEdit {
            background-color: #1a1a1a;
            color: #eeeeee;
            border: 1px solid #333333;
            padding: 5px;
            selection-background-color: #0078d4;
        }
        QCheckBox {
            color: #cccccc;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            background-color: #1a1a1a;
            border: 1px solid #333333;
        }
        QCheckBox::indicator:checked {
            background-color: #0078d4;
        }
    """)
