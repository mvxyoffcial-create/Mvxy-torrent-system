import hashlib
import os
import bencode
from pyrogram import Client
from pyrogram.types import Message

PIECE_LENGTH = 524288  # 512 KB pieces

async def create_torrent_file(client: Client, message: Message, file_hash: str, domain: str) -> str:
    file_name = message.document.file_name or message.video.file_name
    file_size = message.document.file_size or message.video.file_size
    temp_path = f"./temp_{file_hash}"
    
    # Download temporarily to generate SHA-1 hashes for pieces
    await client.download_media(message, file_name=temp_path)
    
    pieces = bytearray()
    with open(temp_path, "rb") as f:
        while True:
            chunk = f.read(PIECE_LENGTH)
            if not chunk:
                break
            pieces.extend(hashlib.sha1(chunk).digest())
            
    # BEP-19 Standard Web-Seed Torrent Dictionary
    torrent_dict = {
        "announce": "udp://tracker.opentrackr.org:1337/announce",
        "announce-list": [
            [b"udp://tracker.opentrackr.org:1337/announce"],
            [b"udp://open.demonii.com:1337/announce"]
        ],
        "url-list": [f"{domain}/stream/{file_hash}".encode('utf-8')],
        "info": {
            "name": file_name.encode('utf-8'),
            "length": file_size,
            "piece length": PIECE_LENGTH,
            "pieces": bytes(pieces)
        }
    }
    
    torrent_file_path = f"./{file_name}.torrent"
    with open(torrent_file_path, "wb") as f:
        f.write(bencode.encode(torrent_dict))
        
    if os.path.exists(temp_path):
        os.remove(temp_path)
        
    return torrent_file_path
