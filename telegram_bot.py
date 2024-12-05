from telethon.sync import TelegramClient
from telethon.tl.types import User, Channel
import telebot
import logging
import threading
import time

class SummarizerBot:
    def __init__(self, telegram_bot_auth_token, telegram_summary_receivers, allowed_contexts, chat_callback):
        self.logger = logging.getLogger("CSB")
        self.telegram_summary_receivers = telegram_summary_receivers
        self.verified_receivers = dict()

        # This one is used for switching between summarized chat conversation
        self.allowed_commands = ["/" + c for c in allowed_contexts]
        self.current_user_contexts = dict()

        # This one is used to generate responses for arbitrary messages
        self.chat_callback = chat_callback

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

    def __handle_messages(self, messages):
        for message in messages:
            if not message.text:
                return
            sender = message.from_user.username
            if not sender or not sender in self.telegram_summary_receivers:
                self.logger.warning(f"Unauthorized usage attempt from user: {str(message.from_user)}")
                return
            if message.text.startswith("/"):
                if message.text == "/verify":
                    # We need this verification because bots cannot retrieve chat IDs by the username
                    self.verified_receivers[sender] = message.chat.id
                    self.bot.send_message(message.chat.id, "You are now verified and will receive generated summaries")
                    return
                else:
                    if not message.text in self.allowed_commands:
                        self.bot.send_message(message.chat.id,
                                              "Invalid command, valid commands are: " + ", ".join(
                                                  self.allowed_commands))
                        return
                    self.set_current_user_context(sender, message.text[1:])
                    self.bot.send_message(message.chat.id, f"Switched context to {self.current_user_contexts[sender]}")
            else:
                if not sender in self.current_user_contexts:
                    self.bot.send_message(message.chat.id,
                                          "Select context first, valid commands are: " + ", ".join(
                                              self.allowed_commands))
                    return
                self.chat_callback(message.text, sender, self.current_user_contexts[sender],
                                   lambda x: self.bot.send_message(message.chat.id, x))