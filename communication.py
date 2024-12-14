import atexit
from datetime import datetime, timedelta, timezone
import threading
import time
import logging
from config import config
from aiotdlib import Client, ClientSettings
from aiotdlib.api import Message, MessageSender, MessageSenderUser, MessageSenderChat, User, Chat, MessageReplyToMessage
from aiotdlib.api import API, UpdateNewMessage, UpdateNewChat, MessageText
from typing import List, Tuple
from handlers import register_handlers
import tgdump
from helpers import load_messages_day_by_day, filter_only_messagetext
import asyncio

class GroupChatScrapper:
    async def startClient(self):
        await self.client.start()

    async def async_stop(self):
        # Асинхронный метод завершения
        await self.client.api.close()
        await self.client.stop()

    def stopClient(self):
        # Запуск асинхронного метода через asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если цикл уже запущен (например, в приложении с асинхронным сервером)
            asyncio.ensure_future(self.async_stop())
        else:
            loop.run_until_complete(self.async_stop())

    def __init__(self):
        self.client = Client(
            settings=ClientSettings(
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                phone_number=config.PHONE_NUMBER,
                library_path="/Users/vladmac/Library/Caches/pypoetry/virtualenvs/python-tdlib-VZrnRyOY-py3.12/lib/python3.12/site-packages/aiotdlib/tdlib/libtdjson_darwin_arm64.dylib"
            )
        )
        # We need to always disconnect not to break the Telegram session
    
    async def get_telegram_user_name(self, sender: MessageSender):
        if sender and isinstance(sender, MessageSenderUser):
            user: User = await self.client.get_user(sender.user_id)
            if user.first_name and user.last_name:
                return user.first_name + " " + user.last_name
            elif user.first_name:
                return user.first_name
            elif user.last_name:
                return user.last_name
            else:
                return "<unknown>"
        else:
            if sender and isinstance(sender, MessageSenderChat):
                chat: Chat = await self.client.get_chat(sender.chat_id)
                return chat.title

    @staticmethod
    def get_datetime_from(lookback_period):
        return (datetime.utcnow() - timedelta(seconds=lookback_period)).replace(tzinfo=timezone.utc)

    def get_sender_id(self, sender: MessageSender) -> int:
        return sender.chat_id if isinstance(sender, MessageSenderChat) else sender.user_id

    async def process_sentences(self, messages: List[Message]) -> Tuple[List, str]:
        messages_text_only: List[Message] = filter_only_messagetext(messages)

        history = []
        sentences = []
        for message in messages_text_only:
            sender = message.sender_id
            sender_user_name = await self.get_telegram_user_name(sender)
            is_reply_to_message = message.reply_to and isinstance(message.reply_to, MessageReplyToMessage)
            data = {
                "id": message.id,
                "datetime": str(message.date),
                "text": message.content.text.text,
                "sender_user_name": sender_user_name,
                "sender_user_id": self.get_sender_id(message.sender_id),
                "is_reply": is_reply_to_message
            }
            if is_reply_to_message:
                data["reply_to_message_id"] = message.reply_to.message_id
            sentences.append(f"{sender_user_name} [str(message.date)]: \"{message.content.text.text}\"")
            history.append(data)

        print(",".join(sentences))

        chat_title = (await self.client.get_chat(messages[0].chat_id)).title
        return list(reversed(history)), chat_title
    
    async def get_message_history(self, chat_id: int, last_days: int):
        await self.client.api.open_chat(chat_id)

        global target_chat_id
        target_chat_id = chat_id

        tgdump.drop_table_messages()
        tgdump.create_messages_if_not_exists()

        current_date = datetime.now()
        days_history = []
        chat_title = None
        async for day_batch in load_messages_day_by_day(self.client, chat_id, last_days):
            current_date -= timedelta(days=1)  # Вычитаем 1 день
            history, chat_title = await self.process_sentences(day_batch)
            print(f"day {current_date.strftime('%Y-%m-%d')}: {history}")
            days_history.extend(history)

        return days_history, chat_title
        