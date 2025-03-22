import logging
import time

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

    def get_all_conversations(self, progress_callback=None):
        offset = 0
        #ограничение API - 200 диалогов в запрос
        count = 200
        total = self._get_total_conversations()
        processed = 0

        while True:
            response = self.vk.messages.getConversations(
                count=count,
                offset=offset
            )
            items = response.get('items', [])

            for i, conv in enumerate(items):
                self.all_conversations.append(conv)
                title = self.get_conversation_title(conv)
                self.conversations_label.append(title)

                processed += 1
                if progress_callback:
                    current_progress = int((processed / total) * 100)
                    previous_progress = int(((processed - 1) / total) * 100)

                    for p in range(previous_progress, current_progress + 1):
                        progress_callback(p)
                        time.sleep(0.02)

            if len(items) < count:
                break

            offset += count
            time.sleep(0.5)

        if progress_callback:
            for p in range(95, 101):
                progress_callback(p)
                time.sleep(0.05)

    def _get_total_conversations(self):
        response = self.vk.messages.getConversations(count=0)
        total = response['count']
        return total

    def get_conversation_title(self, conversation):
        peer_id = conversation['conversation']['peer']['id']
        try:
            if peer_id >= 2000000000:
                chat_id = peer_id - 2000000000
                try:
                    chat = self.vk.messages.getChat(chat_id=chat_id)
                    return chat.get('title', f"Беседа {chat_id}")
                except ApiError as e:
                    if e.code == 15:
                        logger.warning(f"Нет доступа к чату {chat_id}")
                        return f"Недоступный чат {chat_id}"
                    raise
            elif peer_id > 0:
                users = self.vk.users.get(
                    user_ids=peer_id,
                    fields="first_name,last_name",
                    lang="ru"
                )
                if not users:
                    return f"Пользователь удалён (ID {peer_id})"
                return f"{users[0].get('first_name', '')} {users[0].get('last_name', '')}".strip()
            else:
                group_id = abs(peer_id)
                group = self.vk.groups.getById(group_id=group_id)
                return group[0].get('name', f"Сообщество {group_id}")

        except Exception as e:
            logger.error(f"Ошибка для peer_id {peer_id}: {str(e)}")
            return f"Ошибка получения названия"

    def get_media_in_selected_chat(self, selected_chat):
        for dialog in self.all_conversations:
            messages = self.vk.getHistory()

        logger.info(self.get_dialogs_title(self.all_conversations[20]))
        # for conversation in self.all_conversations:
        #     logger.info(self.get_dialogs_title(conversation))
        #     break

token='vk1.a.rvexKkC_nM4msTKREP9dllke-0NBRSxUT8McIW4fg0mjT6saxwvQGuhtsT4nrlBH_IUCDgBLtdlRudirQWoQCuDI6BLP0D-_AJXaGFq87gA7OAOFMPp6oFR0RnQKrT872H4LNnABzIypoE8hutV6sFPkIIUKO_pEQF0HUhn9cCq2qeW_cUhhC2s8_XZqrFgHhEnF7WzSNlBrZoRm-uxxHQ'

def main():
    app = AppSaver(token)
    app.get_all_conversations()
    app.get_media()

if __name__ == '__main__':
    main()
