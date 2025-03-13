import os
import asyncio
from openai import AsyncOpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from dotenv import load_dotenv
from docx import Document

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
PROMPT_FILE_PATH = os.getenv('PROMPT_FILE_PATH')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
WELCOME_PHRASE = os.getenv('WELCOME_PHRASE')
MAX_MESSAGES = os.getenv('MAX_MESSAGES', None)
TEMPERATURE = float(os.getenv('TEMPERATURE', 0.5))
ASSISTANT_DELAY = int(os.getenv('ASSISTANT_DELAY', 1))

conversation_histories = {}
user_message_count = {}

client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
)

def read_prompt_from_word(file_path: str) -> str:
    try:
        document = Document(file_path)
        return "\n".join([para.text for para in document.paragraphs])
    except Exception as e:
        print(f"Ошибка при чтении файла {file_path}: {e}")
        return "Произошла ошибка при загрузке промпта."

smm_prompt = read_prompt_from_word(PROMPT_FILE_PATH)

async def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    
    if chat_id in conversation_histories:
        del conversation_histories[chat_id]
    if chat_id in user_message_count:
        del user_message_count[chat_id]
        
    conversation_histories[chat_id] = [{"role": "system", "content": smm_prompt}]
    conversation_histories[chat_id].append({"role": "user", "content": "Hello"})
    conversation_histories[chat_id].append({"role": "assistant", "content": WELCOME_PHRASE})
    user_message_count[chat_id] = 0
    
    await update.message.reply_text(WELCOME_PHRASE)


async def ask_openai(messages):
    try:
        print("_______________________________________________________________________"
              "Запрос в OpenAI:", messages)

        response = await client.chat.completions.create(
            temperature=TEMPERATURE,
            model="gpt-4o",
            messages=messages
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ошибка при обращении к OpenAI: {e}")
        return "Произошла ошибка при обработке запроса."


async def respond(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_input = update.message.text

    if chat_id not in user_message_count:
        user_message_count[chat_id] = 0

    if MAX_MESSAGES and user_message_count[chat_id] >= int(MAX_MESSAGES):
        await update.message.reply_text(
            "Вы превысили количество сообщений для демо-версии ИИ Менеджера, по вопросам сотрудничества обращайтесь по номеру +79146738418")
        return

    if chat_id not in conversation_histories:
        conversation_histories[chat_id] = [
            {"role": "system", "content": smm_prompt}
        ]

    conversation_histories[chat_id].append({"role": "user", "content": user_input})

    await context.bot.send_chat_action(chat_id, 'typing')
    task_response = asyncio.create_task(ask_openai(conversation_histories[chat_id]))
    task_delay = asyncio.create_task(asyncio.sleep(ASSISTANT_DELAY))
    openai_response = await task_response
    await task_delay
        
    conversation_histories[chat_id].append({"role": "assistant", "content": openai_response})
    user_message_count[chat_id] += 1
    await update.message.reply_text(openai_response)


def main():
    print('TELEGRAM_BOT_TOKEN', TELEGRAM_BOT_TOKEN)
    print('client.api_key', client.api_key)
    if not TELEGRAM_BOT_TOKEN or not client.api_key:
        print("Ошибка: не задан TELEGRAM_API_KEY или OPENAI_API_KEY.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))
    application.run_polling()


if __name__ == "__main__":
    main()
