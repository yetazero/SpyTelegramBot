from telegram import Update
from telegram.ext import MessageHandler, ContextTypes, filters
from telegram.ext.filters import UpdateFilter
import logging
import re
import functools

logger = logging.getLogger(__name__)

class BusinessCommandFilter(UpdateFilter):
    
    def __init__(self, cmd):
        self.cmd = cmd
    
    def filter(self, update):
        if update.business_message and update.business_message.text:
            text = update.business_message.text
            command_parts = text.split()
            if not command_parts:
                return False
            
            command = command_parts[0]
            if command == f"/{self.cmd}" or command.startswith(f"/{self.cmd}@"):
                return True
        return False

class BusinessCommandHandler(MessageHandler):
    
    def __init__(self, command, callback, **kwargs):
        self.command = command
        self.original_callback = callback
        
        super().__init__(
            BusinessCommandFilter(command),
            self._handle_update,
            **kwargs
        )
    
    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.business_message:
            text = update.business_message.text
            chat_id = update.business_message.chat_id
            chat_type = update.business_message.chat.type
            user_id = update.effective_user.id if update.effective_user else "unknown"
            
            business_connection_id = None
            if hasattr(update.business_message, 'business_connection_id'):
                business_connection_id = update.business_message.business_connection_id
                logger.info(f"Business message with business_connection_id: {business_connection_id}")
            
            try:
                context.chat_data['_source_chat_id'] = chat_id
                context.chat_data['_source_chat_type'] = chat_type
                context.chat_data['original_chat_id'] = chat_id
                context.chat_data['is_business'] = True
                if business_connection_id:
                    context.chat_data['business_connection_id'] = business_connection_id
                
                context.user_data['last_chat_id'] = chat_id
                context.bot_data['last_command_chat_id'] = chat_id
                context._source_chat_id = chat_id 
            except Exception as e:
                logger.error(f"Error saving chat context: {e}")
            
            logger.info(f"Command /{self.command} received in chat type: {chat_type}, chat_id: {chat_id}, user: {user_id}")
            
            match = re.match(r'/([^\s@]+)(@\S+)?\s*(.*)', text)
            if match:
                command_name = match.group(1)
                args_str = match.group(3)
                logger.info(f"Parsed command: /{command_name}, args_str: '{args_str}'")
                
                if args_str:
                    context.args = args_str.split()
                else:
                    context.args = []
            else:
                parts = text.split()
                if len(parts) > 1:
                    context.args = parts[1:]
                else:
                    context.args = []
                logger.info(f"Fallback parsing: command parts: {parts}, args: {context.args}")
            
            logger.info(f"Business command /{self.command} parsed with args: {context.args}")
            
            context.chat_data['command_args'] = context.args
            
            from command_utils import MessageSender
            sender = MessageSender(context.bot, chat_id, business_connection_id)
            context.sender = sender
            
            logger.info(f"Created MessageSender for chat_id: {chat_id}, business_connection_id: {business_connection_id}")
            
            try:
                result = await self.original_callback(update, context)
                return result
            finally:
                if hasattr(context, 'sender'):
                    delattr(context, 'sender')
        else:
            return await self.original_callback(update, context)

def register_business_command_handlers(application, commands_dict):
    for command, handler in commands_dict.items():
        application.add_handler(BusinessCommandHandler(command, handler))
        logger.info(f"Registered business command handler for /{command}")
