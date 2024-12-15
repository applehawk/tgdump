from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain.chains.llm import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain.globals import set_debug
set_debug(True)

class Summarizer:
    def __init__(self, anthropic_key: str):
        self.anthropic_api_key = anthropic_key
        self.anthropic_model = "claude-3-5-sonnet-latest"

        # Needed to store chat history
        self.persistent_prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content="You are a chatbot having a conversation with a human."),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{human_input}")
            ]
        )

    def summarize(self, text_to_summarize: str, summarization_prompt: str):

        memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True)
        
        llm = ChatAnthropic(
            model=self.anthropic_model,
            temperature=0,
            max_tokens=1024,
            timeout=None,
            max_retries=2,
            api_key=self.anthropic_api_key)
        
        chat_llm_chain = LLMChain(
            llm=llm,
            prompt=self.persistent_prompt,
            verbose=False,
            memory=memory,
        )

        init_prompt = summarization_prompt.format(text_to_summarize=text_to_summarize)
        return chat_llm_chain.predict(human_input=init_prompt), chat_llm_chain

    @staticmethod
    def validate_summarization_prompt(summarization_prompt):
        if not "{text_to_summarize}" in summarization_prompt:
            raise RuntimeError("Summarization prompt should include \"{ text_to_summarize }\"")