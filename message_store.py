import time
import logging
from typing import Dict, Optional, Any
from config import MESSAGE_LIFETIME

logger = logging.getLogger(__name__)

class MessageStore:
    def __init__(self):
        self.messages = {} 
        self.chats_enabled = {}
        self.last_check = time.time() 
        self.deleted_queue = []  
    
    def store_message(self, message):
        message_id = message.message_id
        chat_id = message.chat.id
        
        key = f"{chat_id}:{message_id}"
        self.messages[key] = {
            'message': message,
            'timestamp': time.time(),
            'deleted': False  
        }
        
        self.cleanup_old_messages()
        
    def get_message(self, chat_id, message_id) -> Optional[Any]:
        """
        Gets a message from storage by chat_id and message_id.
        Returns the message itself or None if it doesn't exist.
        """
        key = f"{chat_id}:{message_id}"
        message_data = self.messages.get(key)
        return message_data['message'] if message_data else None
    
    def cleanup_old_messages(self):
        """
        Removes old messages from storage.
        """
        current_time = time.time()
        for key, message_data in list(self.messages.items()):
            if current_time - message_data['timestamp'] > MESSAGE_LIFETIME:
                del self.messages[key]
    
    def enable_chat(self, chat_id):
        """
        Enables tracking for the specified chat.
        """
        self.chats_enabled[chat_id] = True
        
    def disable_chat(self, chat_id):
        """
        Disables tracking for the specified chat.
        """
        self.chats_enabled[chat_id] = False
        
    def get_deleted_messages(self):
        """
        Returns a list of deleted messages and clears the queue.
        This method is no longer used directly, as checking for deleted messages and sending them
        happens in handlers.check_deleted_messages.
        """
        logger.info("Using deprecated method get_deleted_messages")
        deleted = self.deleted_queue
        self.deleted_queue = []
        return deleted
    
    def check_deleted_messages(self, application):
        """
        Checks for deleted messages by polling the Telegram API.
        Should be called periodically from job_queue.
        
        This method is no longer used, checking happens in handlers.check_deleted_messages directly
        """
        logger.info("Using deprecated method, check handlers.check_deleted_messages instead")
        return []
        
message_store = MessageStore()
