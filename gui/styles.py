import os

APP_STYLE = """
    QWidget {
        background-color: #2b2b2b;
        color: #ffffff;
        font-family: 'Segoe UI';
    }
    QPushButton {
        background-color: #3c3c3c;
        border: 1px solid #4a4a4a;
        border-radius: 4px;
        padding: 8px 16px;
        min-width: 100px;
    }
    QPushButton:hover {
        background-color: #4a4a4a;
    }
    QPushButton:pressed {
        background-color: #5a5a5a;
    }
    QLineEdit {
        background-color: #3c3c3c;
        border: 1px solid #4a4a4a;
        border-radius: 4px;
        padding: 6px;
    }
    QProgressBar {
        border: 1px solid #4a4a4a;
        border-radius: 4px;
        text-align: center;
        background-color: #3c3c3c;
    }
    QProgressBar::chunk {
        background-color: #4CAF50;
        width: 10px;
    }
"""

BTN_STYLE = """
    QPushButton {
        background-color: #5181B8;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #688EB8;
    }
"""

FOLDER_LBL_STYLE_PICK = "color: #4CAF50; font-size: 12px;"
FOLDER_LBL_STYLE_ERR = 'color: #F08080; font-size: 12px;'
#800
OR_LBL_STYLE = 'color: #0888; font-size: 12px;'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON = os.path.join(BASE_DIR, "assets", "icon.png")
FOLDER_ICON = os.path.join(BASE_DIR, "assets", "folder_icon.png")
