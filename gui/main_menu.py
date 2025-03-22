import sys
import time
import webbrowser
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                               QPushButton, QLineEdit, QLabel, QProgressBar,
                               QFileDialog, QMessageBox, QDialog, QHBoxLayout)
from PySide6.QtGui import QIcon, QFont
from PySide6.QtCore import Qt, QSize

from gui.dialog_selector import DialogSelectorDialog
from gui.styles import FOLDER_LBL_STYLE_PICK, FOLDER_LBL_STYLE_ERR, ICON, FOLDER_ICON
from styles import APP_STYLE, BTN_STYLE
from gui.worker import ConversationThread


class MediaSaverApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.setStyleSheet(APP_STYLE)
        self.dialogs = []
        self.selected_dialogs = []
        self.save_path = ""

    def initUI(self):
        self.setWindowTitle('VK Media Downloader')
        self.setMinimumSize(400, 300)
        self.setWindowIcon(QIcon(ICON))  # Добавьте свою иконку

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title = QLabel('VK Media Downloader')
        title.setFont(QFont('Segoe UI', 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText('Введите ваш VK токен')
        self.token_input.setClearButtonEnabled(True)

        self.btn_folder = QPushButton('Выбрать папку')
        self.btn_folder.setIcon(QIcon(FOLDER_ICON))
        self.btn_folder.setIconSize(QSize(20, 20))
        self.btn_folder.clicked.connect(self.choose_folder)

        self.folder_label = QLabel('Папка не выбрана')
        self.folder_label.setWordWrap(True)
        self.folder_label.setStyleSheet(FOLDER_LBL_STYLE_ERR)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)

        self.btn_choose_dialog = QPushButton('Выбрать диалог')
        self.btn_choose_dialog.clicked.connect(self.show_dialog_selector)
        self.btn_choose_dialog.setStyleSheet(BTN_STYLE)


        self.btn_instruction = QPushButton('Инструкция')
        self.btn_instruction.clicked.connect(self.open_instruction)
        self.btn_choose_dialog.setStyleSheet(BTN_STYLE)

        main_layout.addWidget(title)
        main_layout.addWidget(self.token_input)
        main_layout.addWidget(self.btn_folder)
        main_layout.addWidget(self.folder_label)
        simple_builder = QHBoxLayout()
        simple_builder.addWidget(self.btn_instruction, stretch=1)
        simple_builder.addWidget(self.btn_choose_dialog, stretch=2)
        main_layout.addLayout(simple_builder)
        main_layout.addStretch(1)
        main_layout.addWidget(self.progress)
        self.setLayout(main_layout)

    def open_instruction(self):
        webbrowser.open_new('https://github.com/homostultus39/vk-media-saver')

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            'Выберите папку для сохранения',
            options=QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.save_path = folder
            self.folder_label.setText(f'Выбрано: {folder}')
            self.folder_label.setStyleSheet(FOLDER_LBL_STYLE_PICK)

    def show_dialog_selector(self):
        token = self.token_input.text()

        if not token or not self.save_path:
            self.show_error('Сначала введите токен и выберите папку!')
            return

        self.progress.setValue(0)
        self.progress.setVisible(True)

        self.thread = ConversationThread(token)
        self.thread.progress_updated.connect(self._update_progress)
        self.thread.finished.connect(self._handle_dialogs_loaded)
        self.thread.error_occurred.connect(self._handle_dialogs_error)
        self.thread.start()

    def _update_progress(self, value):
        current_value = self.progress.value()
        step = 1 if value > current_value else -1

        while current_value != value:
            current_value += step
            self.progress.setValue(current_value)
            QApplication.processEvents()
            time.sleep(0.005)

    def _handle_dialogs_loaded(self, labels):
        self.progress.setValue(100)

        dialog = DialogSelectorDialog(labels, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_dialogs = dialog.get_selected_labels()
            self.start_download()

    def _handle_dialogs_error(self, error_msg):
        self.progress.setVisible(False)
        self.show_error(error_msg)

    def start_download(self):

        try:
            total = len(self.selected_dialogs)
            for i, peer_id in enumerate(self.selected_dialogs):
                self.progress.setValue(int((i / total) * 100))
                
                # 1. Получение сообщений из диалога
                # messages = vk.method("messages.getHistory", {...})

                # 2. Парсинг вложений
                # for msg in messages:
                #     обработка attachments

                # 3. Скачивание файлов с сохранением метаданных
                # download_media(url, path, dialog_id)

                # 4. Обновление прогресс-бара

            self.show_success('Загрузка завершена!')
        except Exception as e:
            self.show_error(f"Ошибка загрузки: {str(e)}")


    def show_error(self, text):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle('Ошибка')
        msg.setFixedSize(400, 300)
        msg.setText(text)
        msg.setStyleSheet(APP_STYLE)
        msg.exec()

    def show_success(self, text):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle('Успешно')
        msg.setText(text)
        msg.setStyleSheet(APP_STYLE)
        msg.exec()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MediaSaverApp()
    window.show()
    sys.exit(app.exec())