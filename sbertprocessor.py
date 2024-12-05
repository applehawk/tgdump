from transformers import AutoTokenizer, AutoModel
import torch
from aiotdlib.api import Messages, Message
from typing import List
from helpers import filter_only_messagetext

#Load AutoModel from huggingface model repository
tokenizer = AutoTokenizer.from_pretrained("ai-forever/sbert_large_nlu_ru")
model = AutoModel.from_pretrained("ai-forever/sbert_large_nlu_ru")

#Mean Pooling - Take attention mask into account for correct averaging
def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    sum_embeddings = torch.sum(token_embeddings * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    return sum_embeddings / sum_mask

async def process_sentences(messages: List[Message]):
    messages_text_only: List[Message] = filter_only_messagetext(messages)

    sentences = list(map(
        lambda message:
            message.content.text.text
    , messages_text_only))

    data = {
        "id": message.id,
        "datetime": str(message.date),
        "text": message.text,
        "sender_user_name": self.get_telegram_user_name(sender),
        "sender_user_id": sender. id,
        "is_reply": message.is_reply
    }
    if message.is_reply:
        data["reply_to_message_id"] = message.reply_to.reply_to_msg_id

    print(sentences)

    #Tokenize sentences
    #encoded_input = tokenizer(sentences, padding=True, truncation=True, max_length=24, return_tensors='pt')
