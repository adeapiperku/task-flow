# handlers/image.py

import asyncio

async def process_image(payload: dict):
    image_id = payload.get("image_id")
    if not image_id:
        raise ValueError("Missing required field 'image_id'")

    sleep_s = int(payload.get("sleep_s", 0))
    if sleep_s:
        print(f"[handler:image] Sleeping {sleep_s}s to simulate long work...")
        await asyncio.sleep(sleep_s)

    print(f"[handler:image] Processing image {image_id}...")
    await asyncio.sleep(0.5)  # or whatever you already do
    print(f"[handler:image] Finished processing image {image_id}")
