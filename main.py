import signal
import sys
import asyncio
import logging
import json

from config import config
from communication import GroupChatScrapper
from summarizer import Summarizer
from telegram_bot import SummarizerBot
from handlers import register_handlers

from typing import Union, List
from collections import defaultdict
from pydantic import BaseModel, Field
import aioschedule

class SummarizationConfig(BaseModel):
    id: Union[str, int]
    lookback_days: int
    summarization_prompt_path: str

class AppConfig(BaseModel):
    log_level: str = Field(default="INFO")
    chats_to_summarize: List[SummarizationConfig]
    telegram_summary_receivers: List[str]

with open("./prompts/summarization_prompt.txt", "r") as f:
    Summarizer.validate_summarization_prompt(f.read())

async def summarization_job(chat_cfg, summarization_prompt, summary_receivers, llm_contexts, llm_contexts_lock, group_chat_scrapper, summarizer, summary_bot, logger):
    logger.info(f"Running summarization job for: {chat_cfg.id}")
    async with llm_contexts_lock:
        summary_bot.set_typing_status(summary_receivers, llm_contexts_lock.locked)

        messages, chat_title = await group_chat_scrapper.get_message_history(chat_cfg.id, chat_cfg.lookback_days)
        logger.debug(
            f"Scrapped {len(messages)} messages for {chat_cfg.id} over the last {chat_cfg.lookback_days} days")
        serialized_messages = json.dumps({"messages": messages}, ensure_ascii=False)

        summary, context = summarizer.summarize(serialized_messages, summarization_prompt)

        for u in summary_receivers:
            llm_contexts[chat_cfg.id][u] = context
            logger.info(f"Sending summary for {chat_cfg.id} to {u}")
            logger.debug(f"Summary for {chat_title}: {summary}")
            summary_bot.send_summary(
                u,
                f"Summary of the {len(messages)} messages for <b>{chat_cfg.id}</b> for the last {int(chat_cfg.lookback_days)} days:\n\n{summary}",
                chat_cfg.id
            )

async def schedule_jobs(app_config, group_chat_scrapper, summarizer, summary_bot, logger):
    global llm_contexts, llm_contexts_lock

    for chat_config in app_config.chats_to_summarize:
        with open(chat_config.summarization_prompt_path, "r") as f:
            chat_summarization_prompt = f.read()

        # Schedule the summarization job
        aioschedule.every(chat_config.lookback_days).days.do(
            summarization_job,
            chat_cfg=chat_config,
            summarization_prompt=chat_summarization_prompt,
            summary_receivers=app_config.telegram_summary_receivers,
            llm_contexts=llm_contexts,
            llm_contexts_lock=llm_contexts_lock,
            group_chat_scrapper=group_chat_scrapper,
            summarizer=summarizer,
            envoy_bot=summary_bot,
            logger=logger
        )

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(0.1)

async def main():
    global llm_contexts, llm_contexts_lock, scrapper
    llm_contexts = defaultdict(dict)
    llm_contexts_lock = asyncio.Lock()

    # Initialize logger
    logger = logging.getLogger("CSB")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("Started!")

    # Initialize config.json
    with open("./config.json", 'r') as file:
        app_config = AppConfig.model_validate_json(file.read())

    async def add_newchat_callback(sender, chat_id, chatname, days, send_message_func):
        summary_bot.set_typing_status([sender], llm_contexts_lock.locked)
        send_message_func(f"Начало суммаризации чата: {chatname} с id:/{chat_id}")
        send_message_func(f"Будет собрано {days} дней из {chatname} с id:/{chat_id}")
        chat_config = {
            "id": str(chat_id), 
            "lookback_days": days,
            "summarization_prompt_path": "./prompts/summarization_prompt.txt"
        }
        with open(chat_config.summarization_prompt_path, "r") as f:
            chat_summarization_prompt = f.read()
            
        await summarization_job(
                chat_cfg=chat_config,
                summarization_prompt=chat_summarization_prompt,
                summary_receivers=app_config.telegram_summary_receivers,
                llm_contexts=llm_contexts,
                llm_contexts_lock=llm_contexts_lock,
                group_chat_scrapper=group_chat_scrapper,
                summarizer=summarizer,
                summary_bot=summary_bot,
                logger=logger
        )

    def chat_callback(input_message_text, sender, context_name, send_message_func):
        summary_bot.set_typing_status([sender], llm_contexts_lock.locked)
        if not context_name in llm_contexts or not sender in llm_contexts[context_name]:
            send_message_func(f"No context is available for {context_name} yet")
            return
        logger.info(f"Chatting with: {sender}")

        send_message_func("Начало суммаризации чата: {}")
        response = llm_contexts[context_name][sender].predict(human_input=input_message_text)
        logger.debug(f"Response to message \"{input_message_text}\" from {sender}: \"{response}\"")

        send_message_func(response)

    summary_bot = SummarizerBot(
        config.TG_AUTH_TOKEN,
        app_config.telegram_summary_receivers,
        [c.id for c in app_config.chats_to_summarize],
        chat_callback, 
        add_newchat_callback
    )
    summarizer = Summarizer(config.ANTHROPIC_API)

    group_chat_scrapper = GroupChatScrapper()
    await group_chat_scrapper.client.start()
    await group_chat_scrapper.client.api.load_chats(limit=900000)
    #register_handlers(group_chat_scrapper.client)
    scrapper = group_chat_scrapper

    def signal_abort_script(signal, frame):
        scrapper.stopClient()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_abort_script)

    # Run all jobs once
    for chat_config in app_config.chats_to_summarize:
        with open(chat_config.summarization_prompt_path, "r") as f:
            chat_summarization_prompt = f.read()

        await summarization_job(
                chat_cfg=chat_config,
                summarization_prompt=chat_summarization_prompt,
                summary_receivers=app_config.telegram_summary_receivers,
                llm_contexts=llm_contexts,
                llm_contexts_lock=llm_contexts_lock,
                group_chat_scrapper=group_chat_scrapper,
                summarizer=summarizer,
                summary_bot=summary_bot,
                logger=logger
        )

    # Schedule jobs
    await schedule_jobs(app_config, group_chat_scrapper, summarizer, summary_bot, logger)


if __name__ == '__main__':
    asyncio.run(main())
    