import logging
import time
import re
import datetime as dt
from datetime import datetime, timezone
from telegram import Update, constants, User
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from message_store import MessageStore
from config import ADMIN_ID, SPY_ENABLED, save_state
import chat_manager

message_store = MessageStore()
logger = logging.getLogger(__name__)

def format_forward_header(message, message_type="regular"):
    user_id = message.from_user.id if message.from_user else "Unknown"
    username = message.from_user.username if message.from_user and message.from_user.username else ""
    chat_id = message.chat.id if message.chat else "Unknown"
    chat_title = message.chat.title if message.chat and message.chat.title else f"Chat {chat_id}"
    
    header = f"Forwarded from "
    if username:
        header += f"@{username} "
    
    header += f"({user_id}) in {chat_id}\n"
    
    if message_type == "deleted":
        header += "🗑 DELETED MESSAGE\n"
    elif message_type == "edited":
        header += "✏️ EDITED MESSAGE\n"
    else:
        header += "💬 MESSAGE\n"
    
    sent_time = message.date.strftime('%Y-%m-%d %H:%M:%S')
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    
    if message_type == "deleted":
        header += f"<i>Sent at {sent_time}, deleted at {current_time}</i>\n"
    elif message_type == "edited":
        header += f"<i>Sent at {sent_time}, edited at {current_time}</i>\n"
    else:
        header += f"<i>Sent at {sent_time}</i>\n"
    
    return header

def format_message_content(message):
    content = ""
    
    if message.photo:
        content += "[Photo] "
    elif message.video:
        content += "[Video] "
    elif message.audio:
        content += "[Audio] "
    elif message.voice:
        content += "[Voice] "
    elif message.document:
        content += "[Document] "
    elif message.animation:
        content += "[Animation] "
    elif message.sticker:
        emoji = message.sticker.emoji if hasattr(message.sticker, 'emoji') and message.sticker.emoji else ''
        content += f"[Sticker: {emoji}] "
    elif message.location:
        content += "[Location] "
    elif message.venue:
        content += f"[Venue: {message.venue.title}] "
      
    if message.caption:
        content += message.caption
    elif hasattr(message, 'text') and message.text:
        content += message.text
        
    if not content.strip():
        content = "[No content]"
        
    return content

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    if not message:
        logger.error("Neither message nor business_message found in update")
        return
    
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = message.chat_id
    chat_type = message.chat.type if hasattr(message.chat, 'type') else 'unknown'
    is_business = update.business_message is not None
    
    if not user_id or str(user_id) != str(ADMIN_ID):
        logger.info(f"Non-admin user {user_id} tried to use /start command")
        return
    
    if chat_type in ['group', 'supergroup']:
        chat_manager.save_group_chat(user_id, chat_id, chat_type)
        context.user_data['last_group_chat_id'] = chat_id
        context.bot_data['last_group_chat_id'] = chat_id
    
    if hasattr(context, 'sender'):
        logger.info(f"Command /start from {user_id} - using context.sender to chat_id: {context.sender.chat_id}")
        await context.sender.send_message(
            text="Hello! I'm Spy Bot for tracking deleted and edited messages in chats.\n\n"
            "Available commands:\n"
            "/spy on - Enable tracking mode\n"
            "/spy off - Disable tracking mode\n"
            "/who - Get user information\n"
            "/random cube - Roll a dice\n"
            "/random yn - Yes/No answer\n"
            "/random q - Magic 8-ball response"
        )
    else:
        logger.info(f"Command /start from {user_id} - using direct send to chat_id: {chat_id}")
        await context.bot.send_message(
            chat_id=chat_id,
            text="Hello! I'm Spy Bot for tracking deleted and edited messages in chats.\n\n"
            "Available commands:\n"
            "/spy on - Enable tracking mode\n"
            "/spy off - Disable tracking mode\n"
            "/who - Get user information\n"
            "/random cube - Roll a dice\n"
            "/random yn - Yes/No answer\n"
            "/random q - Magic 8-ball response"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    if not message:
        logger.error("Neither message nor business_message found in update")
        return
    
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = message.chat_id
    chat_type = message.chat.type if hasattr(message.chat, 'type') else 'unknown'
    is_business = update.business_message is not None
    
    if not user_id or str(user_id) != str(ADMIN_ID):
        logger.info(f"Non-admin user {user_id} tried to use /help command")
        return
    
    if chat_type in ['group', 'supergroup']:
        chat_manager.save_group_chat(user_id, chat_id, chat_type)
        context.user_data['last_group_chat_id'] = chat_id
        context.bot_data['last_group_chat_id'] = chat_id
    
    help_text = "Spy Bot Help:\n\n"\
        "Admin Commands:\n"\
        "/spy on - Enable tracking and forwarding of edited/deleted messages\n"\
        "/spy off - Disable tracking\n"\
        "/who - Get user information\n\n"\
        "Fun Commands (available to all):\n"\
        "/random cube - Roll a dice\n"\
        "/random yn - Yes/No answer\n"\
        "/random q - Magic 8-ball response"
    
    if hasattr(context, 'sender'):
        logger.info(f"Command /help from {user_id} - using context.sender to chat_id: {context.sender.chat_id}")
        await context.sender.send_message(text=help_text)
    else:
        logger.info(f"Command /help from {user_id} - using direct send to chat_id: {chat_id}")
        await context.bot.send_message(chat_id=chat_id, text=help_text)

async def spy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SPY_ENABLED
    
    message = update.message or update.business_message
    if not message:
        logger.error("Neither message nor business_message found in update")
        return
    
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = message.chat_id
    chat_type = message.chat.type if hasattr(message.chat, 'type') else 'unknown'
    
    if not user_id or str(user_id) != str(ADMIN_ID):
        logger.info(f"Non-admin user {user_id} tried to use /spy command")
        return
    
    if chat_type in ['group', 'supergroup']:
        chat_manager.save_group_chat(user_id, chat_id, chat_type)
        context.user_data['last_group_chat_id'] = chat_id
        context.bot_data['last_group_chat_id'] = chat_id
    
    if hasattr(context, 'sender'):
        logger.info(f"Command /spy from {user_id} - using context.sender to chat_id: {context.sender.chat_id}")
        sender = context.sender
    else:
        logger.info(f"Command /spy from {user_id} - using direct send to chat_id: {chat_id}")
        async def direct_send(text, **kwargs):
            return await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        sender = type('', (), {'send_message': direct_send})()
    
    if not context.args:
        await sender.send_message(
            text=f"Current mode: {'ON' if SPY_ENABLED else 'OFF'}\nUse /spy on or /spy off"
        )
        return
    
    command = context.args[0].lower()
    
    if command == "on":
        SPY_ENABLED = True
        await sender.send_message(
            text="Spy mode is now ON. I will track edited and deleted messages."
        )
    elif command == "off":
        SPY_ENABLED = False
        await sender.send_message(
            text="Spy mode is now OFF. I will not track edited and deleted messages."
        )
    else:
        await sender.send_message(
            text="Unknown command. Use /spy on or /spy off"
        )

async def who_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.business_message
    if not message:
        logger.error("Neither message nor business_message found in update")
        return
    
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = message.chat_id
    chat_type = message.chat.type if hasattr(message.chat, 'type') else 'unknown'
    is_business = update.business_message is not None
    
    if not user_id or str(user_id) != str(ADMIN_ID):
        logger.info(f"Non-admin user {user_id} tried to use /who command")
        return
    
    if chat_type in ['group', 'supergroup']:
        chat_manager.save_group_chat(user_id, chat_id, chat_type)
        context.user_data['last_group_chat_id'] = chat_id
        context.bot_data['last_group_chat_id'] = chat_id
    
    if hasattr(context, 'sender'):
        logger.info(f"Command /who from {user_id} - using context.sender to chat_id: {context.sender.chat_id}")
        sender = context.sender
    else:
        logger.info(f"Command /who from {user_id} - using direct send to chat_id: {chat_id}")
        async def direct_send(text, **kwargs):
            return await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
        sender = type('', (), {'send_message': direct_send})()
    
    replied_message = message.reply_to_message
    if not replied_message:
        await sender.send_message(
            text="Please use this command as a reply to a message to get information about its sender."
        )
        return
    
    replied_user_id = replied_message.from_user.id if replied_message.from_user else "Unknown"
    replied_user_name = replied_message.from_user.first_name if replied_message.from_user else "Unknown"
    if replied_message.from_user and replied_message.from_user.last_name:
        replied_user_name += f" {replied_message.from_user.last_name}"
    if replied_message.from_user and replied_message.from_user.username:
        replied_user_name += f" (@{replied_message.from_user.username})"
    
    await sender.send_message(
        text=f"User ID: {replied_user_id}\nName: {replied_user_name}"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"=== MESSAGE HANDLER CALLED ===")
    logger.info(f"Update object type: {type(update).__name__}")
    
    if update.message:
        message = update.message
        logger.info(f"Message received: {message.message_id} from {message.from_user.id}")
    elif update.business_message:
        message = update.business_message
        logger.info(f"Business message received: {message.message_id} from {message.from_user.id}")
    else:
        logger.warning(f"Received update without message or business_message: {update}")
        return
    
    if not SPY_ENABLED:
        logger.info("Spy mode is disabled, ignoring message")
        return
    
    try:
        logger.info(f"Message full content: {message.to_dict()}")
        logger.info(f"Message has photo: {message.photo is not None and len(message.photo) > 0}")
        logger.info(f"Message has video: {message.video is not None}")
        logger.info(f"Message has voice: {message.voice is not None}")
        logger.info(f"Message has document: {message.document is not None}")
        logger.info(f"Message has animation: {message.animation is not None}")
    except Exception as e:
        logger.error(f"Error logging message details: {e}")
    
    message_store.store_message(message)
    
    chat_id = message.chat.id
    message_id = message.message_id
    logger.info(f"Processing message with chat_id={chat_id}, message_id={message_id}")
    
    has_media = False
    media_type = None
    
    if message.photo:
        has_media = True
        media_type = "photo"
        logger.info(f"Message contains photo")
    elif message.video:
        has_media = True
        media_type = "video"
        logger.info(f"Message contains video")
    elif message.voice:
        has_media = True
        media_type = "voice"
        logger.info(f"Message contains voice")
    elif message.audio:
        has_media = True
        media_type = "audio"
        logger.info(f"Message contains audio")
    elif message.document:
        has_media = True
        media_type = "document"
        logger.info(f"Message contains document")
    elif message.sticker:
        has_media = True
        media_type = "sticker"
        logger.info(f"Message contains sticker")
    
    if has_media:
        logger.info(f"Message contains media of type: {media_type}")
    
    message_store.store_message(message)
    
    test_message = message_store.get_message(chat_id, message_id)
    logger.info(f"Retrieved message: {test_message is not None}")

async def handle_edited_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"=== EDITED MESSAGE HANDLER CALLED ===")
    logger.info(f"Update object type: {type(update).__name__}")
    logger.info(f"Has edited_message: {update.edited_message is not None}")
    logger.info(f"Has edited_business_message: {update.edited_business_message is not None}")
    logger.info(f"Entire update: {update.to_dict()}")
    
    if not SPY_ENABLED:
        logger.info("Spy mode is disabled, ignoring edited message")
        return
        
    if update.edited_business_message:
        edited_message = update.edited_business_message
    else:
        edited_message = update.edited_message
    
    if edited_message is None:
        logger.warning(f"Received update without edited_message or edited_business_message: {update.to_dict()}")
        return
    
    # Проверяем, не от администратора ли сообщение
    user_id = edited_message.from_user.id if edited_message.from_user else None
    if user_id and str(user_id) == str(ADMIN_ID):
        logger.info(f"Ignoring edited message from admin user {user_id}")
        return
    
    chat_id = edited_message.chat.id
    message_id = edited_message.message_id
    logger.info(f"Processing edited message with chat_id={chat_id}, message_id={message_id}")
    logger.info(f"Message content: {edited_message.text if hasattr(edited_message, 'text') else '[NO TEXT]'}")
    logger.info(f"Edit date: {edited_message.edit_date}")
    logger.info(f"From user: {edited_message.from_user.id if edited_message.from_user else 'Unknown'}")
    logger.info(f"Is admin: {str(user_id) == str(ADMIN_ID) if user_id else False}")

    original_message = message_store.get_message(chat_id, message_id)
    
    user_id = edited_message.from_user.id if edited_message.from_user else "Unknown"
    user_name = edited_message.from_user.first_name if edited_message.from_user else "Unknown"
    if edited_message.from_user and edited_message.from_user.last_name:
        user_name += f" {edited_message.from_user.last_name}"
    if edited_message.from_user and edited_message.from_user.username:
        user_name += f" (@{edited_message.from_user.username})"
    
    chat_title = edited_message.chat.title if hasattr(edited_message.chat, 'title') and edited_message.chat.title else "Private Chat"
    
    current_time = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        if original_message:

            try:
                original_header = format_forward_header(original_message, "regular")
                original_content = format_message_content(original_message)
                
                if len(original_content) > 3000:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"{original_header}<b>❗ Original message:</b>",
                        parse_mode=constants.ParseMode.HTML
                    )
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=original_content,
                        parse_mode=constants.ParseMode.HTML
                    )
                else:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"{original_header}<b>❗ Original message:</b>\n\n{original_content}",
                        parse_mode=constants.ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"Error sending original message part: {e}")
            
            await forward_media(context.bot, ADMIN_ID, original_message)
            
            try:
                edited_header = format_forward_header(edited_message, "edited")
                edited_content = format_message_content(edited_message)
                
                if len(edited_content) > 3000:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=edited_header,
                        parse_mode=constants.ParseMode.HTML
                    )
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=edited_content,
                        parse_mode=constants.ParseMode.HTML
                    )
                else:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"{edited_header}{edited_content}",
                        parse_mode=constants.ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"Error sending edited message part: {e}")
            
            await forward_media(context.bot, ADMIN_ID, edited_message)
        else:
            try:
                edited_header = format_forward_header(edited_message, "edited")
                edited_content = format_message_content(edited_message)
                
                warning = "⚠️ <i>Original message not found in cache</i>\n\n"
                
                if len(edited_content) > 3000:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"{edited_header}{warning}",
                        parse_mode=constants.ParseMode.HTML
                    )
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=edited_content,
                        parse_mode=constants.ParseMode.HTML
                    )
                else:
                    await context.bot.send_message(
                        chat_id=ADMIN_ID,
                        text=f"{edited_header}{warning}{edited_content}",
                        parse_mode=constants.ParseMode.HTML
                    )
            except Exception as e:
                logger.error(f"Error sending edited message (no original): {e}")
                
            await forward_media(context.bot, ADMIN_ID, edited_message)
    except Exception as e:
        logger.error(f"Error sending edited message notification: {e}")
        logger.exception(e)
    
    message_store.store_message(edited_message)

async def handle_deleted_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

async def send_deleted_message(context: ContextTypes.DEFAULT_TYPE, message_data):
    pass

async def forward_media(bot, target_chat_id, message):
    logger.info(f"Forward media called for message: {message.message_id} in chat {message.chat.id}")
    
    original_caption = message.caption or ""
    
    try:
        if message.photo:
            logger.info(f"Forwarding photo for message {message.message_id}")
            try:
                file = await bot.get_file(message.photo[-1].file_id)
                photo_bytes = await bot.download_file(file.file_path)
                
                from io import BytesIO
                photo_io = BytesIO(photo_bytes)
                photo_io.name = "photo.jpg"
                
                await bot.send_photo(
                    chat_id=target_chat_id,
                    photo=photo_io,
                    caption=f"📸 Saved photo:\n{original_caption}"
                )
                logger.info(f"Photo forwarded successfully")
                return
            except Exception as e:
                logger.error(f"Error forwarding photo as file, trying with file_id: {e}")
                await bot.send_photo(
                    chat_id=target_chat_id,
                    photo=message.photo[-1].file_id,
                    caption=f"📸 Photo:\n{original_caption}"
                )
                return
        
        elif message.video:
            logger.info(f"Forwarding video for message {message.message_id}")
            try:
                file = await bot.get_file(message.video.file_id)
                video_bytes = await bot.download_file(file.file_path)
                
                from io import BytesIO
                video_io = BytesIO(video_bytes)
                video_io.name = "video.mp4"
                
                await bot.send_video(
                    chat_id=target_chat_id,
                    video=video_io,
                    caption=f"🎬 Saved video:\n{original_caption}"
                )
                logger.info(f"Video forwarded successfully")
                return
            except Exception as e:
                logger.error(f"Error forwarding video as file, trying with file_id: {e}")
                await bot.send_video(
                    chat_id=target_chat_id,
                    video=message.video.file_id,
                    caption=f"🎬 Video:\n{original_caption}"
                )
                return
        
        elif message.voice:
            logger.info(f"Forwarding voice for message {message.message_id}")
            try:
                file = await bot.get_file(message.voice.file_id)
                voice_bytes = await bot.download_file(file.file_path)
                
                from io import BytesIO
                voice_io = BytesIO(voice_bytes)
                voice_io.name = "voice.ogg"
                
                await bot.send_voice(
                    chat_id=target_chat_id,
                    voice=voice_io,
                    caption=f"🔊 Saved voice message:\n{original_caption}"
                )
                logger.info(f"Voice forwarded successfully")
                return
            except Exception as e:
                logger.error(f"Error forwarding voice as file, trying with file_id: {e}")
                await bot.send_voice(
                    chat_id=target_chat_id,
                    voice=message.voice.file_id,
                    caption=f"🔊 Voice message:\n{original_caption}"
                )
                return
        
        elif message.audio:
            logger.info(f"Forwarding audio for message {message.message_id}")
            await bot.send_audio(
                chat_id=target_chat_id,
                audio=message.audio.file_id,
                caption=f"🎵 Audio:\n{original_caption}"
            )
            return
        
        elif message.document:
            logger.info(f"Forwarding document for message {message.message_id}")
            await bot.send_document(
                chat_id=target_chat_id,
                document=message.document.file_id,
                caption=f"📄 Document:\n{original_caption}"
            )
            return
        
        elif message.sticker:
            logger.info(f"Forwarding sticker for message {message.message_id}")
            await bot.send_sticker(
                chat_id=target_chat_id,
                sticker=message.sticker.file_id
            )
            if original_caption:
                await bot.send_message(
                    chat_id=target_chat_id,
                    text=f"🏷 Sticker caption:\n{original_caption}"
                )
            return
            
        elif message.animation:
            logger.info(f"Forwarding animation for message {message.message_id}")
            await bot.send_animation(
                chat_id=target_chat_id,
                animation=message.animation.file_id,
                caption=f"Animation:\n{original_caption}"
            )
            return
        
        elif message.video_note:
            logger.info(f"Forwarding video note for message {message.message_id}")
            await bot.send_video_note(
                chat_id=target_chat_id,
                video_note=message.video_note.file_id
            )
            return
        
        elif message.location:
            logger.info(f"Forwarding location for message {message.message_id}")
            await bot.send_location(
                chat_id=target_chat_id,
                latitude=message.location.latitude,
                longitude=message.location.longitude
            )
            return
            
        else:
            logger.info(f"No media found in message {message.message_id}")
            
    except Exception as e:
        logger.error(f"Error in forward_media: {e}")
        logger.exception(e)

async def who_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to get user information"""
    message = update.message or update.business_message
    if not message:
        logger.error("Neither message nor business_message found in update")
        return
        
    chat_id = message.chat_id
    
    if not context.args:
        user = update.effective_user
    else:
        try:
            user_id = int(context.args[0])
            chat_member = await context.bot.get_chat_member(chat_id, user_id)
            user = chat_member.user
        except (ValueError, Exception) as e:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Error: {str(e)}\nUsage: /who [user_id]"
            )
            return
    
    user_info = [
        f"🔹 User ID: {user.id}",
        f"🔹 Full Name: {user.first_name} {user.last_name or ''}".strip(),
    ]
    
    if user.username:
        user_info.append(f"🔹 Username: @{user.username}")
    else:
        user_info.append(f"🔹 Username: None")
    
    has_photo = False
    try:
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        has_photo = photos.total_count > 0
    except:
        pass
    
    user_info.append(f"🔹 Has Profile Photo: {'Yes' if has_photo else 'No'}")
    user_info.append(f"🔹 Is Bot: {'Yes' if user.is_bot else 'No'}")
    
    if user.language_code:
        user_info.append(f"🔹 Language Code: {user.language_code}")
    
    if user.id < 100000000:
        registration = "2013 or earlier"
    elif user.id < 200000000:
        registration = "2014-2015"
    elif user.id < 400000000:
        registration = "2016-2017"
    elif user.id < 900000000:
        registration = "2018-2019"
    elif user.id < 1500000000:
        registration = "2020-2021"
    elif user.id < 5000000000:
        registration = "2022-2023"
    else:
        registration = "2024 or later"
    
    user_info.append(f"🔹 Estimated Registration: {registration}")
    
    try:
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo = photos.photos[0][-1]
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=photo.file_id,
                caption="\n".join(user_info)
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="\n".join(user_info)
            )
    except Exception as e:
        await context.bot.send_message(
            chat_id=chat_id,
            text="\n".join(user_info)
        )
        logger.error(f"Error getting user photo: {e}")

async def check_deleted_messages(context: ContextTypes.DEFAULT_TYPE):
    if not SPY_ENABLED:
        return
    
    logger.info("Checking for deleted messages...")
    
    try:
        for key, message_data in list(message_store.messages.items()):
            if message_data.get('deleted'):
                continue
                
            chat_id, message_id = key.split(':')
            
            chat_id = int(chat_id)
            message_id = int(message_id)
            
            logger.info(f"Checking if message {message_id} in chat {chat_id} still exists...")
            
            try:
                message = message_data['message']
                if hasattr(message, 'edit_date') and message.edit_date:
                    logger.debug(f"Skipping edited message {message_id} in chat {chat_id}")
                    continue
                
                now = datetime.now(timezone.utc)
                msg_time = message.date
                time_diff = (now - msg_time).total_seconds()
                
                if time_diff < 30:
                    logger.info(f"Message {message_id} is too recent ({time_diff} sec), skipping")
                    continue
                
                deletion_confirmed = False
                
                try:
                    from telegram.error import BadRequest
                    
                    chat = await context.bot.get_chat(chat_id)
                    
                    await context.bot.copy_message(
                        chat_id=ADMIN_ID,
                        from_chat_id=chat_id,
                        message_id=message_id,
                        disable_notification=True
                    )
                    logger.debug(f"Message {message_id} in chat {chat_id} still exists (copy successful)")
                    
                except BadRequest as e:
                    error_text = str(e).lower()
                    if "message to copy not found" in error_text or "message not found" in error_text:
                        deletion_confirmed = True
                        logger.info(f"Message {message_id} in chat {chat_id} was DELETED (not found)")
                    else:
                        logger.debug(f"Non-deletion error: {e}")
                
                except Exception as e:
                    logger.debug(f"Chat {chat_id} not accessible anymore: {e}")
                    continue
                
                if deletion_confirmed:
                    logger.info(f"Message {message_id} in chat {chat_id} was DELETED (confirmed)")
                    
                    message_data['deleted'] = True
                    
                    try:
                        header = format_forward_header(message, "deleted")
                        
                        sent_message = await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"{header}{format_message_content(message)}",
                            parse_mode=constants.ParseMode.HTML
                        )
                        logger.info(f"Sent deleted message notification: {sent_message.message_id}")
                        
                        await forward_media(context.bot, ADMIN_ID, message)
                    
                    except Exception as media_error:
                        logger.error(f"Error sending deleted message notification: {media_error}")
            
            except Exception as e:
                logger.error(f"Error processing message {message_id} in chat {chat_id}: {e}")
                continue
        
        message_store.cleanup_old_messages()
    
    except Exception as e:
        logger.error(f"Error in check_deleted_messages job: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Error handler for the bot"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    import traceback
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)
    
    logger.error(f"Traceback: {tb_string}")
    
    error_message = f"An error occurred: {context.error}\n\n"
    
    if update:
        error_message += f"Update: {update}\n"
        if update.effective_user:
            error_message += f"User: {update.effective_user.id}\n"
        if update.effective_chat:
            error_message += f"Chat: {update.effective_chat.id}\n"
        if update.effective_message:
            error_message += f"Message: {update.effective_message.id}\n"
    
    if len(tb_string) > 3000:
        tb_string = tb_string[:3000] + "...\n(truncated)"
    
    error_message += f"\nTraceback:\n{tb_string}"
    
    if len(error_message) > 4096:
        for i in range(0, len(error_message), 4096):
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=error_message[i:i+4096]
                )
            except Exception as e:
                logger.error(f"Failed to send error message to admin: {e}")
    else:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=error_message
            )
        except Exception as e:
            logger.error(f"Failed to send error message to admin: {e}")

async def check_deleted_messages(context: ContextTypes.DEFAULT_TYPE):
    """Periodic task to check for deleted messages"""
    if not SPY_ENABLED:
        return
    logger.info("Checking for deleted messages...")
    
    try:
        for key, message_data in list(message_store.messages.items()):
            # Пропускаем уже обработанные удаленные сообщения
            if message_data.get('deleted'):
                continue
                
            chat_id, message_id = key.split(':')
            
            chat_id = int(chat_id)
            message_id = int(message_id)
            
            message = message_data['message']
            
            # Проверяем, не от администратора ли сообщение
            user_id = message.from_user.id if message.from_user else None
            if user_id and str(user_id) == str(ADMIN_ID):
                logger.info(f"Skipping message {message_id} from admin user {user_id}")
                # Удаляем сообщение админа из отслеживания
                del message_store.messages[key]
                continue
            
            original_date = message.date
            current_time = datetime.now(timezone.utc)
            time_diff = (current_time - original_date).total_seconds()
            
            # Увеличиваем время ожидания перед проверкой
            if time_diff < 120:  # 2 минуты вместо 30 секунд
                logger.info(f"Message {message_id} is too recent ({time_diff:.1f} sec), skipping check")
                continue
            
            # Добавляем счетчик проверок
            message_data['check_count'] = message_data.get('check_count', 0) + 1
            
            # Проверяем только каждое третье сообщение
            if message_data['check_count'] % 3 != 1:
                continue
                
            # После 10 проверок прекращаем отслеживание
            if message_data['check_count'] > 10:
                logger.info(f"Message {message_id} checked {message_data['check_count']} times, removing from tracking")
                del message_store.messages[key]
                continue
            
            logger.info(f"Checking if message {message_id} in chat {chat_id} still exists... (check #{message_data['check_count']})")
            
            try:
                from telegram.error import BadRequest
                
                is_deleted = False
                
                # Проверяем существование сообщения с помощью прямого запроса
                try:
                    try:
                        # Проверяем, что чат доступен
                        await context.bot.get_chat(chat_id=chat_id)
                        
                        # Вместо copy_message используем forward_message, чтобы проверить существование
                        # Создаем временный чат для проверки
                        try:
                            # Пытаемся получить сообщение напрямую
                            await context.bot.get_message(
                                chat_id=chat_id,
                                message_id=message_id
                            )
                            logger.debug(f"Message {message_id} still exists (get_message successful)")
                        except Exception as e:
                            # Если get_message не работает, пробуем копирование
                            try:
                                await context.bot.copy_message(
                                    chat_id=chat_id,
                                    from_chat_id=chat_id,
                                    message_id=message_id,
                                    disable_notification=True
                                )
                                logger.debug(f"Message {message_id} still exists (copy test successful)")
                            except BadRequest as e:
                                error_text = str(e).lower()
                                if ("message to copy not found" in error_text or 
                                    "message not found" in error_text or
                                    "message to forward not found" in error_text or
                                    "message can't be found" in error_text):
                                    is_deleted = True
                                else:
                                    logger.warning(f"API error, but message probably exists: {e}")
                    except BadRequest as e:
                        error_text = str(e).lower()
                        if ("message to copy not found" in error_text or 
                            "message not found" in error_text or
                            "message to forward not found" in error_text or
                            "message can't be found" in error_text):
                            is_deleted = True
                        else:
                            logger.warning(f"API error, but message probably exists: {e}")
                except Exception as e:
                    logger.error(f"Error checking message: {e}")
                    continue
                
                if is_deleted:
                    logger.info(f"Message {message_id} in chat {chat_id} was DELETED (confirmed)")
                    message_data['deleted'] = True
                    
                    try:
                        user_id = message.from_user.id if message.from_user else "Unknown"
                        username = message.from_user.username if message.from_user and message.from_user.username else ""
                        chat_title = message.chat.title if message.chat and message.chat.title else message.chat.id
                        
                        if username:
                            header = f"<b>Forwarded from @{username} ({user_id}) in {chat_title}</b>\n"
                        else:
                            header = f"<b>Forwarded from {user_id} in {chat_title}</b>\n"
                            
                        delete_info = "🗑 <b>DELETED MESSAGE</b>\n"
                        sent_time = message.date.strftime('%Y-%m-%d %H:%M:%S')
                        delete_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                        time_info = f"<i>Sent at {sent_time}, deleted at {delete_time}</i>\n"
                        
                        sent_message = await context.bot.send_message(
                            chat_id=ADMIN_ID,
                            text=f"{header}{delete_info}{time_info}\n{format_message_content(message)}",
                            parse_mode=constants.ParseMode.HTML
                        )
                        logger.info(f"Sent deleted message notification: {sent_message.message_id}")
                        
                        await forward_media(context.bot, ADMIN_ID, message)
                    except Exception as media_error:
                        logger.error(f"Error sending deleted message notification: {media_error}")
            except Exception as e:
                logger.error(f"Error checking if message {message_id} exists: {e}")
    except Exception as e:
        logger.error(f"Error in check_deleted_messages job: {e}")

    message_store.cleanup_old_messages()
