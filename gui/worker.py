from PySide6.QtCore import QThread, Signal

from scripts.parse_vk_dialogs import AppSaver


class ConversationThread(QThread):
    progress_updated = Signal(int)
    finished = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, token):
        super().__init__()
        self.token = token

    def run(self):
        try:
            app = AppSaver(self.token)
            app.get_all_conversations(
                progress_callback=lambda p: self.progress_updated.emit(p)
            )
            filtered_labels = [l for l in app.conversations_label if "Недоступный" not in l]
            self.finished.emit(filtered_labels)

        except Exception as e:
            self.error_occurred.emit(str(e))