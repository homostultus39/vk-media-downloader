import logging
import sys
import os
import time
import requests
import datetime
import piexif
from PIL import Image
from mutagen.mp4 import MP4
import yt_dlp
from vk_api import vk_api, ApiError

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class AppSaver:
    def __init__(self, token):

        self.token = token
        vk_session = vk_api.VkApi(token=token)
        self.vk = vk_session.get_api()
        self.conversations_label = []

        self.media_types = {
            'photo': self._process_photo,
            'video': self._process_video
        }

        self.ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
        }


    def get_all_conversations(self, progress_callback=None):
        offset = 0
        count = 200
        total = self._get_total_conversations()
        processed = 0

        self.conversations_label = []

        while True:
            response = self.vk.messages.getConversations(count=count, offset=offset)
            items = response.get('items', [])

            for conv in items:
                dialog_data = self.get_conversation_title(conv)
                self.conversations_label.append(dialog_data)
                processed += 1

                if progress_callback:
                    progress = int((processed / total) * 100)
                    progress_callback(progress)

            if len(items) < count:
                break
            offset += count
            time.sleep(0.33)

        return self.conversations_label

    def _get_total_conversations(self):
        response = self.vk.messages.getConversations(count=0)
        return response['count']

    def get_conversation_title(self, conversation):
        peer_id = conversation['conversation']['peer']['id']
        result = {
            'title': "Ошибка",
            'peer_id': peer_id
        }
        try:
            if peer_id >= 2000000000:
                chat_id = peer_id - 2000000000
                chat = self.vk.messages.getChat(chat_id=chat_id)
                result['title'] = chat.get('title', f"Беседа {chat_id}")

            elif peer_id > 0:
                users = self.vk.users.get(
                    user_ids=peer_id,
                    fields="first_name,last_name",
                    lang="ru"
                )
                if users:
                    result['title'] = f"{users[0]['first_name']} {users[0]['last_name']}"
                else:
                    result['title'] = f"Пользователь {peer_id}"

            else:
                group_id = abs(peer_id)
                group = self.vk.groups.getById(group_id=group_id)
                result['title'] = group[0].get('name', f"Сообщество {group_id}")

        except ApiError as e:
            logger.error(f"Ошибка для peer_id {peer_id}: {str(e)}")
            result['title'] = f"Ошибка"
        except Exception as e:
            logger.error(f"Непредвиденная ошибка для peer_id {peer_id}: {e}")
            result['title'] = f"Ошибка"
        return result

    def get_media(self, peer_id):
        """
        Возвращает список аттачей (фото / видео / ...).
        ВАЖНО: используем extended=1, чтобы у видео мог быть access_key.
        """
        media = []
        offset = 0
        count = 200

        while True:
            response = self.vk.messages.getHistory(
                peer_id=peer_id,
                offset=offset,
                count=count,
                extended=1
            )

            items = response.get('items', [])
            for msg in items:
                media.extend(self._parse_attachments(msg))

            if len(items) < count:
                break

            offset += count
            time.sleep(0.33)

        return media

    def _parse_attachments(self, message):
        attachments = []

        for attach in message.get('attachments', []):
            attach_type = attach.get('type')
            handler = self.media_types.get(attach_type)
            if not handler:
                continue
            data = attach[attach_type]
            result = handler(data)
            if result:
                attachments.append(result)

        for fwd_msg in message.get('fwd_messages', []):
            attachments.extend(self._parse_attachments(fwd_msg))

        return attachments

    def _process_photo(self, photo):
        sizes = photo.get('sizes', [])
        if not sizes:
            return None
        best = max(sizes, key=lambda s: s['width'])

        return {
            'type': 'photo',
            'url': best.get('url'),
            'date': photo.get('date'),
            'id': f"photo{photo['owner_id']}_{photo['id']}"
        }

    def _process_video(self, video):
        try:
            if video.get('platform') is not None:
                return None

            owner_id = video['owner_id']
            video_id = video['id']
            upload_ts = video.get('date')
            access_key = video.get('access_key')

            # Пытаемся вытащить прямую ссылку (mobile=1)
            direct_url = None
            if access_key:
                direct_url = self._download_private_video(owner_id, video_id, access_key)
            else:
                logger.debug(f"У видео {owner_id}_{video_id} нет access_key, возможно, публичное или слишком приватное.")

            # Если не удалось добыть прямой URL, дадим fallback ссылку (обычно не скачивается)

            final_url = direct_url or f"https://vk.com/video{owner_id}_{video_id}"

            return {
                'type': 'video',
                'url': final_url,
                'title': video.get('title', ''),
                'date': upload_ts,
                'id': f"video{owner_id}_{video_id}"
            }

        except Exception as e:
            logger.error(f"Ошибка обработки видео: {e}")
            return None

    def _download_private_video(self, owner_id, video_id, access_key):
        try:
            logger.debug(f"_download_private_video: {owner_id}_{video_id}_{access_key}")
            resp = requests.get(
                "https://api.vk.com/method/video.get",
                params={
                    'access_token': self.token,
                    'v': '5.131',
                    'videos': f"{owner_id}_{video_id}_{access_key}",
                    'mobile': 1
                },
                timeout=10
            )
            data = resp.json()

            if 'error' in data:
                err = data['error']
                logger.warning(f"Ошибка mobile API: {err.get('error_code')} - {err.get('error_msg')}")
                return None

            items = data.get('response', {}).get('items', [])
            if not items:
                logger.warning("video.get (mobile=1) не вернул items. Нет доступа или видео удалено.")
                return None

            # Ищем ссылки в 'files'
            files_dict = items[0].get('files', {})

            direct_url = (files_dict.get('mp4_1080') or
                          files_dict.get('mp4_720') or
                          files_dict.get('mp4_480') or
                          files_dict.get('mp4_360') or
                          files_dict.get('mp4_240') or
                          files_dict.get('external'))
            if not direct_url:
                logger.warning("Поле files есть, но прямых ссылок не найдено.")
                return None
            logger.debug(f"hui nya {direct_url}")
            return direct_url

        except Exception as e:
            logger.exception(f"Исключение в _download_private_video: {e}")
            return None

    def download_file(self, url, path, item_date=None):
        try:
            if not url:
                return False

            if 'vk.com/video' in url:
                logger.warning(f"Прямая ссылка недоступна, пропускаем: {url}")
                return False

            if any(fmt in url for fmt in ('.mp4', '.m3u8')):
                self.ydl_opts['outtmpl'] = path.rsplit('.', 1)[0] + '.%(ext)s'
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    ydl.download([url])
            else:
                r = requests.get(url, stream=True)
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            if item_date:
                if path.lower().endswith(('.jpg', '.jpeg')):
                    self._add_photo_metadata(path, item_date)
                elif path.lower().endswith('.mp4'):
                    self._add_video_metadata(path, item_date)

                self._set_file_mtime(path, item_date)

            return True

        except Exception as e:
            logger.error(f"Ошибка при скачивании {url} -> {path}: {e}")
            return False

    def _add_video_metadata(self, file_path, create_date):
        try:
            video = MP4(file_path)
            date_iso = datetime.datetime.utcfromtimestamp(create_date).isoformat()

            video["\xa9day"] = [date_iso]
            video["\xa9too"] = ["VK Media Saver"]
            video["\xa9nam"] = ["Media from VK"]
            video["\xa9cmt"] = [f"Original VK upload date: {date_iso}"]
            video.save()

            logger.info(f"Метаданные видео успешно добавлены: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка записи метаданных видео: {str(e)}")
            return False

    def _set_file_mtime(self, file_path, timestamp):
        try:
            os.utime(file_path, (timestamp, timestamp))
        except Exception as e:
            logger.warning(f"Не удалось установить время файла: {e}")

    def _add_photo_metadata(self, file_path, create_date):
        try:
            date_str = datetime.datetime.utcfromtimestamp(create_date).strftime('%Y:%m:%d %H:%M:%S')

            exif_dict = {
                "0th": {
                    piexif.ImageIFD.DateTime: date_str,
                    piexif.ImageIFD.Software: "VK Media Saver",
                },
                "Exif": {
                    piexif.ExifIFD.DateTimeOriginal: date_str,
                    piexif.ExifIFD.DateTimeDigitized: date_str,
                },
                "GPS": {},
            }

            exif_bytes = piexif.dump(exif_dict)
            with Image.open(file_path) as img:
                img.save(file_path, exif=exif_bytes, quality=95)

            logger.info(f"EXIF-данные успешно добавлены: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Ошибка записи EXIF: {str(e)}")
            return False
