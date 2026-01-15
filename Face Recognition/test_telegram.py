from telegram_config import BOT_TOKEN, CHAT_ID
import requests

print("TOKEN OK:", bool(BOT_TOKEN))
print("CHAT_ID:", CHAT_ID)

r = requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={"chat_id": CHAT_ID, "text": "✅ Telegram works from Thonny!"},
    timeout=10
)

print(r.status_code, r.text)
