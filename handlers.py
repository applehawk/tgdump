import logging
from aiotdlib import Client
from aiotdlib.api import API, UpdateNewMessage, UpdateNewChat, UpdateChatPosition, Messages, MessageText, MessageSenderUser
import tgdump
from helpers import load_all_messages_backward, load_messages_day_by_day
from sbertprocessor import process_sentences

target_chat_id: int = None

async def get_message_history(client: Client, chat_id: int, l):
    await client.api.open_chat(chat_id)

    global target_chat_id
    target_chat_id = chat_id

    tgdump.drop_table_messages()
    tgdump.create_messages_if_not_exists()

    async for day_batch in load_messages_day_by_day(client, chat_id, 7):
        await process_sentences(day_batch)

#   async for batch in load_all_messages_backward(client, chat_id, max=200):
#        await process_sentences(batch)
#
#        for message in batch.messages:
#            if isinstance(message.sender_id, MessageSenderUser):
#                user = await client.api.get_user(message.sender_id.user_id)
#
#            if isinstance(message.content, MessageText):
#                print(f"UserName: {user.usernames.active_usernames[0]} Message ID: {message.id}, Content: {message.content.text.text}")
#        tgdump.add_messages_bulk(batch)
    await client.api.close_chat(chat_id)

async def on_update_new_message(client: Client, update: UpdateNewMessage):
    logging.info('on_update_new_message handler called')
    message = update.message

    if target_chat_id == None or message.chat_id != target_chat_id:
        return

    if isinstance(message.content, MessageText):
        print(f"UpdateNewMessage: Message ID: {message.id}, Content: {message.content.text.text}")
        tgdump.add_message(message)

async def on_new_chat(client: Client, update: UpdateNewChat):
    print(f"Новый чат добавлен: {update.chat.title}, id: {update.chat.id}")
    tgdump.add_chat(update.chat.id, 
                    update.chat.title)

def register_handlers(client: Client):
    client.add_event_handler(on_update_new_message, update_type=API.Types.UPDATE_NEW_MESSAGE)
    client.add_event_handler(on_new_chat, update_type=API.Types.UPDATE_NEW_CHAT)