import asyncio
from communication import GroupChatScrapper
from summarizer import Summarizer
import logging
from config import config
from telegram_bot import SummarizerBot
import json
import logging
from collections import defaultdict
import threading
from typing import Union, List
from pydantic import BaseModel, Field
import argparse
import schedule
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

async def summarization_job(chat_cfg, summarization_prompt, summary_receivers, llm_contexts, llm_contexts_lock, group_chat_scrapper, summarizer, envoy_bot, logger):
    logger.info(f"Running summarization job for: {chat_cfg.id}")
    async with llm_contexts_lock:
        envoy_bot.set_typing_status(summary_receivers, llm_contexts_lock.locked)

        messages, chat_title = await group_chat_scrapper.get_message_history(chat_cfg.id, chat_cfg.lookback_days)
        logger.debug(
            f"Scrapped {len(messages)} messages for {chat_cfg.id} over the last {chat_cfg.lookback_days} days")
        serialized_messages = json.dumps({"messages": messages}, ensure_ascii=False)

        summary, context = summarizer.summarize(serialized_messages, summarization_prompt)

        for u in summary_receivers:
            llm_contexts[chat_cfg.id][u] = context
            logger.info(f"Sending summary for {chat_cfg.id} to {u}")
            logger.debug(f"Summary for {chat_title}: {summary}")
            envoy_bot.send_summary(
                u,
                f"Summary of the {len(messages)} messages for <b>{chat_cfg.id}</b> for the last {int(chat_cfg.lookback_days)} days:\n\n{summary}",
                chat_cfg.id
            )

async def schedule_jobs(app_config, group_chat_scrapper, summarizer, envoy_bot, logger):
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
            envoy_bot=envoy_bot,
            logger=logger
        )

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(0.1)

async def main():
    global llm_contexts, llm_contexts_lock
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

    with open("./config.json", 'r') as file:
        app_config = AppConfig.model_validate_json(file.read())

    def chat_callback(input_message_text, sender, context_name, send_message_func):
        envoy_bot.set_typing_status([sender], llm_contexts_lock.locked)
        if not context_name in llm_contexts or not sender in llm_contexts[context_name]:
            send_message_func(f"No context is available for {context_name} yet")
            return
        logger.info(f"Chatting with: {sender}")
        response = llm_contexts[context_name][sender].predict(human_input=input_message_text)
        logger.debug(f"Response to message \"{input_message_text}\" from {sender}: \"{response}\"")
        send_message_func(response)

    group_chat_scrapper = GroupChatScrapper()
    await group_chat_scrapper.client.start()

    summarizer = Summarizer(config.ANTHROPIC_API)

    envoy_bot = SummarizerBot(
        config.TG_AUTH_TOKEN,
        app_config.telegram_summary_receivers,
        [c.id for c in app_config.chats_to_summarize],
        chat_callback
    )

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
            envoy_bot=envoy_bot,
            logger=logger
        )

    # Schedule jobs
    await schedule_jobs(app_config, group_chat_scrapper, summarizer, envoy_bot, logger)
    await group_chat_scrapper.client.stop()

if __name__ == '__main__':


    asyncio.run(main())