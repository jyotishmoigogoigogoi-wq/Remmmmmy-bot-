import os
import asyncio
from pyrogram import Client, filters
from pytgcalls import PyTgCalls
from pytgcalls.types.input_stream import AudioPiped
from collections import deque
import yt_dlp

# ================= CONFIG =================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION_STRING")

AUTHORIZED_USERS = list(map(int, os.getenv("SUDO_USERS", "").split()))

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ================= INIT =================
app = Client("userbot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION)
call = PyTgCalls(app)

queues = {}

# ================= UTIL =================
def is_allowed(user_id):
    return user_id in AUTHORIZED_USERS

def get_queue(chat_id):
    if chat_id not in queues:
        queues[chat_id] = deque()
    return queues[chat_id]

def download_audio(query):
    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=True)
        entry = info["entries"][0]
        return ydl.prepare_filename(entry), entry["title"]

# ================= PLAYER =================
async def play_next(chat_id):
    queue = get_queue(chat_id)

    if not queue:
        await call.leave_group_call(chat_id)
        return

    file, title = queue.popleft()

    await call.change_stream(
        chat_id,
        AudioPiped(file)
    )

# ================= COMMANDS =================
@app.on_message(filters.command("play"))
async def play(_, msg):
    if not is_allowed(msg.from_user.id):
        return await msg.reply("Not allowed")

    if len(msg.command) < 2:
        return await msg.reply("Give song name")

    query = msg.text.split(None, 1)[1]
    status = await msg.reply("Downloading...")

    file, title = await asyncio.to_thread(download_audio, query)

    queue = get_queue(msg.chat.id)
    queue.append((file, title))

    if len(queue) == 1:
        try:
            await call.join_group_call(
                msg.chat.id,
                AudioPiped(file)
            )
        except:
            await call.change_stream(
                msg.chat.id,
                AudioPiped(file)
            )

        await status.edit(f"Playing: {title}")
    else:
        await status.edit(f"Queued: {title}")

@app.on_message(filters.command("skip"))
async def skip(_, msg):
    if not is_allowed(msg.from_user.id):
        return

    await play_next(msg.chat.id)
    await msg.reply("Skipped ⏭️")

@app.on_message(filters.command("stop"))
async def stop(_, msg):
    if not is_allowed(msg.from_user.id):
        return

    queues[msg.chat.id] = deque()
    await call.leave_group_call(msg.chat.id)
    await msg.reply("Stopped ❌")

@app.on_message(filters.command("pause"))
async def pause(_, msg):
    if not is_allowed(msg.from_user.id):
        return

    await call.pause_stream(msg.chat.id)
    await msg.reply("Paused ⏸️")

@app.on_message(filters.command("resume"))
async def resume(_, msg):
    if not is_allowed(msg.from_user.id):
        return

    await call.resume_stream(msg.chat.id)
    await msg.reply("Resumed ▶️")

# ================= EVENTS =================
@call.on_stream_end()
async def stream_end(_, update):
    chat_id = update.chat_id
    await play_next(chat_id)

# ================= START =================
async def main():
    await app.start()
    await call.start()
    print("Userbot Music Started 🔥")
    await idle()

from pyrogram import idle
asyncio.run(main())
