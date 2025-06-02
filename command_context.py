from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
import logging
import functools

logger = logging.getLogger(__name__)

def force_same_chat(original_method):
    @functools.wraps(original_method)
    async def wrapper(self, *args, **kwargs):
        if 'chat_id' in kwargs:
            if isinstance(kwargs['chat_id'], int) and kwargs['chat_id'] > 0:
                if hasattr(self, '_original_chat_id'):
                    logger.info(f"Redirecting message from user chat {kwargs['chat_id']} to original chat {self._original_chat_id}")
                    kwargs['chat_id'] = self._original_chat_id
        
        return await original_method(self, *args, **kwargs)
    return wrapper

class ContextAwareCommandHandler(CommandHandler):
    
    async def handle_update(self, update: Update, application, check_result, context=None):
        if context is None:
            context = application.context_types.context.copy()
        
        message = update.message or update.business_message
        if message:
            chat_id = message.chat_id
            chat_type = message.chat.type
            user_id = update.effective_user.id if update.effective_user else None
            
            context.chat_data['_source_chat_id'] = chat_id
            context.chat_data['original_chat_id'] = chat_id
            context.user_data['last_chat_id'] = chat_id
            
            application.bot._original_chat_id = chat_id
            
            if not hasattr(application.bot, '_original_send_message'):
                application.bot._original_send_message = application.bot.send_message
                application.bot.send_message = force_same_chat(application.bot.send_message)
            
            logger.info(f"Command received in chat type: {chat_type}, id: {chat_id}, from user: {user_id}")
        
        return await super().handle_update(
            update=update,
            application=application,
            check_result=check_result,
            context=context
        )
