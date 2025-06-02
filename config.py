import configparser
import os
import json

config = configparser.ConfigParser()
config_file = os.path.join(os.path.dirname(__file__), 'config.ini')
config.read(config_file)

TOKEN = config.get('Bot', 'TOKEN', fallback=os.environ.get("TELEGRAM_BOT_TOKEN", ""))
ADMIN_ID = int(config.get('Bot', 'ADMIN_ID', fallback=os.environ.get("ADMIN_ID", 0)))

MESSAGE_LIFETIME = int(config.get('Settings', 'MESSAGE_LIFETIME', fallback=86400))

STATE_FILE = os.path.join(os.path.dirname(__file__), 'bot_state.json')

SPY_ENABLED = False

def save_state():
    """
    Saves the bot state to a file
    """
    state = {
        'spy_enabled': SPY_ENABLED
    }
    
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Error saving bot state: {e}")

def load_state():
    """
    Loads the bot state from a file
    """
    global SPY_ENABLED
    
    if not os.path.exists(STATE_FILE):
        return
    
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            SPY_ENABLED = state.get('spy_enabled', False)
    except Exception as e:
        print(f"Error loading bot state: {e}")

load_state()
