import asyncio

async def send_email(payload: dict):
    email = payload.get("email")
    if not email:
        raise ValueError("Missing required field 'email'")

    subject = payload.get("subject", "No subject")

    print(f"[handler:email] Sending email to {email!r} with subject {subject!r}")

    # Simulate sending work
    await asyncio.sleep(0.3)

    print(f"[handler:email] Email sent to {email!r}")