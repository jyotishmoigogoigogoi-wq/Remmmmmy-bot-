import os
import asyncio
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
from yt_dlp import YoutubeDL

# --- Flask Health Check Setup ---
# Render expects a web service to bind to a port.
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Telegram Bot Logic ---
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
SESSION_STRING = os.environ.get("SESSION_STRING")

bot = Client("MusicBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
assistant = Client("Assistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)
call_py = PyTgCalls(assistant)

ydl_opts = {"format": "bestaudio/best", "quiet": True, "no_warnings": True}

@bot.on_message(filters.command("play") & filters.group)
async def play_handler(_, message):
    if len(message.command) < 2:
        return await message.reply("Usage: /play [song name or link]")
    
    query = " ".join(message.command[1:])
    m = await message.reply("🔎 Searching...")
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            results = ydl.extract_info(f"ytsearch:{query}", download=False)['entries']
            if not results:
                return await m.edit("❌ No results found.")
            info = results[0]
            url, title = info['url'], info['title']
        
        await call_py.join_group_call(message.chat.id, AudioPiped(url))
        await m.edit(f"▶️ **Playing:** {title}")
    except Exception as e:
        await m.edit(f"❌ Error: {str(e)}")

@bot.on_message(filters.command("stop") & filters.group)
async def stop_handler(_, message):
    try:
        await call_py.leave_group_call(message.chat.id)
        await message.reply("⏹ Stopped.")
    except:
        await message.reply("❌ Nothing is playing.")

async def main():
    # Start health check server in background
    Thread(target=run_flask, daemon=True).start()
    
    await bot.start()
    await assistant.start()
    await call_py.start()
    print("Hybrid Bot is Online with Health Check!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
