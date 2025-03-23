import logging
import time
import yt_dlp
import piexif
import requests
import datetime
from PIL import Image
from mutagen.mp4 import MP4
from vk_api import vk_api, ApiError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class AppSaver:
    def __init__(self, token):
        vk_session = vk_api.VkApi(token=token)
        self.vk = vk_session.get_api()
        self.all_conversations = []
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
            response = self.vk.messages.getConversations(
                count=count,
                offset=offset
            )
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
            time.sleep(0.5)

        return self.conversations_label

    def _get_total_conversations(self):
        response = self.vk.messages.getConversations(count=0)
        total = response['count']
        return total

    def get_conversation_title(self, conversation):
        peer_id = conversation['conversation']['peer']['id']
        result = {
            'title': "Ошибка",
            'peer_id': peer_id
        }
        try:
            if peer_id >= 2000000000:
                chat_id = peer_id - 2000000000
                try:
                    chat = self.vk.messages.getChat(chat_id=chat_id)
                    result['title'] = chat.get('title', f"Беседа {chat_id}")
                except ApiError as e:
                    if e.code == 15:
                        result['title'] = f"Недоступный чат {chat_id}"
                    else:
                        result['title'] = f"Ошибка чата {chat_id}"
            elif peer_id > 0:
                users = self.vk.users.get(
                    user_ids=peer_id,
                    fields="first_name,last_name",
                    lang="ru"
                )
                result[
                    'title'] = f"{users[0]['first_name']} {users[0]['last_name']}" if users else f"Пользователь {peer_id}"
            else:
                group_id = abs(peer_id)
                group = self.vk.groups.getById(group_id=group_id)
                result['title'] = group[0].get('name', f"Сообщество {group_id}")
        except Exception as e:
            logger.error(f"Ошибка для peer_id {peer_id}: {str(e)}")
            result['title'] = f"Ошибка получения названия"
        return result

    def get_media(self, peer_id):
        media = []
        offset = 0
        count = 200

        while True:
            response = self.vk.messages.getHistory(
                peer_id=peer_id,
                offset=offset,
                count=count,
                extended=0
            )

            for msg in response['items']:
                media.extend(self._parse_attachments(msg))

            if len(response['items']) < count:
                break

            offset += count
            time.sleep(0.5)

        return media

    def _parse_attachments(self, message):
        attachments = []

        for attach in message.get('attachments', []):
            handler = self.media_types.get(attach['type'])
            if handler:
                result = handler(attach[attach['type']])
                if result:
                    attachments.append(result)

        for fwd_msg in message.get('fwd_messages', []):
            attachments.extend(self._parse_attachments(fwd_msg))

        return attachments

    def _process_photo(self, photo):
        sizes = photo.get('sizes', [])
        max_size = max(sizes, key=lambda x: x['width']) if sizes else {}
        return {
            'type': 'photo',
            'url': max_size.get('url'),
            'date': photo.get('date'),
            'id': f"photo{photo['owner_id']}_{photo['id']}"
        }

    def _process_video(self, video):
        try:
            if video.get('platform') is None:
                video_url = f"https://vk.com/video{video['owner_id']}_{video['id']}"

                return {
                    'type': 'video',
                    'url': video_url,
                    'title': video.get('title'),
                    'date': video.get('date'),
                    'id': f"video{video['owner_id']}_{video['id']}"
                }
            return None
        except Exception as e:
            logger.error(f"Ошибка обработки видео: {str(e)}")
            return None

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

    def download_file(self, url, path, item_date=None):
        try:
            if not self._download_file(url, path):
                return False

            if item_date:
                if path.lower().endswith(('.jpg', '.jpeg')):
                    self._add_photo_metadata(path, item_date)
                elif path.lower().endswith('.mp4'):
                    self._add_video_metadata(path, item_date)

            return True

        except Exception as e:
            logger.error(f"Критическая ошибка при обработке файла: {str(e)}")
            return False

    def _download_file(self, url, path):
        if not url:
            return False

        try:
            if 'video' in url:
                self.ydl_opts['outtmpl'] = path.replace('.mp4', '') + '.%(ext)s'
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    ydl.download([url])
                return True
            else:
                response = requests.get(url, stream=True)
                with open(path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except Exception as e:
            logger.error(f"Ошибка скачивания {url}: {str(e)}")
            return False

