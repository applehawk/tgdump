import sqlite3
from typing import Union
from aiotdlib.api import Vector, Message, MessageText, MessageSender, MessageSenderChat, User
from helpers import filter_only_messagetext

# Создаем или подключаемся к базе данных
conn = sqlite3.connect("tgdump.db")
cursor = conn.cursor()

# Создаем таблицу Chats
cursor.execute("""
CREATE TABLE IF NOT EXISTS Chats (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL
)
""")
conn.commit()

def create_messages_if_not_exists():
    # Создаем таблицу Chats
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Messages (
        id INTEGER PRIMARY KEY,
        text TEXT NOT NULL,
        date INTEGER NOT NULL, -- Поле для даты
        sender_id_type TEXT NOT NULL, -- Тип отправителя (user или chat)
        sender_id INTEGER NOT NULL -- ID отправителя
    )
    """)
    conn.commit()

# Метод добавления данных в таблицу
def add_chat(chat_id: int, title: str):
    try:
        cursor.execute("""
        INSERT INTO Chats (id, title)
        VALUES (?, ?)
        """, (chat_id, title))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Chat with ID {chat_id} already exists.")

def drop_table_messages():
    try:
        cursor.execute("""
        DROP TABLE IF EXISTS Messages;
        """)
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"IntegrityError: {e}")

def get_sender_id(sender: MessageSender) -> int:
    return sender.chat_id if isinstance(sender, MessageSenderChat) else sender.user_id

def add_messages_bulk(messages: Vector[Message]):
    try:
        message_text_only = filter_only_messagetext(messages)
        
        values = [  (message.id, 
                     message.content.text.text,
                     message.date,
                     message.sender_id.ID,
                     get_sender_id(message.sender_id)) for message in message_text_only]
        query = f"""
        INSERT OR REPLACE INTO Messages (id, text, date, sender_id_type, sender_id) VALUES (?, ?, ?, ?, ?)
        """
        cursor.executemany(query, values)
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"IntegrityError: {e}")

# Метод подсчета уникальных ID чатов
def count_unique_chats() -> int:
    cursor.execute("SELECT COUNT(DISTINCT id) FROM Chats")
    result = cursor.fetchone()
    return result[0] if result else 0

def close():
    conn.close()