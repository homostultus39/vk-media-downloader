import os
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


class DownloadThread(QThread):
    progress_updated = Signal(int)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, token, dialogs, save_path):
        super().__init__()
        self.token = token
        self.dialogs = dialogs
        self.save_path = save_path
        self._is_running = True

    def run(self):
        try:
            downloader = AppSaver(token=self.token)
            total = len(self.dialogs)

            for i, dialog_data in enumerate(self.dialogs):
                if not self._is_running:
                    break

                self.progress_updated.emit(int((i / total) * 100))
                peer_id = dialog_data['peer_id']

                media = downloader.get_media(peer_id)
                valid_media = [m for m in media if m is not None]

                folder_name = self.sanitize_folder_name(dialog_data['title'])
                final_save_path = os.path.join(self.save_path, folder_name)
                os.makedirs(final_save_path, exist_ok=True)

                for item in valid_media:
                    if not self._is_running:
                        break

                    filename = f"{item['id']}.{'jpg' if item['type'] == 'photo' else 'mp4'}"
                    path = os.path.join(final_save_path, filename)
                    downloader.download_file(item['url'], path, item['date'])

            self.finished.emit() if self._is_running else None

        except Exception as e:
            self.error_occurred.emit(str(e))

    def sanitize_folder_name(self, name):
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()

    def stop(self):
        self._is_running = False