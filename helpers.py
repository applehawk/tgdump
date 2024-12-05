from typing import AsyncGenerator, List
from aiotdlib import Client
from aiotdlib.api import Messages, MessageText, Message
import tgdump
from datetime import datetime, UTC

def filter_only_messagetext(messages: List[Message]) -> List[Message]:
    return list(
        filter(
            lambda message: 
                isinstance(message.content, MessageText), 
            messages
        )
    )

async def input_chat_id():
    chat_id = ""
    while not chat_id.lstrip('-').isdigit():
        chat_id = input(f'Enter chat_id:')
    return int(chat_id)

async def load_messages_day_by_day(client: Client, 
                                     chat_id: int = None, 
                                     backward_days: int = 0) -> AsyncGenerator[ Messages, None ]:
    current_day = None
    accumulated_messages = []
    days_count = 0
    async for batch in load_all_messages_backward(client, chat_id, 1000):
        for message in batch.messages:

            message_date = datetime.fromtimestamp(message.date)
            message_day = message_date.date()

            # Если день изменился, возвращаем накопленные сообщения за предыдущий день
            if current_day and message_day != current_day:
                if accumulated_messages:
                    yield accumulated_messages  # Отправляем накопленные сообщения
                accumulated_messages = []  # Очищаем накопленные сообщения

                days_count += 1
                if days_count >= backward_days:
                    break 

            accumulated_messages.append(message)
            current_day = message_day


async def load_all_messages_backward(client: Client, 
                                     chat_id: int = None, max_messages: int = 0) -> AsyncGenerator[ Messages, None ]:
    if chat_id is None:
        chat_id = await input_chat_id()
        
    count = 0
    from_message_id = 0  # 0 означает начать с последнего сообщения
    while True:
        try:
            batch = await client.api.get_chat_history(
                chat_id, 
                from_message_id=from_message_id, 
                offset=0, 
                limit=100, request_timeout=30)

            if not batch or not batch.messages:  # Если сообщений больше нет, прекращаем загрузку
                break

            yield batch
            
            count += batch.total_count
            # Если достигнут лимит, прекращаем генерацию
            if max_messages > 0 and count >= max_messages:
                return

            from_message_id = batch.messages[-1].id

        except Exception as e:
            print(f"Exception: {e}")