import os
import logging
import configparser
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.ext.filters import UpdateFilter
from random_commands import register_random_commands
from business_command_handler import register_business_command_handlers, BusinessCommandHandler
from command_context import ContextAwareCommandHandler
from command_utils import ensure_reply_to_same_chat
from handlers import (
    handle_message, 
    handle_edited_message,
    start_command, 
    help_command, 
    spy_command, 
    who_command, 
    check_deleted_messages,
    error_handler
)
from config import SPY_ENABLED

config = configparser.ConfigParser()
config_file = os.path.join(os.path.dirname(__file__), "config.ini")
config.read(config_file)

TOKEN = config.get("Bot", "TOKEN", fallback="your_bot_token_here")
ADMIN_ID = config.get("Bot", "ADMIN_ID", fallback="your_admin_id_here")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_application():
    """
    Create a new bot application
    """
    global SPY_ENABLED
    
    logging.info("Creating application...")
    
    if TOKEN == "your_bot_token_here" or not TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN found")
        return None
    
    from telegram.ext import Defaults
    from telegram.constants import ParseMode
    
    defaults = Defaults(
        parse_mode=ParseMode.HTML,
    )
    
    builder = Application.builder().token(TOKEN)
    builder.defaults(defaults)
    
    application = builder.build()
    
    def is_admin(update):
        user_id = update.effective_user.id if update.effective_user else None
        return user_id and str(user_id) == str(ADMIN_ID)
    
    class AdminFilter(UpdateFilter):
        def filter(self, update):
            return is_admin(update)
    
    admin_command_handlers_map = {
        "start": ensure_reply_to_same_chat(start_command),
        "help": ensure_reply_to_same_chat(help_command),
        "spy": ensure_reply_to_same_chat(spy_command),
        "who": ensure_reply_to_same_chat(who_command)
    }
    
    for cmd, handler in admin_command_handlers_map.items():
        application.add_handler(CommandHandler(cmd, handler, filters=AdminFilter()))
    
    from random_commands import random_command
    application.add_handler(CommandHandler("random", ensure_reply_to_same_chat(random_command)))
    
    class BusinessCommandFilter(UpdateFilter):
        def __init__(self, command=None, admin_only=False):
            self.command = command
            self.admin_only = admin_only
        
        def filter(self, update):
            if not update.business_message or not update.business_message.text:
                return False
            
            text = update.business_message.text
            if not text.startswith('/'):
                return False
            
            if self.admin_only:
                user_id = update.effective_user.id if update.effective_user else None
                if not user_id or str(user_id) != str(ADMIN_ID):
                    return False
            
            if self.command:
                command_parts = text.split()
                command = command_parts[0].lower()
                return command == f'/{self.command}' or command.startswith(f'/{self.command}@')
            else:
                return True
    
    for cmd, handler in {
        "start": ensure_reply_to_same_chat(start_command),
        "help": ensure_reply_to_same_chat(help_command),
        "spy": ensure_reply_to_same_chat(spy_command),
        "who": ensure_reply_to_same_chat(who_command)
    }.items():
        application.add_handler(MessageHandler(
            BusinessCommandFilter(cmd, admin_only=True),
            handler
        ))
    
    application.add_handler(MessageHandler(
        BusinessCommandFilter("random", admin_only=False),
        ensure_reply_to_same_chat(random_command)
    ))
    
    class EditedBusinessMessageFilter(UpdateFilter):
        def filter(self, update):
            return update.edited_business_message is not None
    
    application.add_handler(MessageHandler(
        filters.UpdateType.EDITED_MESSAGE | filters.UpdateType.EDITED_CHANNEL_POST,
        handle_edited_message
    ))
    
    application.add_handler(MessageHandler(
        EditedBusinessMessageFilter(),
        handle_edited_message
    ))
    
    class NonCommandBusinessMessageFilter(UpdateFilter):
        def filter(self, update):
            if update.business_message and update.business_message.text:
                first_word = update.business_message.text.split()[0]
                return not first_word.startswith('/')
            return update.business_message is not None and not hasattr(update.business_message, 'text')
    
    application.add_handler(MessageHandler(
        (filters.ALL & ~filters.COMMAND),
        handle_message
    ))
    
    application.add_handler(MessageHandler(
        NonCommandBusinessMessageFilter(),
        handle_message
    ))
    
    application.add_error_handler(error_handler)
    
    job_queue = application.job_queue
    if job_queue is not None:
        job_queue.run_repeating(check_deleted_messages, interval=10, first=10)
    else:
        logger.warning("JobQueue is not available. Install python-telegram-bot[job-queue] for deleted messages tracking.")
    
    return application

def start_bot(application):
    """Start the bot with the given application instance"""
    if not application:
        logger.error("Cannot start bot: No valid application instance provided")
        return
        
    logger.info("Bot started")
    
    async def log_raw_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            logger.info(f"Raw update received: {type(update).__name__}")
            
            msg = None
            if update.message:
                msg = update.message
                logger.info(f"Regular message detected: {msg.message_id}")
            elif update.edited_message:
                msg = update.edited_message
                logger.info(f"Edited message detected: {msg.message_id}")
            elif update.business_message:
                msg = update.business_message
                logger.info(f"Business message detected: {msg.message_id}")
            elif update.edited_business_message:
                msg = update.edited_business_message
                logger.info(f"Edited business message detected: {msg.message_id}")
            
            if msg:
                logger.info(f"Message has photo: {msg.photo is not None and len(msg.photo) > 0}")
                logger.info(f"Message has video: {msg.video is not None}")
                logger.info(f"Message has voice: {msg.voice is not None}")
                logger.info(f"Message has document: {msg.document is not None}")
                
                try:
                    message_dict = msg.to_dict()
                    logger.info(f"Full message dict: {message_dict}")
                    
                    for key, value in message_dict.items():
                        if any(term in key.lower() for term in ['ttl', 'self', 'destruct', 'one_time']):
                            logger.info(f"Found potential self-destruct key: {key}={value}")
                            
                except Exception as e:
                    logger.error(f"Error checking message dict: {e}")
                    
                if msg.photo or msg.video or msg.voice or msg.document:
                    logger.info(f"RAW HANDLER: Detected media in message {msg.message_id}")
                        
        except Exception as e:
            logger.error(f"Error in raw update handler: {e}")
            logger.exception(e)
    
    application.add_handler(MessageHandler(filters.ALL, log_raw_update), group=999)
    
    allowed_updates = [
        "message",
        "edited_message",
        "edited_channel_post",
        "business_message",
        "edited_business_message"
    ]
    logger.info(f"Starting polling with allowed_updates: {allowed_updates}")
    application.run_polling(allowed_updates=allowed_updates, drop_pending_updates=True)
    logger.info("Bot polling stopped")
    
    logger.info("Bot stopped")

def run_bot():
    """Wrapper for running the bot"""
    try:
        application = create_application()
        if application:
            start_bot(application)
        else:
            logger.error("Failed to create application")
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")

if __name__ == '__main__':
    run_bot()
