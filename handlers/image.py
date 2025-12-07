# handlers/image.py

import asyncio

async def process_image(payload: dict):
    image_id = payload.get("image_id")
    if not image_id:
        raise ValueError("Missing required field 'image_id'")

    print(f"[handler:image] Processing image {image_id}...")

    # Simulate some I/O work
    await asyncio.sleep(0.5)

    print(f"[handler:image] Finished processing image {image_id}")
