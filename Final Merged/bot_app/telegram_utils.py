import requests
from config.telegram_config import BOT_TOKEN, CHAT_ID

def send_telegram_alert(message: str, image_path: str | None = None):
    try:
        msg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r1 = requests.post(msg_url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print("TG message:", r1.status_code)

        if image_path:
            photo_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            with open(image_path, "rb") as photo:
                r2 = requests.post(
                    photo_url,
                    data={"chat_id": CHAT_ID},
                    files={"photo": photo},
                    timeout=25
                )
            print("TG photo:", r2.status_code)

    except Exception as e:
        print("[ERROR] Telegram failed:", e)
