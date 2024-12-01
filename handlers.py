
import logging
from aiotdlib import Client
from aiotdlib.api import API, UpdateNewMessage, UpdateNewChat, UpdateChatPosition, Messages
import tgdump

async def on_update_new_message(client: Client, update: UpdateNewMessage):
    logging.info('on_update_new_message handler called')

async def on_new_chat(client: Client, update: UpdateNewChat):
    print(f"Новый чат добавлен: {update.chat.title}, id: {update.chat.id}")
    tgdump.add_chat(update.chat.id, 
                    update.chat.title)

def register_handlers(client: Client):
    client.add_event_handler(on_update_new_message, update_type=API.Types.UPDATE_NEW_MESSAGE)
    client.add_event_handler(on_new_chat, update_type=API.Types.UPDATE_NEW_CHAT)