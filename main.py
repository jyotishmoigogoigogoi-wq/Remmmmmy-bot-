import os
import asyncio
from flask import Flask
from threading import Thread
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
import yt_dlp

# ========== CONFIG ==========
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")

# ========== FLASK (Keep Alive) ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "🎵 Music Bot is Running!"

@app.route('/health')
def health():
    return {"status": "alive"}, 200

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

# ========== BOT SETUP ==========
bot = Client(
    "music_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    session_string=SESSION_STRING,
    in_memory=True
)

call = PyTgCalls(bot)

# ========== HELPERS ==========
def get_audio(query):
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
    }
    
    if not query.startswith(('http://', 'https://', 'youtu')):
        query = f"ytsearch1:{query}"
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        
        formats = [f for f in info.get('formats', []) if f.get('acodec') != 'none']
        if formats:
            best = max(formats, key=lambda x: x.get('abr', 0) or 0)
            return {'url': best['url'], 'title': info.get('title', 'Unknown')}
        return None

# ========== COMMANDS ==========
@bot.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("""
🎵 **Music UserBot**

`!join` - Join voice chat
`!play <song>` - Play music  
`!leave` - Leave voice chat
    """)

@bot.on_message(filters.command("join"))
async def join(client, message):
    try:
        await call.join_group_call(
            message.chat.id,
            AudioPiped("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
        )
        await message.reply("✅ Joined voice chat!")
    except Exception as e:
        await message.reply(f"❌ {e}")

@bot.on_message(filters.command("play"))
async def play(client, message):
    if len(message.command) < 2:
        return await message.reply("Usage: `!play <song>`")
    
    query = " ".join(message.command[1:])
    status = await message.reply(f"🔍 Searching: `{query}`")
    
    try:
        audio = get_audio(query)
        if not audio:
            return await status.edit("❌ Not found!")
        
        try:
            await call.change_stream(message.chat.id, AudioPiped(audio['url']))
        except:
            await call.join_group_call(message.chat.id, AudioPiped(audio['url']))
        
        await status.edit(f"▶️ **Playing:** {audio['title']}")
    except Exception as e:
        await status.edit(f"❌ {e}")

@bot.on_message(filters.command("leave"))
async def leave(client, message):
    try:
        await call.leave_group_call(message.chat.id)
        await message.reply("👋 Left!")
    except Exception as e:
        await message.reply(f"❌ {e}")

# ========== START ==========
if __name__ == "__main__":
    # Start Flask in thread
    Thread(target=run_flask, daemon=True).start()
    
    # Start bot
    print("🚀 Starting bot...")
    call.run()
    
