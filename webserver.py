from flask import Flask
import os
import threading
from main import bot

app = Flask(__name__)

@app.route('/')
def home():
    return "Discord Bot is running!"

def run_bot():
    bot.run(os.getenv('DISCORD_TOKEN'))

def start():
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    return bot_thread

if __name__ == "__main__":
    thread = start()
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
