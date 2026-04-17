import os
import uuid
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pyrogram import Client, filters
from pyrogram.types import Message
import database as db
from torrent import create_torrent_file

# Config
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN") 
STORE_CHANNEL = int(os.environ.get("STORE_CHANNEL"))
DOMAIN = os.environ.get("DOMAIN").rstrip("/")

app = FastAPI()
tg_app = Client("torrent_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.on_event("startup")
async def startup_event():
    await tg_app.start()

@tg_app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    await message.reply_text("👋 **WebSeed Torrent Bot Online!**\nSend me a file to generate a permanent torrent.")

@tg_app.on_message((filters.document | filters.video) & filters.private)
async def handle_file(client: Client, message: Message):
    status = await message.reply_text("⏳ Processing file...")
    
    # Forward to the permanent storage channel
    fwd = await message.copy(STORE_CHANNEL)
    
    file_hash = uuid.uuid4().hex
    file_name = message.document.file_name if message.document else message.video.file_name
    file_size = message.document.file_size if message.document else message.video.file_size
    
    await db.save_file_data(file_hash, fwd.id, file_name, file_size)
    
    await status.edit_text("⚙️ Creating .torrent with Web-Seed...")
    torrent_path = await create_torrent_file(client, fwd, file_hash, DOMAIN)
    
    await message.reply_document(
        document=torrent_path,
        caption=f"✅ **Torrent Ready!**\n\nOpen this in qBittorrent. It will download directly from Telegram at max speed."
    )
    os.remove(torrent_path)

@app.get("/stream/{file_hash}")
async def stream_engine(file_hash: str, request: Request):
    data = await db.get_file_data(file_hash)
    if not data: raise HTTPException(status_code=404)

    msg = await tg_app.get_messages(STORE_CHANNEL, data["message_id"])
    
    # Handle byte-range requests from Torrent Apps
    range_header = request.headers.get('Range', 'bytes=0-')
    ranges = range_header.replace("bytes=", "").split("-")
    start = int(ranges[0]) if ranges[0] else 0
    end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else data["size"] - 1
    chunk_size = (end - start) + 1

    async def gen():
        async for chunk in tg_app.stream_media(msg, offset=start, limit=chunk_size):
            yield chunk

    return StreamingResponse(gen(), status_code=206, headers={
        'Content-Range': f'bytes {start}-{end}/{data["size"]}',
        'Content-Length': str(chunk_size),
        'Accept-Ranges': 'bytes',
    })
