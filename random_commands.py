import random
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def random_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /random command with various options"""
    user_id = update.effective_user.id if update.effective_user else 'unknown'
    
    message = update.message or update.business_message
    if not message:
        logger.error("Neither message nor business_message found in update")
        return
    
    chat_id = message.chat_id
    is_business = update.business_message is not None
    
    logger.info(f"======= RANDOM COMMAND DEBUG =======")
    logger.info(f"Command /random from user: {user_id}, chat_id: {chat_id}, is_business: {is_business}")
    
    # Используем context.sender если он есть, иначе отправляем напрямую в текущий чат
    if hasattr(context, 'sender'):
        logger.info(f"Using context.sender to send messages to chat_id: {context.sender.chat_id}")
        sender = context.sender
    else:
        logger.info(f"No context.sender found, using direct bot.send_message to chat_id: {chat_id}")
        # Отправляем напрямую в текущий чат
        async def direct_send(text, **kwargs):
            return await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        sender = type('', (), {'send_message': direct_send})()
    
    # Подробное логирование аргументов
    logger.info(f"Context args: {context.args}")
    logger.info(f"Context type: {type(context.args)}")
    
    # Проверяем, есть ли аргументы в тексте сообщения
    if message and message.text:
        text_parts = message.text.split()
        logger.info(f"Message text parts: {text_parts}")
        if len(text_parts) > 1:
            logger.info(f"Potential arg from text: {text_parts[1]}")
    
    # Проверяем стандартные аргументы
    args = context.args
    logger.info(f"Final args: {args}")
    
    # Если аргументы не переданы, пытаемся извлечь их из текста сообщения
    if not args and message and message.text:
        text_parts = message.text.split()
        if len(text_parts) > 1:
            args = [text_parts[1]]
            logger.info(f"Extracted args from message text: {args}")
    
    if not args:
        await sender.send_message(
            text="Please specify a random option:\n"
            "/random cube - Roll a 6-sided dice\n"
            "/random yn - Yes or No answer\n"
            "/random q - Ask the Magic 8-Ball\n"
            "/random r - Russian roulette"
        )
        return
    
    option = args[0].lower()
    logger.info(f"Selected option: {option}")
    
    if option == "cube":
        result = random.randint(1, 6)
        await sender.send_message(text=f"🎲 Rolling a dice... You got: {result}")
    
    elif option == "yn":
        result = random.choice(["Yes", "No"])
        await sender.send_message(text=f"🔮 {result}")
    
    elif option == "q":
        positive_answers = [
            "It is certain.",
            "Without a doubt.",
            "You may rely on it.",
            "Yes, definitely.",
            "As I see it, yes.",
            "Most likely.",
            "Outlook good.",
            "Signs point to yes.",
            "Yes.",
            "All signs say YES.",
            "The stars align in your favor.",
            "Absolutely positive.",
            "The universe says yes.",
            "You can count on it.",
            "Definitely yes.",
            "The answer is clear: yes.",
            "Undoubtedly yes.",
            "Affirmative.",
            "Positive outcome expected.",
            "Success is guaranteed."
        ]
        
        neutral_answers = [
            "Reply hazy, try again.",
            "Ask again later.",
            "Cannot predict now.",
            "Better not tell you now.",
            "Concentrate and ask again.",
            "Don't decide yet.",
            "Outlook unclear.",
            "The answer is foggy.",
            "The future is uncertain.",
            "The stars are not aligned yet.",
            "The crystal ball is cloudy.",
            "The answer is in flux.",
            "The outcome is still forming.",
            "Too early to tell.",
            "The answer is hidden for now.",
            "The spirits are silent on this matter.",
            "The universe is undecided.",
            "Neither yes nor no at this time.",
            "The answer requires more time.",
            "The outcome is balanced between possibilities."
        ]
        
        negative_answers = [
            "Don't count on it.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful.",
            "My reply is no.",
            "No way.",
            "Not a chance.",
            "Highly unlikely.",
            "The stars say no.",
            "All signs point to no.",
            "The universe disagrees.",
            "Not in your favor.",
            "The answer is clearly no.",
            "Chances are very slim.",
            "Definitely not.",
            "The cosmic forces say no.",
            "The outcome looks negative.",
            "Not possible at this time.",
            "Absolutely not.",
            "The odds are against you."
        ]
        
        all_answers = positive_answers + neutral_answers + negative_answers
        result = random.choice(all_answers)
        
        await sender.send_message(text=f"🔮 {result}")
        
    elif option == "r":
        bullet = random.randint(1, 6)
        if bullet == 1:
            result = "🔫 BANG! A deafening shot rang out. But you won't hear it anymore."
        else:
            result = "🔫 Click... Misfire. You got lucky this time."
        
        await sender.send_message(text=result)
    
    else:
        await sender.send_message(
            text="Unknown option. Available options:\n"
            "/random cube - Roll a 6-sided dice\n"
            "/random yn - Yes or No answer\n"
            "/random q - Ask the Magic 8-Ball\n"
            "/random r - Russian roulette"
        )

def register_random_commands(application, business_message_support=False):
    """Register the random command handlers"""
    logger.info("")
