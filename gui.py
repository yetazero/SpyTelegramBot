import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import sys
import signal
import logging
import time
from PIL import Image, ImageDraw
import pystray
from io import BytesIO
import tempfile

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot_thread = None
bot_process = None
tray_icon = None
root = None
is_running = False

def create_square_icon(size=64, color='black'):
    """Create a black square icon for the tray"""
    img = Image.new('RGB', (size, size), color='white')
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (size, size)], fill=color)
    return img

def on_exit(icon, item):
    """Exit the application when tray icon exit is selected"""
    global root, is_running
    logger.info("Exiting application from tray")
    is_running = False
    stop_bot()
    icon.stop()
    if root:
        root.destroy()
    sys.exit(0)

def show_window(icon, item):
    """Show the main window when tray icon is clicked"""
    global root
    logger.info("Showing main window from tray")
    if root:
        root.deiconify()
        root.lift()
        root.focus_force()

def hide_to_tray():
    """Hide the main window to tray"""
    global root
    logger.info("Hiding to tray")
    root.withdraw()

def update_bot_status(running):
    """Update the UI status indicator"""
    global status_label, start_button, stop_button, is_running
    is_running = running
    
    if running:
        status_label.config(text="Status: Running", foreground="green")
        start_button.config(state=tk.DISABLED)
        stop_button.config(state=tk.NORMAL)
    else:
        status_label.config(text="Status: Stopped", foreground="red")
        start_button.config(state=tk.NORMAL)
        stop_button.config(state=tk.DISABLED)

def start_bot():
    """Start the Telegram Bot in a separate thread"""
    global bot_thread, is_running
    
    if is_running:
        return
    
    logger.info("Starting the bot...")
    
    try:
        from run import run_bot
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        update_bot_status(True)
        logger.info("Bot started successfully!")
        
    except Exception as e:
        logger.exception(f"Error starting bot: {e}")
        messagebox.showerror("Error", f"Failed to start bot: {e}")
        update_bot_status(False)

def stop_bot():
    """Stop the running Telegram Bot"""
    global bot_thread, is_running
    
    if not is_running:
        return
        
    logger.info("Stopping the bot...")
    
    try:
        from run import stop_bot
        stop_bot()
        
        time.sleep(1)
        
        update_bot_status(False)
        logger.info("Bot stopped successfully!")
        
    except Exception as e:
        logger.exception(f"Error stopping bot: {e}")
        messagebox.showerror("Error", f"Failed to stop bot: {e}")

def create_ui():
    """Create the main UI window"""
    global root, status_label, start_button, stop_button, tray_icon
    
    root = tk.Tk()
    root.title("Telegram Spy Bot")
    root.geometry("300x200")
    root.resizable(False, False)
    
    try:
        icon_img = create_square_icon()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ico') as temp_icon:
            icon_img.save(temp_icon.name)
            root.iconbitmap(temp_icon.name)
            root.after(1000, lambda: os.unlink(temp_icon.name))
    except Exception as e:
        logger.error(f"Failed to set window icon: {e}")
        
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    title_label = ttk.Label(main_frame, text="Telegram Spy Bot Control", font=("Helvetica", 14, "bold"))
    title_label.pack(pady=(0, 20))

    status_label = ttk.Label(main_frame, text="Status: Stopped", foreground="red")
    status_label.pack(pady=(0, 10))
    
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(pady=10)
    
    start_button = ttk.Button(button_frame, text="Start Bot", command=start_bot)
    start_button.pack(side=tk.LEFT, padx=5)
    
    stop_button = ttk.Button(button_frame, text="Stop Bot", command=stop_bot, state=tk.DISABLED)
    stop_button.pack(side=tk.LEFT, padx=5)
    
    tray_button = ttk.Button(main_frame, text="Hide to Tray", command=hide_to_tray)
    tray_button.pack(pady=(10, 0))
    
    icon_image = create_square_icon()
    
    menu = (
        pystray.MenuItem('Show', show_window),
        pystray.MenuItem('Exit', on_exit)
    )
    
    tray_icon = pystray.Icon("spy_bot", icon_image, "Telegram Spy Bot", menu)
    
    def on_close():
        if messagebox.askyesno("Confirmation", "Do you want to minimize to tray?"):
            hide_to_tray()
        else:
            on_exit(tray_icon, None)
    
    root.protocol("WM_DELETE_WINDOW", on_close)
    
    tray_thread = threading.Thread(target=tray_icon.run)
    tray_thread.daemon = True
    tray_thread.start()
    
    return root

def main():
    """Main function to start the GUI"""
    root = create_ui()
    root.mainloop()

if __name__ == "__main__":
    main()
