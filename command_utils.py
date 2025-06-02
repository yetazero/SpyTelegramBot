import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

class MessageSender:
    def __init__(self, bot, chat_id, business_connection_id=None):
        self.bot = bot
        self.chat_id = chat_id
        self.business_connection_id = business_connection_id
    
    async def send_message(self, text, **kwargs):
        if 'chat_id' in kwargs:
            del kwargs['chat_id']
            
        if self.business_connection_id and 'business_connection_id' not in kwargs:
            kwargs['business_connection_id'] = self.business_connection_id
            logger.info(f"Sending business message to chat_id={self.chat_id} with business_connection_id={self.business_connection_id}")
            
        return await self.bot.send_message(chat_id=self.chat_id, text=text, **kwargs)

def ensure_reply_to_same_chat(handler):
    @functools.wraps(handler)
    async def wrapped_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        message = update.message or update.business_message
        
        if not message:
            logger.error("No message found in update")
            return await handler(update, context, *args, **kwargs)

        original_chat_id = message.chat_id
        
        is_business = update.business_message is not None
        business_connection_id = None
        
        if is_business and hasattr(update.business_message, 'business_connection_id'):
            business_connection_id = update.business_message.business_connection_id
            logger.info(f"Business message detected with business_connection_id: {business_connection_id}")
        
        logger.info(f"Original chat_id: {original_chat_id}, message type: {'business' if is_business else 'regular'}")
        
        context.chat_data['original_chat_id'] = original_chat_id
        context.chat_data['is_business'] = is_business
        if business_connection_id:
            context.chat_data['business_connection_id'] = business_connection_id
        
        context._source_chat_id = original_chat_id
        context.user_data['_source_chat_id'] = original_chat_id
        
        sender = MessageSender(context.bot, original_chat_id, business_connection_id)
        context.sender = sender
        
        try:
            return await handler(update, context, *args, **kwargs)
        finally:
            if hasattr(context, 'sender'):
                delattr(context, 'sender')
    
    return wrapped_handler
