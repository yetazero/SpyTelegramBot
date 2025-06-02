import logging
from telegram.ext import ContextTypes
from config import ADMIN_ID

logger = logging.getLogger(__name__)

CHAT_TYPE_PRIVATE = 'private'
CHAT_TYPE_GROUP = 'group'
CHAT_TYPE_SUPERGROUP = 'supergroup'

user_group_mapping = {}

def save_group_chat(user_id, chat_id, chat_type):
    chat_type_str = str(chat_type) if not isinstance(chat_type, str) else chat_type
    
    if chat_type_str in [CHAT_TYPE_GROUP, CHAT_TYPE_SUPERGROUP, 'group', 'supergroup']:
        user_group_mapping[str(user_id)] = chat_id
        logger.info(f"Saved group chat {chat_id} for user {user_id} (type: {chat_type_str})")
        return True
    return False

def is_user_admin(user_id):
    return str(user_id) == str(ADMIN_ID)

def get_target_chat_id(context: ContextTypes.DEFAULT_TYPE, user_id, current_chat_id, current_chat_type):
    logger.info(f"get_target_chat_id called with user_id={user_id}, current_chat_id={current_chat_id}, current_chat_type={current_chat_type}")
    
    chat_type_str = str(current_chat_type) if not isinstance(current_chat_type, str) else current_chat_type
    
    update = context.update if hasattr(context, 'update') else None
    if update and hasattr(update, 'business_message') and update.business_message:
        logger.info(f"Business message detected, using original chat: {current_chat_id}")
        return current_chat_id
    
    if hasattr(context, 'chat_data') and 'original_chat_id' in context.chat_data:
        original_id = context.chat_data['original_chat_id']
        logger.info(f"Found original_chat_id in context: {original_id}")
        return original_id
    
    if hasattr(context, '_source_chat_id') and context._source_chat_id:
        logger.info(f"Found _source_chat_id in context: {context._source_chat_id}")
        return context._source_chat_id
    
    if chat_type_str == CHAT_TYPE_PRIVATE or chat_type_str == 'private':
        logger.info(f"Private chat, replying to same chat: {current_chat_id}")
        return current_chat_id
    
    if chat_type_str in [CHAT_TYPE_GROUP, CHAT_TYPE_SUPERGROUP, 'group', 'supergroup']:
        save_group_chat(user_id, current_chat_id, chat_type_str)
        logger.info(f"Group chat, replying to same chat: {current_chat_id}")
        return current_chat_id
        
    if str(user_id) in user_group_mapping:
        group_chat_id = user_group_mapping[str(user_id)]
        logger.info(f"Using saved group chat for user {user_id}: {group_chat_id}")
        return group_chat_id
    
    logger.info(f"No suitable target chat found, using current chat: {current_chat_id}")
    return current_chat_id
