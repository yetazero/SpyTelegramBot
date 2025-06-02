import sys
import logging
import traceback
from gui import main as start_gui

if __name__ == "__main__":
    try:
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO,
            filename='spy_bot_gui.log'
        )
        logger = logging.getLogger("SpyBotGUI")
        
        logger.info("Starting Telegram Spy Bot GUI")
        
        start_gui()
        
    except Exception as e:
        print(f"Error starting Telegram Spy Bot: {e}")
        traceback.print_exc()
        
        try:
            logger.error(f"Error starting Telegram Spy Bot: {e}")
            logger.error(traceback.format_exc())
        except:
            pass
        
        input("Press Enter to exit...")
        sys.exit(1)
