from .image import process_image
from .email import send_email

HANDLERS = {
    "process-image": process_image,
    "send-email": send_email,
}