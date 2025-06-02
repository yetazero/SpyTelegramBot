import os
import sys
import signal
import logging
import socket
import tempfile
import atexit
import configparser

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

LOCK_FILE = os.path.join(tempfile.gettempdir(), 'spy_bot.lock')

_lock_socket = None

def check_single_instance():
    global _lock_socket
    
    _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        _lock_socket.bind(('localhost', 47200))
        _lock_socket.listen(1)
        
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
            
        atexit.register(cleanup_lock)
        return True
    except socket.error:
        if _lock_socket:
            _lock_socket.close()
            _lock_socket = None
        return False

def cleanup_lock():
    global _lock_socket
    logger.info("Cleaning up lock file and socket...")
    
    if os.path.exists(LOCK_FILE):
        try:
            os.unlink(LOCK_FILE)
            logger.info("Lock file removed")
        except Exception as e:
            logger.error(f"Failed to remove lock file: {e}")
    
    if _lock_socket:
        try:
            _lock_socket.close()
            logger.info("Lock socket closed")
        except Exception as e:
            logger.error(f"Failed to close socket: {e}")
        _lock_socket = None

def check_config():
    """Check if config file is properly set up"""
    config = configparser.ConfigParser()
    config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    if not os.path.exists(config_file):
        logger.error("Config file not found! Create config.ini file.")
        return False
    
    config.read(config_file)
    
    if 'Bot' not in config:
        logger.error("Bot section not found in config file!")
        return False
    
    if 'TOKEN' not in config['Bot'] or config['Bot']['TOKEN'] == 'your_bot_token_here':
        logger.error("Bot TOKEN not set in config file!")
        return False
    
    if 'ADMIN_ID' not in config['Bot'] or config['Bot']['ADMIN_ID'] == 'your_admin_id_here':
        logger.error("Admin ID not set in config file!")
        return False
    
    return True

def signal_handler(sig, frame):
    logger.info("Stopping bot (received signal)...")
    cleanup_lock()
    sys.exit(0)

_app_instance = None

def run_bot():
    """Run the Telegram bot with proper error handling"""
    global _app_instance
    
    if not check_single_instance():
        logger.error("Error: Another instance of Spy Bot is already running.")
        return False
    
    if not check_config():
        logger.error("Error: Invalid configuration")
        return False
    
    import main
    from main import create_application

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting Spy Bot (single instance)...")
    try:
        _app_instance = create_application()
        main.start_bot(_app_instance)
        return True
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
        cleanup_lock()
        return False
    except Exception as e:
        logger.error(f"Bot crashed with error: {e}")
        cleanup_lock()
        return False

def stop_bot():
    """Stop the running bot instance"""
    global _app_instance
    
    logger.info("Stopping the bot...")
    try:
        if _app_instance:
            _app_instance.stop()
            _app_instance.shutdown()
            _app_instance = None
            logger.info("Bot stopped successfully")
            cleanup_lock()
            return True
        else:
            logger.warning("No running bot instance found")
            return False
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return False

def is_bot_running():
    """Check if the bot is currently running"""
    global _app_instance
    return _app_instance is not None

if __name__ == "__main__":
    if not run_bot():
        sys.exit(1)
