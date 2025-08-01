#!/usr/bin/env python3
import requests
import json

BOT_TOKEN = "8335717977:AAHBAg8ovHrx9ctVfN8BckafZhmmFbRedJY"

print("Getting updates from your bot...")
response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates")
data = response.json()

if data["ok"] and data["result"]:
    for update in data["result"]:
        if "message" in update and "chat" in update["message"]:
            chat = update["message"]["chat"]
            print(f"\nFound chat:")
            print(f"  Type: {chat.get('type')}")
            print(f"  Title: {chat.get('title', 'N/A')}")
            print(f"  ID: {chat.get('id')}")
            print(f"  👆 This is your TELEGRAM_CHANNEL_ID: {chat.get('id')}")
else:
    print("No messages found. Please:")
    print("1. Make sure your bot is added to the group")
    print("2. Send a message in the group")
    print("3. Run this script again")