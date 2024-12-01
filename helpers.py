from aiotdlib import Client
import tgdump

async def input_chat_id():
    chat_id = ""
    while not chat_id.lstrip('-').isdigit():
        chat_id = input(f'Enter chat_id:')
    return int(chat_id)

async def load_all_messages(client: Client, chat_id: int = None):
    if chat_id is None:
        chat_id = await input_chat_id()
        
    all_messages = []
    from_message_id = 0  # 0 означает начать с последнего сообщения
    while True:
        try:
            messages = await client.api.get_chat_history(
                chat_id, 
                from_message_id=from_message_id, 
                offset=0, 
                limit=100, request_timeout=30)

            if not messages.messages:  # Если сообщений больше нет, прекращаем загрузку
                break

            tgdump.add_messages_bulk(messages.messages)
            all_messages.extend(messages.messages)
            from_message_id = messages.messages[-1].id
        except TimeoutError:
            continue
        except Exception as e:
            print(f"Exception: {e}")
            input(f"Pause")

    print(f"Всего сообщений загружено: {len(all_messages)}")
    input(f"Пауза вводом")