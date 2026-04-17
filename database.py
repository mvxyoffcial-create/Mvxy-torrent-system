import os
from motor.motor_asyncio import AsyncIOMotorClient

# Load MongoDB URL from Environment Variables
MONGO_URL = os.environ.get("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client.torrent_bot

async def save_file_data(file_hash, message_id, file_name, file_size):
    await db.files.insert_one({
        "hash": file_hash,
        "message_id": message_id,
        "file_name": file_name,
        "size": file_size
    })

async def get_file_data(file_hash):
    return await db.files.find_one({"hash": file_hash})
