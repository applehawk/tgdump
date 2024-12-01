import sqlite3
from typing import Union
from aiotdlib.api import Vector, Message, MessageText

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

# Создаем таблицу Chats
cursor.execute("""
CREATE TABLE IF NOT EXISTS Messages (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL
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

def add_messages_bulk(messages: Vector[Message]):
    try:
        message_text_only = list(filter(lambda message: isinstance(message.content, MessageText), messages))
        values = [(message.id, message.content.text.text) for message in message_text_only]
        query = f"""
        INSERT OR REPLACE INTO Messages (id, text) VALUES (?, ?)
        """
        cursor.executemany(query, values)
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"IntegrityError: {e}")

def add_messages(message_id: int, text: str):
    try:
        cursor.execute("""
        INSERT INTO Messages (id, text)
        VALUES (?, ?)
        """, (message_id, text))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Message with ID {message_id} already exists.")

# Метод подсчета уникальных ID чатов
def count_unique_chats() -> int:
    cursor.execute("SELECT COUNT(DISTINCT id) FROM Chats")
    result = cursor.fetchone()
    return result[0] if result else 0

def close():
    conn.close()