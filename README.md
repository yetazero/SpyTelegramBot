# Telegram Spy Bot

This project is a Telegram bot designed for monitoring messages and providing additional utility commands. It features a graphical user interface for easy management, supports both standard messages and messages from Telegram Business accounts, and includes a set of commands that generate random results.

## Functional Capabilities

### Spy Mode
When this mode is activated, the bot forwards messages from monitored chats (groups and supergroups) to the specified administrator ID. Notifications for deleted or edited messages are included.

### Telegram Business Support
The bot can process messages from Telegram Business accounts, allowing commands to be used directly in these chats. This feature is particularly useful for efficient business correspondence management. **Please note:** The bot's compatibility with messages from Telegram Business accounts does not mean that a Telegram Premium subscription is required for its operation.

### Random Choice Commands
A series of utility commands for interactive engagement is included:
* `/random cube`: Simulates a six-sided die roll, generating a random number from 1 to 6.
* `/random yn`: Provides a binary answer ('Yes' or 'No').
* `/random q`: Functions as a 'Magic 8-Ball', offering random answers to questions.
* `/random r`: Simulates a game of 'Russian roulette' (intended for entertainment purposes only).

## Setup and Installation

### Prerequisites
* Python version 3.8 or higher.
* `python-telegram-bot` library.
* `Pillow` library (PIL fork) for displaying icons in the GUI.
* `pystray` library for system tray functionality.

Required Python packages can be installed using pip:
```bash
pip install python-telegram-bot Pillow pystray
## Configuration

### Creating `config.ini`
In the root directory of the project, create a file named `config.ini` with the following content:

```ini
[Bot]
TOKEN = YOUR_BOT_TOKEN
ADMIN_ID = YOUR_TELEGRAM_ADMIN_ID

[Settings]
MESSAGE_LIFETIME = 86400 ; Messages will be stored for the specified number of seconds (e.g., 24 hours)
* Replace `YOUR_BOT_TOKEN` with the API token obtained from `BotFather` in Telegram.
* Replace `YOUR_TELEGRAM_ADMIN_ID` with your Telegram user ID. Messages and notifications will be forwarded to this ID when monitoring mode is activated.

### Starting the Bot

#### Using the Command Line (For testing or non-GUI environments)
The bot can be launched directly from the command line using `run.py`. This method is preferable for server environments or when a graphical interface is not available.

```bash
python run.py
