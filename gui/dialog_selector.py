from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QListWidget, QListWidgetItem, QCheckBox

from gui.styles import APP_STYLE


class DialogSelectorDialog(QDialog):
    def __init__(self, dialog_labels, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выбор диалогов")
        self.setFixedSize(400, 500)
        self.setStyleSheet(APP_STYLE)

        layout = QVBoxLayout()

        self.btn_toggle_all = QPushButton("Выбрать все")
        self.btn_toggle_all.clicked.connect(self.toggle_all_selection)
        layout.addWidget(self.btn_toggle_all)

        self.list_widget = QListWidget()
        for label in dialog_labels:
            item = QListWidgetItem()
            check = QCheckBox(label)
            check.setChecked(True)
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, check)

        layout.addWidget(self.list_widget)

        self.btn_confirm = QPushButton("Начать загрузку")
        self.btn_confirm.clicked.connect(self.accept)
        layout.addWidget(self.btn_confirm)

        self.setLayout(layout)

    def toggle_all_selection(self):
        """Переключает состояние всех чекбоксов"""
        new_state = self.btn_toggle_all.text() == "Выбрать все"
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            widget.setChecked(new_state)

        self.btn_toggle_all.setText("Снять все" if new_state else "Выбрать все")

    def get_selected_labels(self):
        """Возвращает список выбранных меток"""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget.isChecked():
                selected.append(widget.text())
        return selected