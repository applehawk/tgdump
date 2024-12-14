from telethon.sync import TelegramClient
from telethon.tl.types import User, Channel
from telethon.tl.types import Message
import telebot
import logging
import threading
import time

class SummarizerBot:
    def __init__(self, telegram_bot_auth_token, telegram_summary_receivers, allowed_contexts, chat_callback, add_newchat_callback):
        self.logger = logging.getLogger("CSB")
        self.telegram_summary_receivers = telegram_summary_receivers
        self.verified_receivers = dict()

        # This one is used for switching between summarized chat conversation
        self.allowed_commands = ["/" + c for c in allowed_contexts]
        self.current_user_contexts = dict()

        # This one is used to generate responses for arbitrary messages
        self.chat_callback = chat_callback
        self.add_newchat_callback = add_newchat_callback

        # The bot is running in the background thread to make the call non-blocking
        self.bot = telebot.TeleBot(telegram_bot_auth_token)
        self.bot.set_update_listener(self.__handle_messages)
        self.bot_thread = threading.Thread(target=self.bot.infinity_polling)
        self.bot_thread.start()

    def send_summary(self, username, text, chat_id):
        if not username in self.verified_receivers:
            self.logger.info(f"User {username} is not yet verified")
            return
        self.bot.send_message(self.verified_receivers[username], text, parse_mode="HTML")
        self.set_current_user_context(username, chat_id)

    def set_typing_status(self, users, predicate):
        # The self self.bot.send_chat_action(user, "typing") sets the status for <= 5 seconds until the message is sent
        # We use this kludge to make the status persistent for a longer time
        def f():
            while predicate():
                for u in users:
                    if u in self.verified_receivers:
                        self.bot.send_chat_action(self.verified_receivers[u], "typing")
                time.sleep(5)

        threading.Thread(target=f).start()

    def set_current_user_context(self, username, context):
        self.current_user_contexts[username] = context

    def parse_addchat_command(self, sender, message):
        parts = message.text.split()
        if len(parts) != 3 or parts[0] != "/add":
            self.bot.send_message(message.chat.id, "Строка не соответствует ожидаемому формату.")
            return
        
        chatname = parts[1]
        try:
            days = int(parts[2])  # Преобразуем days в целое число
        except ValueError:
            self.bot.send_message(message.chat.id, "Параметр days должен быть целым числом.")
            pass
        
        return chatname, days

    def addchat_command(self, sender, message):
        chatname, days = self.parse_addchat_command(sender, message)
        
        chat = self.bot.get_chat(chatname)
        chat_id = chat.id
        self.allowed_commands.extend(["/" + c for c in [chat_id]])
        self.set_current_user_context(sender, chat_id)
        self.bot.send_message(message.chat.id, f"Добавлен чат {chat.username}")
        self.add_newchat_callback(sender, chat_id, chatname, days, lambda x: self.bot.send_message(message.chat.id, x))

    def __handle_messages(self, messages):
        for message in messages:

            if not message.text: # Только с текстом работаем
                return
            
            sender = message.from_user.username # Ник отправившего сообщение
            fwd_from = message.fwd_from

            if not sender or not sender in self.telegram_summary_receivers:
                self.bot.send_message(message.chat.id, 
                                      f"Попытка использования неавторизованным пользоваталем {sender}, {str(message.from_user)}")
                self.logger.warning(f"Unauthorized usage attempt from user: {str(message.from_user)}")
                return
            
            if message.text.startswith("/"): # Обработка команд
                if message.text.startswith("/addchat"):
                    self.addchat_command(sender, message)
                    return
                if message.text.startswith("/exit"):
                    self.set_current_user_context(sender, None)
                    return
                if message.text == "/verify":
                    # We need this verification because bots cannot retrieve chat IDs by the username
                    self.verified_receivers[sender] = message.chat.id
                    self.bot.send_message(message.chat.id, "You are now verified and will receive generated summaries")
                    return
                else: # Здесь выбирается контекст
                    if not message.text in self.allowed_commands: # если этой команда
                        self.bot.send_message(message.chat.id,
                                              "Invalid command, valid commands are: " + ", ".join(
                                                  self.allowed_commands))
                        return
                    self.set_current_user_context(sender, message.text[1:])
                    self.bot.send_message(message.chat.id, f"Switched context to {self.current_user_contexts[sender]}")
            else: # Это обычный текст, для вызова модели
                if not sender in self.current_user_contexts:
                    chat = self.bot.get
                    self.bot.send_message(message.chat.id,
                                          "Select context first, valid commands are: " + ", ".join(
                                              self.allowed_commands))
                    return
                self.chat_callback(message.text, sender, self.current_user_contexts[sender],
                                   lambda x: self.bot.send_message(message.chat.id, x))