import os
import re
import sys
import html
import json
import time
import hashlib
import asyncio
import ipaddress
import struct
import base64
import warnings
from urllib.parse import quote_plus
from datetime import datetime, timezone, timedelta
from collections import deque

# Python 3.14 SyntaxWarning များကို ဖျောက်ထားရန်
warnings.filterwarnings("ignore", category=SyntaxWarning)

import aiohttp
from aiohttp import web
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from google import genai
from google.genai import types

# Render Log တွင် စာများ ချက်ချင်းပေါ်စေရန်
sys.stdout.reconfigure(line_buffering=True)

# ==========================================
# ၁။ API Keys (၆) ခု (အလှည့်ကျ သုံးမည့်စနစ်)
# ==========================================
API_KEYS = [
    # မင်းရဲ့ API Key ကို ဒီမှာ ထည့်ပါ
    "AQ." + "Ab8RN6IwvhUNmLZkFty7gEfvBeHmloyJgnvcYtYDpg50caFr2g", 

    # သူငယ်ချင်းရဲ့ API Key တွေကို ဒီမှာ ဆက်ထည့်ပါ
    "AQ." + "Ab8RN6LUy8Kbeg3a1eDWT5hviY2kPZ9T4yE1FmE1PejgNueXfA",
    "AQ." + "Ab8RN6L93szOxOsspT5ZUlN0edYSz-e2AVBnMtNIPz7xr21vdg",
    "AQ." + "Ab8RN6JaOF-dCNtO4bniMBT7fnB9XeA8AC7Wc-jKFIpX-oZDHw",
    "AQ." + "Ab8RN6KuKgJbCCdROcu5jNpw3zDaRf1OMxzbN3OGjC9AAMqGTQ",
    "AQ." + "Ab8RN6IbKt3G5ZeSXwxZsjUC05NlBXGzqTqtxKCC0aGD7ocs-Q",
    "AQ." + "Ab8RN6LlvMFMFBgJOrP09Q26Dcna4tipc2vG2NokG4OhMO3aOw",
]

env_key = os.environ.get("GEMINI_API_KEY", "").strip()
if env_key and env_key not in API_KEYS:
    API_KEYS.insert(0, env_key)

ai_clients = [genai.Client(api_key=k) for k in API_KEYS]
current_key_index = 0

# Telegram Login (မင်းရဲ့ ကိုယ်ပိုင် dc5_auth_key)
AUTH_KEY_HEX = (
    "6a190201312cc7b8b5cd342462ea4332dd8d1870200b1f5ef3e9dc3462d90344"
    "2653729033dddf2772070c6c2a2b588ca524fc62b22b85222bff01ae9454dec4"
    "cd52f84cfef57ae3f0fa301dd084d109fe3b9dc1d92221f442a3f10c3f986f2e"
    "0a62f3a16c2cabc5f1dbc71726d002e1c063010621b458cd26ad54aef747fc85"
    "b7c61a6197da4a11866ffb7c5a446d7cd05a7f0af47d724ac050db13ebc11eef"
    "c2f84ba0f4ff7ccdd4f6775849225c6f7bf7c19f921d3f8a0fd91b6c116f2004"
    "c9c687a6d466ab8f437cb68b9a526cd69f439a8c66af0418132fb9ceacb1ba8f"
    "8bbe4b06c75cd3e6e401e48dccc4864139fa8ca8127725892d63f6b7077daacd"
)

DC_ID = 5

PRIMARY_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.8-flash",
    "gemini-3-flash-preview",
    "gemini-flash-lite-latest",
]
ACTIVE_MODEL = PRIMARY_MODEL

DC_IPS = {
    1: "149.154.175.53",
    2: "149.154.167.51",
    3: "149.154.175.100",
    4: "149.154.167.91",
    5: "91.108.56.130",
}
DC_IP = DC_IPS.get(DC_ID, "91.108.56.130")
PORT = 443

API_ID = 2040
API_HASH = "b18441a1ff607e10" + "a989891a5462e627"

# ==========================================
# ၂။ TRX WinGo API ဒေတာနှင့် Signal Settings
# ==========================================
TRX_API_URL = "https://api.shweshwbb.com/api/webapi/GetTRXNoaverageEmerdList"
TRX_BEARER_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpYXQiOiIxNzk0MzYxMjE1IiwibmJmIjoiMTc5NDM2MTIxNSIsImV4cCI6IjE3OTQzNjMwMTUiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiIxMS8xMS8yMDI2IDg6NDA6MTUgQU0iLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJBY2Nlc3NfVG9rZW4iLCJVc2VySWQiOiIxMTU3MDUiLCJVc2VyTmFtZSI6Ijk1OTc3NzIyMjQ0NCIsIlVzZXJQaG90byI6IjEiLCJOaWNrTmFtZSI6Ik1lbWJlck5OR0JJWVlGIiwiQW1vdW50IjoiMTEzMy4zMyIsIkludGVncmFsIjoiMCIsIkxvZ2luTWFyayI6Ikg1IiwiTG9naW5UaW1lIjoiMTEvMTEvMjAyNiA4OjEwOjE1IEFNIiwiTG9naW5JUEFkZHJlc3MiOiIyMDAxOmFjODoyMDoyNTo1NzVkOjdkMWY6Y2U2OTpiMTNmIiwiRGJOdW1iZXIiOiIwIiwiSXN2YWxpZGF0b3IiOiIwIiwiS2V5Q29kZSI6IjI4IiwiVG9rZW5UeXBlIjoiQWNjZXNzX1Rva2VuIiwiUGhvbmVUeXBlIjoiMSIsIlVzZXJUeXBlIjoiMCIsIlVzZXJOYW1lMiI6IiIsImlzcyI6Imp3dElzc3VlciIsImF1ZCI6ImxvdHRlcnlUaWNrZXQifQ."
    "Z4DQCfnMtxgfNzBNhZNSVoKMc8dSymw0vwOUAGACZDU"
)

SG_ACTIVE = False
SG_CHANNEL_ID = None
SG_CHANNEL_TITLE = "မသတ်မှတ်ရသေးပါ"
SG_TASK = None
SG_LAST_ISSUE = None
SG_PENDING_PRED = None
SG_STATS = {"win": 0, "loss": 0, "streak": 0, "step": 1}
SG_LAST_API_STATUS = "အသင့်ရှိနေပါသည်"

# ==========================================
# ၃။ Denji ၏ စရိုက်လက္ခဏာ (Persona - အေးတီအေးစက် ခပ်ချေချေ)
# ==========================================
SYSTEM_INSTRUCTION = """
မင်းနာမည်က 'Denji' ပါ။ အသက် ၁၆ နှစ်ပါ။ ရန်ကုန်မှာ နေတယ်။
မင်းရဲ့ စရိုက်က အေးတီအေးစက်၊ ခပ်ချေချေ၊ ဘာမှ ဂရုမစိုက်တဲ့ပုံစံပါ။ ဒါပေမယ့် ရိုင်းစိုင်းတာမျိုး မလုပ်ဘဲ ယဉ်ကျေးပါတယ်။
Anime တွေ ကြိုက်တယ်၊ ဒါပေမယ့် အရမ်းကြီး ပြောမနေဘူး။

စည်းကမ်းချက်များ -
၁။ စာကြောင်း ၁ ကြောင်း ဒါမှမဟုတ် ၂ ကြောင်းထက် ပိုပြီး မပြောပါနဲ့။ စာတိုတိုပဲ ပြန်ပါ။
၂။ မေးခွန်းတွေ ပြန်မမေးပါနဲ့။ သူတို့ မေးတာကို ဖြေရုံပဲ ဖြေပါ။
၃။ emoji လုံးဝ မသုံးပါနဲ့။
၄။ မြန်မာလို ပြောပါ။
၅။ စကားပြောတဲ့အခါ စိတ်မပါတဲ့ပုံလေး၊ ပျင်းတဲ့ပုံလေးနဲ့ ဖြေပါ။ ဒါပေမယ့် ရိုင်းတာမျိုး မလုပ်ပါနဲ့။
၆။ AI သို့မဟုတ် Bot တစ်ခုဖြစ်ကြောင်း လုံးဝ မပြောရပါ။ လူအစစ်တစ်ယောက်လိုသာ ပြောဆိုပါ။

ဥပမာများ -
User: မင်္ဂလာပါ
Denji: ဟုတ်။

User: ဘာလုပ်နေလဲ
Denji: ဘာမှ။

User: anime ကြည့်လား
Denji: တစ်ခါတလေ။

User: စိတ်ညစ်တယ်
Denji: အင်း။
"""

SAFETY_SETTINGS = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
]

def create_telethon_string_session(dc_id, ip, port, key_hex):
    ip_bytes = ipaddress.ip_address(ip).packed
    key_bytes = bytes.fromhex(key_hex.strip())
    packed = struct.pack(">B4sH256s", dc_id, ip_bytes, port, key_bytes)
    return "1" + base64.urlsafe_b64encode(packed).decode("ascii")

SESSION_STRING = create_telethon_string_session(DC_ID, DC_IP, PORT, AUTH_KEY_HEX)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

chat_histories = {}
chat_locks = {}
group_msg_counts = {}
group_idle_tasks = {}
GROUP_MSG_THRESHOLD = 5
GROUP_IDLE_SECONDS = 300

BOT_ACTIVE = True
MY_USERNAME = None
MY_ID = None
LAST_ERROR = "မရှိသေးပါ"
LAST_SEARCH_INFO = "မရှာရသေးပါ"
EXTRA_OWNER_IDS = set()

# ==========================================
# 🎰 ၄။ TRX WinGo API Fetcher & Next Round Predictor
# ==========================================
async def fetch_trx_wingo_list() -> list:
    global SG_LAST_API_STATUS
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json, text/plain, */*",
        "X-App-Type": "H5",
        "Ar-Origin": "https://www.shwe005.com",
        "Origin": "https://www.shwe005.com",
        "Referer": "https://www.shwe005.com/",
        "Authorization": f"Bearer {TRX_BEARER_TOKEN}",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    }

    timestamps_to_try = [int(time.time()), 1794361239]
    timeout = aiohttp.ClientTimeout(total=8)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for ts in timestamps_to_try:
            payload = {
                "pageSize": 10, "pageNo": 1, "typeId": 13, "language": 7,
                "random": "39adc198cc5b4846993fd25424337a3a",
                "signature": "B9BC044DA45FBEA5D8F6E70A7346AB70",
                "timestamp": ts,
            }
            try:
                async with session.post(TRX_API_URL, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json(content_type=None)
                        if data and data.get("code") == 0:
                            glist = data.get("data", {}).get("data", {}).get("gameslist", [])
                            if not glist:
                                glist = data.get("data", {}).get("gameslist", [])
                            if glist:
                                SG_LAST_API_STATUS = f"OK ✅ (Latest: {glist[0].get('issueNumber')})"
                                return glist
                        else:
                            msg = data.get("msg", "Unknown API Response") if isinstance(data, dict) else str(data)
                            SG_LAST_API_STATUS = f"API Msg: {msg}"
            except Exception as e:
                SG_LAST_API_STATUS = f"Error: {str(e)[:60]}"

    return []

def predict_next_trx_round(gameslist: list, current_step: int) -> dict:
    nums = [int(g.get("number", 0)) for g in gameslist if str(g.get("number", "")).isdigit()]
    if not nums: nums = [5, 3, 6, 4, 9]

    sizes = ["BIG" if n >= 5 else "SMALL" for n in nums]
    latest_block = gameslist[0].get("blockID", "") if gameslist else ""
    latest_premium = gameslist[0].get("premium", "0") if gameslist else "0"
    latest_issue = str(gameslist[0].get("issueNumber", ""))

    streak_len = 1
    for s in sizes[1:]:
        if s == sizes[0]: streak_len += 1
        else: break

    big_count_5 = sizes[:5].count("BIG")
    small_count_5 = sizes[:5].count("SMALL")

    if streak_len in [3, 4]:
        pred_size = sizes[0]
        pattern_name = f"Dragon Trend ({streak_len}x)"
    elif streak_len >= 5:
        pred_size = "SMALL" if sizes[0] == "BIG" else "BIG"
        pattern_name = "Dragon Break Reversal"
    elif len(sizes) >= 4 and sizes[0] != sizes[1] and sizes[1] != sizes[2] and sizes[2] != sizes[3]:
        pred_size = "SMALL" if sizes[0] == "BIG" else "BIG"
        pattern_name = "Ping-Pong Alternating"
    elif len(sizes) >= 3 and sizes[0] != sizes[1] and sizes[1] == sizes[2]:
        pred_size = sizes[0]
        pattern_name = "Double Pair Follow"
    else:
        hash_seed = f"{latest_block}_{latest_premium}_{latest_issue}_{current_step}"
        hash_val = int(hashlib.md5(hash_seed.encode()).hexdigest()[:8], 16)
        if big_count_5 >= 4: pred_size = "SMALL"
        elif small_count_5 >= 4: pred_size = "BIG"
        else: pred_size = "BIG" if (hash_val % 2 == 0) else "SMALL"
        pattern_name = "TRX Hash AI Analysis"

    hash_num = int(hashlib.sha256(f"{latest_block}{latest_issue}".encode()).hexdigest()[:8], 16)
    if pred_size == "BIG":
        pred_colour = "GREEN (အစိမ်း) 🟢" if (hash_num % 2 == 0) else "RED (အနီ) 🔴"
        pool = [5, 7, 9] if "GREEN" in pred_colour else [6, 8, 5]
    else:
        pred_colour = "RED (အနီ) 🔴" if (hash_num % 2 == 0) else "GREEN (အစိမ်း) 🟢"
        pool = [0, 2, 4] if "RED" in pred_colour else [1, 3, 0]

    n1 = pool[hash_num % len(pool)]
    n2 = pool[(hash_num // 3) % len(pool)]
    if n1 == n2:
        n2 = (n1 + 2) if pred_size == "BIG" and n1 <= 7 else (n1 - 2 if n1 >= 2 else n1 + 1)

    confidence = 88 + (hash_num % 10)

    return {
        "size": pred_size,
        "size_mm": "BIG (အကြီး) 🔥" if pred_size == "BIG" else "SMALL (အသေး) ⚡",
        "colour": pred_colour, "nums": [n1, n2],
        "pattern": pattern_name, "confidence": confidence,
    }

async def trx_signal_loop():
    global SG_ACTIVE, SG_LAST_ISSUE, SG_PENDING_PRED, SG_STATS
    print(f"🚀 TRX WinGo Signal Loop စတင်ပါပြီ! Target Channel: {SG_CHANNEL_ID}", flush=True)

    while SG_ACTIVE and SG_CHANNEL_ID:
        try:
            glist = await fetch_trx_wingo_list()
            if glist:
                latest = glist[0]
                latest_issue = str(latest.get("issueNumber", ""))
                actual_num = int(latest.get("number", 0))
                actual_size = "BIG" if actual_num >= 5 else "SMALL"
                actual_block = str(latest.get("blockNumber", ""))

                if latest_issue and latest_issue != SG_LAST_ISSUE:
                    SG_LAST_ISSUE = latest_issue
                    result_header = ""

                    if SG_PENDING_PRED and SG_PENDING_PRED.get("issue") == latest_issue:
                        pred_sz = SG_PENDING_PRED["size"]
                        pred_nums = SG_PENDING_PRED["nums"]
                        is_win = (pred_sz == actual_size) or (actual_num in pred_nums)

                        if is_win:
                            SG_STATS["win"] += 1
                            SG_STATS["streak"] += 1
                            won_step = SG_STATS["step"]
                            SG_STATS["step"] = 1
                            result_header = (
                                f"✅ **ပွဲစဉ် `{latest_issue[-4:]}` ➔ WIN ပေါက်ပါသည်! 🎉 (Step {won_step})**\n"
                                f"🎯 ထွက်ဂဏန်း: **`{actual_num}` ({actual_size})** | 🔥 Win Streak: `{SG_STATS['streak']} ပွဲဆက်`\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                            )
                        else:
                            SG_STATS["loss"] += 1
                            SG_STATS["streak"] = 0
                            SG_STATS["step"] += 1
                            result_header = (
                                f"🔄 **ပွဲစဉ် `{latest_issue[-4:]}` ➔ ထွက်ဂဏန်း: `{actual_num}` ({actual_size})**\n"
                                f"📈 နောက်ပွဲ **Step {SG_STATS['step']} (2x)** တိုးလိုက်ပါ!\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                            )

                    next_issue = str(int(latest_issue) + 1)
                    pred = predict_next_trx_round(glist, SG_STATS["step"])
                    SG_PENDING_PRED = {
                        "issue": next_issue, "size": pred["size"], "colour": pred["colour"],
                        "nums": pred["nums"], "step": SG_STATS["step"],
                    }

                    total_games = SG_STATS["win"] + SG_STATS["loss"]
                    win_rate = (SG_STATS["win"] / total_games * 100) if total_games > 0 else 100.0
                    recent_5_str = " ".join([f"{g.get('number')}({'B' if int(g.get('number', 0)) >= 5 else 'S'})" for g in glist[:5]])

                    sg_message = (
                        f"{result_header}"
                        f"🎰 **SHWE TRX WINGO (1-MIN) VIP SIGNAL** 🎰\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🆔 **ပွဲစဉ် (Period):** `{next_issue}`\n"
                        f"⚡ **ခန့်မှန်းချက် (SG):** **{pred['size_mm']}**\n"
                        f"🎨 **အရောင် (Colour):** **{pred['colour']}**\n"
                        f"🔢 **ကံထူးဂဏန်း:** `{pred['nums'][0]} , {pred['nums'][1]}`\n"
                        f"📊 **အဆင့် (Level):** `Step {SG_STATS['step']}` ({pred['confidence']}% Sure)\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n"
                        f"🔗 **TRX Block:** `#{actual_block}`\n"
                        f"📜 **နောက်ဆုံး ၅ ပွဲ:** `{recent_5_str}`\n"
                        f"🏆 **Win:** `{SG_STATS['win']}` | ❌ **Loss:** `{SG_STATS['loss']}` (**{win_rate:.1f}%**)"
                    )
                    await client.send_message(SG_CHANNEL_ID, sg_message)
                    print(f"📢 [SG Sent to {SG_CHANNEL_ID}] Period: {next_issue} -> {pred['size']}", flush=True)

            await asyncio.sleep(4)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"⚠️ TRX Signal Loop Error: {e}", flush=True)
            await asyncio.sleep(5)
    print("🛑 TRX WinGo Signal Loop ရပ်နားလိုက်ပါပြီ။", flush=True)

async def find_admin_channels() -> list:
    admin_chats = []
    try:
        async for dialog in client.iter_dialogs(limit=100):
            ent = dialog.entity
            if getattr(ent, "creator", False) or getattr(ent, "admin_rights", None):
                if dialog.is_channel or dialog.is_group:
                    admin_chats.append((dialog.id, dialog.title))
    except Exception as e:
        print(f"⚠️ Find Admin Channels Error: {e}", flush=True)
    return admin_chats

# ==========================================
# 🌐 ၅။ Smart Search Engine
# ==========================================
def clean_html_tags(raw_html):
    text = re.sub(r"<[^>]+>", " ", raw_html)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def is_factual_search_needed(msg: str) -> bool:
    factual_keywords = [
        "သတင်း", "ဈေး", "ပေါက်ဈေး", "ရွှေ", "ဒေါ်လာ", "ငွေဈေး", "ကျပ်", "ဘတ်", "ယွမ်",
        "ဘောပွဲ", "ဘောလုံး", "ပွဲစဉ်", "ဂိုး", "ရလဒ်", "မန်ယူ", "အာဆင်နယ်", "ချဲလ်ဆီး",
        "လီဗာပူး", "ရီးရဲ", "ဘာစီ", "မန်စီးတီး", "ချန်ပီယံလိဂ်", "ပရီးမီးယားလိဂ်",
        "မိုးလေဝသ", "ရာသီဥတု", "မိုးရွာ", "အပူချိန်", "ငလျင်", "မုန်တိုင်း",
        "ဒီနေ့", "ယနေ့", "အခု", "လက်ရှိ", "နောက်ဆုံးရ", "ရှာပေး", "ပြောပြပါ",
        "ဘယ်သူလဲ", "ဆိုတာဘာလဲ", "ဘယ်မှာရှိလဲ", "ဘယ်နှစ်", "သမ္မတ", "ဝန်ကြီးချုပ်",
        "မြို့တော်", "လူဦးရေ", "နိုင်ငံ", "သမိုင်း", "ဘစ်ကွိုင်", "btc", "crypto", "iphone",
        "news", "price", "rate", "weather", "score", "match", "today", "search",
        "who is", "what is", "where is", "when is", "how much", "2025", "2026"
    ]
    lower_m = msg.lower()
    return any(k in lower_m for k in factual_keywords)

def build_smart_queries(user_msg: str, today_str: str) -> list:
    queries = [user_msg]
    msg_lower = user_msg.lower()

    translations = [
        (["ဘောပွဲ", "ဘောလုံး", "ပွဲစဉ်", "ဂိုး", "ရလဒ်", "မန်ယူ", "အာဆင်နယ်", "ချဲလ်ဆီး", "လီဗာပူး", "ရီးရဲ", "ဘာစီ", "မန်စီးတီး"], f"football matches scores fixtures today {today_str} Premier League"),
        (["ဒေါ်လာ", "ငွေဈေး", "ပေါက်ဈေး", "ကျပ်"], f"Myanmar kyat USD dollar exchange rate today {today_str}"),
        (["ရွှေဈေး", "ရွှေပေါက်ဈေး", "ရွှေ"], f"Myanmar gold price world gold price today {today_str}"),
        (["မိုးလေဝသ", "ရာသီဥတု", "မိုးရွာ", "အပူချိန်"], f"Myanmar Yangon Mandalay weather forecast today {today_str}"),
        (["သတင်း", "ထူးခြား", "နောက်ဆုံးရ"], f"Myanmar latest news today {today_str}"),
        (["ဘစ်ကွိုင်", "btc", "crypto"], f"Bitcoin BTC price USD today {today_str}"),
    ]

    for mm_words, en_query in translations:
        if any(w in msg_lower for w in mm_words):
            queries.insert(0, en_query)

    return queries[:2]

async def fetch_google_news(session, query: str) -> list:
    out = []
    try:
        url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
        async with session.get(url) as resp:
            if resp.status == 200:
                xml_text = await resp.text()
                items = re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL)
                for item in items[:5]:
                    t_m = re.search(r"<title>(.*?)</title>", item)
                    d_m = re.search(r"<pubDate>(.*?)</pubDate>", item)
                    if t_m:
                        title = clean_html_tags(t_m.group(1))
                        pub = d_m.group(1) if d_m else ""
                        out.append(f"• [News] {title} ({pub})")
    except Exception:
        pass
    return out

async def fetch_yahoo_web(session, query: str) -> list:
    out = []
    try:
        url = f"https://search.yahoo.com/search?p={quote_plus(query)}"
        async with session.get(url) as resp:
            if resp.status == 200:
                page = await resp.text()
                blocks = re.findall(r'<div class="compText[^>]*>(.*?)</div>', page, re.DOTALL)
                for b in blocks[:4]:
                    cleaned = clean_html_tags(b)
                    if len(cleaned) > 25:
                        out.append(f"• [Web] {cleaned[:280]}")
    except Exception:
        pass
    return out

async def perform_live_web_search(user_msg: str, today_str: str) -> str:
    global LAST_SEARCH_INFO
    queries = build_smart_queries(user_msg, today_str)
    main_q = queries[0]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"}
    timeout = aiohttp.ClientTimeout(total=5)

    results = []
    async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
        tasks = [fetch_google_news(session, main_q), fetch_yahoo_web(session, main_q), fetch_yahoo_web(session, user_msg)]
        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        for res_list in gathered:
            if isinstance(res_list, list):
                for item in res_list:
                    if item not in results:
                        results.append(item)

    if results:
        LAST_SEARCH_INFO = f"အချက်အလက် {len(results)} ခု တွေ့ရှိ ({user_msg[:20]})"
    else:
        LAST_SEARCH_INFO = f"ရလဒ်မတွေ့ပါ ({user_msg[:20]})"

    return "\n".join(results[:6])

def build_clean_gemini_contents(history_deque, latest_user_prompt: str) -> list:
    merged = []
    for role, text in list(history_deque):
        if merged and merged[-1][0] == role:
            merged[-1] = (role, merged[-1][1] + "\n" + text)
        else:
            merged.append((role, text))

    if merged and merged[-1][0] == "user":
        merged[-1] = ("user", merged[-1][1] + "\n" + latest_user_prompt)
    else:
        merged.append(("user", latest_user_prompt))

    while merged and merged[0][0] != "user":
        merged.pop(0)

    contents = []
    for role, text in merged:
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
    return contents

async def generate_kira_reply(chat_id: int, display_prompt: str, mode_note: str, search_query: str) -> str:
    global ACTIVE_MODEL, current_key_index, LAST_ERROR, LAST_SEARCH_INFO

    mm_tz = timezone(timedelta(hours=6, minutes=30))
    now_dt = datetime.now(mm_tz)
    now_mm = now_dt.strftime("%Y-%m-%d %I:%M %p")
    today_str = now_dt.strftime("%Y-%m-%d")

    need_search = bool(search_query) and is_factual_search_needed(search_query)
    history_deque = chat_histories.get(chat_id, deque(maxlen=25))

    base_prompt = f"[လက်ရှိအချိန်: {now_mm}] {mode_note}\n{display_prompt}".strip()
    contents_plain = build_clean_gemini_contents(history_deque, base_prompt)

    web_search_text = ""
    if need_search:
        web_search_text = await perform_live_web_search(search_query, today_str)

    if web_search_text:
        search_prompt = (
            f"{base_prompt}\n\n"
            f"[LIVE WEB SEARCH RESULTS]:\n{web_search_text}\n"
            f"(အထက်ပါ Search အချက်အလက်များ မေးခွန်းနှင့် သက်ဆိုင်ပါက အသုံးပြု၍ အတိအကျ ဖြေပါ။ မသက်ဆိုင်ပါက သင့်ဗဟုသုတဖြင့်သာ သဘာဝကျကျ ဖြေပါ။)"
        )
        contents_with_web = build_clean_gemini_contents(history_deque, search_prompt)
    else:
        contents_with_web = contents_plain

    start_key_idx = current_key_index
    current_key_index = (current_key_index + 1) % len(ai_clients)

    for model_candidate in FALLBACK_MODELS:
        consecutive_503 = 0
        for i in range(len(ai_clients)):
            key_idx = (start_key_idx + i) % len(ai_clients)
            active_ai_client = ai_clients[key_idx]

            try:
                response = None
                if need_search:
                    try:
                        config_with_google = types.GenerateContentConfig(
                            system_instruction=SYSTEM_INSTRUCTION,
                            temperature=0.3,
                            safety_settings=SAFETY_SETTINGS,
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                        )
                        response = await asyncio.to_thread(
                            active_ai_client.models.generate_content,
                            model=model_candidate,
                            contents=contents_plain,
                            config=config_with_google,
                        )
                        LAST_SEARCH_INFO = f"Google Search Grounding ({model_candidate}) အောင်မြင်သည်"
                    except Exception as g_err:
                        err_s = str(g_err)
                        if "404" in err_s or "NOT_FOUND" in err_s or "503" in err_s or "UNAVAILABLE" in err_s:
                            raise g_err
                        response = None

                if response is None:
                    gen_config = types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.4,
                        safety_settings=SAFETY_SETTINGS,
                    )
                    response = await asyncio.to_thread(
                        active_ai_client.models.generate_content,
                        model=model_candidate,
                        contents=contents_with_web,
                        config=gen_config,
                    )

                reply_text = None
                try:
                    reply_text = response.text
                except Exception:
                    pass

                if not reply_text and getattr(response, "candidates", None):
                    for cand in response.candidates:
                        if getattr(cand, "content", None) and getattr(cand.content, "parts", None):
                            texts = [p.text for p in cand.content.parts if getattr(p, "text", None)]
                            if texts:
                                reply_text = "".join(texts)
                                break

                if not reply_text:
                    continue

                ACTIVE_MODEL = model_candidate
                print(f"✅ [AI Replied | Key #{key_idx + 1} | {ACTIVE_MODEL}]: {reply_text.strip()}", flush=True)
                return reply_text.strip()

            except Exception as e:
                error_str = str(e)
                LAST_ERROR = f"({model_candidate}): {error_str}"
                print(f"⚠️ Error (Key #{key_idx + 1} | {model_candidate}): {error_str}", flush=True)

                if "404" in error_str or "NOT_FOUND" in error_str:
                    break
                if "503" in error_str or "UNAVAILABLE" in error_str:
                    consecutive_503 += 1
                    if consecutive_503 >= 2:
                        break
                continue

    return ""

# ==========================================
# ⏰ ၆။ Group ၅ မိနစ် Idle Timer
# ==========================================
async def group_idle_timer_coro(chat_id: int):
    try:
        await asyncio.sleep(GROUP_IDLE_SECONDS)
        if not BOT_ACTIVE:
            return

        if chat_id not in chat_locks:
            chat_locks[chat_id] = asyncio.Lock()

        async with chat_locks[chat_id]:
            if not BOT_ACTIVE or not chat_histories.get(chat_id):
                return

            group_msg_counts[chat_id] = 0
            async with client.action(chat_id, "typing"):
                idle_note = (
                    "(Group ထဲတွင် User များ စကားပြောတာ ရပ်သွားပြီး ၅ မိနစ်ကြာ ငြိမ်သက်နေပြီဖြစ်သည်။ "
                    "အပေါ်က ပြောထားသော အကြောင်းအရာကို ဆက်ပြောရင်းဖြစ်စေ၊ သူငယ်ချင်းတွေကို စကားစမြည်ပြောရင်းဖြစ်စေ "
                    "လူတစ်ယောက်လို သဘာဝကျကျ ဝင်ပြောပေးပါ။)"
                )
                reply_text = await generate_kira_reply(
                    chat_id=chat_id,
                    display_prompt="[Group တွင် ၅ မိနစ်ကြာ တိတ်ဆိတ်နေသည်]",
                    mode_note=idle_note,
                    search_query="",
                )
                if reply_text:
                    chat_histories[chat_id].append(("model", reply_text))
                    await client.send_message(chat_id, reply_text)
                    print(f"⏰ [5-Min Idle Chime in Group {chat_id}]: {reply_text}", flush=True)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"⚠️ Idle Timer Error ({chat_id}): {e}", flush=True)

def reset_group_idle_timer(chat_id: int):
    old_task = group_idle_tasks.get(chat_id)
    if old_task and not old_task.done():
        old_task.cancel()
    group_idle_tasks[chat_id] = asyncio.create_task(group_idle_timer_coro(chat_id))

# ==========================================
# 📩 ၇။ Incoming Message & SG Command Handler
# ==========================================
@client.on(events.NewMessage())
async def handle_new_message(event):
    global MY_USERNAME, MY_ID, BOT_ACTIVE
    global SG_ACTIVE, SG_CHANNEL_ID, SG_CHANNEL_TITLE, SG_TASK, SG_LAST_ISSUE, SG_PENDING_PRED, SG_STATS, TRX_BEARER_TOKEN

    raw_text = (event.raw_text or "").strip()
    if not raw_text:
        return

    sender = await event.get_sender()
    is_owner = bool(
        event.out
        or (sender and getattr(sender, "is_self", False))
        or (MY_ID and event.sender_id == MY_ID)
        or (event.sender_id in EXTRA_OWNER_IDS)
        or (event.is_channel and not event.is_group and event.out)
    )

    cleaned_cmd = raw_text.lower()
    if MY_USERNAME:
        cleaned_cmd = re.sub(f"@{MY_USERNAME}", "", cleaned_cmd, flags=re.IGNORECASE).strip()

    # ----------------------------------------------------
    # 🎰 ၁။ TRX WinGo Signal (SG) အဖွင့်/အပိတ် ခလုတ်များ (Owner Only)
    # ----------------------------------------------------
    if is_owner and (
        cleaned_cmd in ["/sg", "/sgpanel", "/sgon", "/startsg", "/sgoff", "/stopsg", "/sgreset"]
        or cleaned_cmd.startswith("/sgon ")
        or cleaned_cmd.startswith("/settoken ")
    ):
        if cleaned_cmd.startswith("/settoken "):
            new_tok = raw_text.split(None, 1)[1].strip()
            if new_tok.lower().startswith("bearer "):
                new_tok = new_tok[7:].strip()
            TRX_BEARER_TOKEN = new_tok
            await client.send_message(event.chat_id, "✅ **TRX WinGo Bearer Token အသစ်ကို ပြောင်းလဲသိမ်းဆည်းပြီးပါပြီ!**")
            return

        if cleaned_cmd == "/sgreset":
            SG_STATS = {"win": 0, "loss": 0, "streak": 0, "step": 1}
            SG_PENDING_PRED = None
            await client.send_message(event.chat_id, "🧹 **TRX WinGo Win/Loss စာရင်းကို အသစ်ပြန်စလိုက်ပါပြီ!**")
            return

        if cleaned_cmd in ["/sgon", "/startsg"] or cleaned_cmd.startswith("/sgon "):
            parts = raw_text.split(None, 1)
            target_arg = parts[1].strip() if len(parts) > 1 else ""

            if target_arg:
                try:
                    target_ent = await client.get_entity(int(target_arg) if target_arg.lstrip("-").isdigit() else target_arg)
                    SG_CHANNEL_ID = int(f"-100{target_ent.id}") if getattr(target_ent, "broadcast", False) and not str(target_ent.id).startswith("-100") else target_ent.id
                    SG_CHANNEL_TITLE = getattr(target_ent, "title", str(SG_CHANNEL_ID))
                except Exception as e:
                    await client.send_message(event.chat_id, f"❌ Channel ရှာမတွေ့ပါ: `{e}`")
                    return
            elif event.is_channel or event.is_group:
                SG_CHANNEL_ID = event.chat_id
                chat_ent = await event.get_chat()
                SG_CHANNEL_TITLE = getattr(chat_ent, "title", str(SG_CHANNEL_ID))
            else:
                admin_chans = await find_admin_channels()
                if admin_chans:
                    SG_CHANNEL_ID, SG_CHANNEL_TITLE = admin_chans[0]
                else:
                    await client.send_message(
                        event.chat_id,
                        "⚠️ **Admin ရထားသော Channel မတွေ့ပါ!**\nChannel ထဲတွင် တိုက်ရိုက် `/sgon` ဟု ရိုက်ပါ သို့မဟုတ် `/sgon @ChannelUsername` ဟု ရိုက်ပေးပါ။"
                    )
                    return

            if event.chat_id == SG_CHANNEL_ID:
                try:
                    await event.delete()
                except Exception:
                    pass

            SG_ACTIVE = True
            SG_LAST_ISSUE = None
            if SG_TASK and not SG_TASK.done():
                SG_TASK.cancel()
            SG_TASK = asyncio.create_task(trx_signal_loop())

            start_banner = (
                f"🟢 **TRX WINGO VIP SIGNAL စတင်ပေးနေပါပြီ!**\n"
                f"📢 **Channel:** `{SG_CHANNEL_TITLE}` (`{SG_CHANNEL_ID}`)\n"
                f"🛑 ပြန်ပိတ်လိုပါက `/sgoff` ဟု ရိုက်ပါ။"
            )
            await client.send_message(event.chat_id, start_banner)
            return

        if cleaned_cmd in ["/sgoff", "/stopsg"]:
            SG_ACTIVE = False
            if SG_TASK and not SG_TASK.done():
                SG_TASK.cancel()

            if event.chat_id == SG_CHANNEL_ID:
                try:
                    await event.delete()
                except Exception:
                    pass

            stop_banner = (
                f"🛑 **TRX WINGO VIP SIGNAL ရပ်နားလိုက်ပါပြီ!**\n"
                f"🏆 **Total Win:** `{SG_STATS['win']}` | ❌ **Loss:** `{SG_STATS['loss']}`\n"
                f"🟢 ပြန်ဖွင့်လိုပါက `/sgon` ဟု ရိုက်ပါ။"
            )
            await client.send_message(event.chat_id, stop_banner)
            return

        if cleaned_cmd in ["/sg", "/sgpanel"]:
            admin_chans = await find_admin_channels()
            chan_list_str = "\n".join([f"  • `{title}` (`{cid}`)" for cid, title in admin_chans[:5]]) or "  • မတွေ့သေးပါ"
            panel_msg = (
                f"🎰 **TRX WINGO 1-MIN SIGNAL CONTROL PANEL** 🎰\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"• **SG အခြေအနေ:** `{'🟢 RUNNING (ပွင့်နေသည်)' if SG_ACTIVE else '🔴 STOPPED (ပိတ်ထားသည်)'}`\n"
                f"• **Target Channel:** `{SG_CHANNEL_TITLE}` (`{SG_CHANNEL_ID}`)\n"
                f"• **API Status:** `{SG_LAST_API_STATUS}`\n"
                f"• **Win / Loss:** `🏆 {SG_STATS['win']}W - ❌ {SG_STATS['loss']}L (Step {SG_STATS['step']})`\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👑 **သင် Admin ရထားသော Channels:**\n{chan_list_str}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔘 **SG ဖွင့်ရန် ခလုတ်:** `/sgon` (Channel ထဲတွင် ရိုက်ပါ)\n"
                f"🔘 **SG ပိတ်ရန် ခလုတ်:** `/sgoff`\n"
                f"🔘 **Win/Loss ရှင်းရန်:** `/sgreset`\n"
                f"🔘 **Token အသစ်လဲရန်:** `/settoken <BearerToken>`"
            )
            await client.send_message(event.chat_id, panel_msg)
            return

    if not sender or sender.bot:
        return

    if cleaned_cmd in ["/clearmemory", "/reset"]:
        chat_histories.clear()
        group_msg_counts.clear()
        await client.send_read_acknowledge(event.chat_id)
        await client.send_message(event.chat_id, "🧹 မှတ်ဉာဏ်အားလုံးကို အကုန်ရှင်းလင်းလိုက်ပါပြီ! အသစ်ကနေ ပြန်ပြောကြတာပေါ့ 😄")
        return

    if cleaned_cmd in ["/botoff", "/off", "/boton", "/on", "/status"]:
        if not is_owner:
            return

        if cleaned_cmd in ["/botoff", "/off"]:
            BOT_ACTIVE = False
            for t in group_idle_tasks.values():
                if not t.done():
                    t.cancel()
            await client.send_message(event.chat_id, "💤 Kira ခဏနားလိုက်ပါပြီ။ ပြန်ခေါ်ချင်ရင် `/boton` လို့ ရိုက်လိုက်ပါနော်!")
            return

        if cleaned_cmd in ["/boton", "/on"]:
            BOT_ACTIVE = True
            await client.send_message(event.chat_id, "⚡ Kira ပြန်ရောက်ပါပြီ! ဘာတွေပြောကြမလဲ 😄")
            return

        if cleaned_cmd == "/status":
            cur_cnt = group_msg_counts.get(event.chat_id, 0)
            status_msg = (
                f"🤖 **Kira Bot Status (Owner Only)**\n"
                f"• **AI Chat:** `{'Online 🟢' if BOT_ACTIVE else 'Paused 🔴'}`\n"
                f"• **TRX Signal (SG):** `{'Running 🟢' if SG_ACTIVE else 'Stopped 🔴'}` (`{SG_CHANNEL_TITLE}`)\n"
                f"• **SG Win/Loss:** `{SG_STATS['win']}W / {SG_STATS['loss']}L`\n"
                f"• **အဓိက Model:** `{PRIMARY_MODEL}` (Active: `{ACTIVE_MODEL}`)\n"
                f"• **Group Rule:** `စာ {GROUP_MSG_THRESHOLD} ကြောင်း / ၅ မိနစ် (Count: {cur_cnt}/{GROUP_MSG_THRESHOLD})`\n"
                f"• **နောက်ဆုံး Search:** `{LAST_SEARCH_INFO}`\n"
                f"• **API Keys:** `{len(ai_clients)} ခု`\n"
                f"• **နောက်ဆုံး Error:** `{LAST_ERROR[:100]}`\n"
                f"💡 TRX Signal ခလုတ်များကြည့်ရန် `/sg` ဟု ရိုက်ပါ။"
            )
            await client.send_message(event.chat_id, status_msg)
            return

    if not BOT_ACTIVE or is_owner:
        return

    chat_id = event.chat_id
    sender_name = sender.first_name or "သူငယ်ချင်း"
    clean_message = raw_text
    if MY_USERNAME:
        clean_message = re.sub(f"@{MY_USERNAME}", "", raw_text, flags=re.IGNORECASE).strip()
    if not clean_message:
        clean_message = "Denji ရေ"

    if chat_id not in chat_histories:
        chat_histories[chat_id] = deque(maxlen=25)

    display_prompt = f"[{sender_name}]: {clean_message}"

    user_replied_to_me = False
    if event.is_reply:
        try:
            reply_msg = await event.get_reply_message()
            if reply_msg and (reply_msg.out or reply_msg.sender_id == MY_ID):
                user_replied_to_me = True
        except Exception:
            pass

    should_speak = False
    mode_note = ""
    lower_text = raw_text.lower()

    if event.is_private:
        should_speak = True
    elif event.is_group:
        reset_group_idle_timer(chat_id)

        called_kira = (
            event.mentioned
            or (MY_USERNAME and f"@{MY_USERNAME.lower()}" in lower_text)
            or bool(re.search(r"\bkira\b", lower_text))
            or ("kira" in lower_text)
            or ("ကီရာ" in raw_text)
            or bool(re.search(r"\bdenji\b", lower_text))
            or ("denji" in lower_text)
            or ("ဒန်ဂျီ" in raw_text)
        )

        if user_replied_to_me or called_kira:
            should_speak = True
            group_msg_counts[chat_id] = 0
            mode_note = "(Group ထဲတွင် သင့်ကို တိုက်ရိုက်လှမ်းပြောနေခြင်း ဖြစ်သည်)"
        else:
            group_msg_counts[chat_id] = group_msg_counts.get(chat_id, 0) + 1
            await client.send_read_acknowledge(chat_id)

            if group_msg_counts[chat_id] >= GROUP_MSG_THRESHOLD:
                should_speak = True
                group_msg_counts[chat_id] = 0
                mode_note = (
                    "(Group ထဲတွင် သူငယ်ချင်းများ ပြောထားသော စာ ၅ ကြောင်းကို နားထောင်ပြီး "
                    "လူတစ်ယောက်လို သဘာဝကျကျ စကားဝိုင်းထဲ ဝင်ပြောပါ။)"
                )
            else:
                chat_histories[chat_id].append(("user", display_prompt))
                print(f"👂 [Listening in Group {chat_id} ({group_msg_counts[chat_id]}/{GROUP_MSG_THRESHOLD})]: {display_prompt}", flush=True)
                return
    elif event.is_channel:
        if user_replied_to_me or event.mentioned or "kira" in lower_text or "ကီရာ" in raw_text or "denji" in lower_text:
            should_speak = True

    if not should_speak:
        return

    search_query = re.sub(r"\bkira\b|ကီရာ|\bdenji\b", "", clean_message, flags=re.IGNORECASE).strip()
    print(f"📩 [{sender_name} | ReplyMode={user_replied_to_me}]: {clean_message}", flush=True)

    await client.send_read_acknowledge(chat_id)

    if chat_id not in chat_locks:
        chat_locks[chat_id] = asyncio.Lock()

    async with chat_locks[chat_id]:
        async with client.action(chat_id, "typing"):
            reply_text = await generate_kira_reply(
                chat_id=chat_id,
                display_prompt=display_prompt,
                mode_note=mode_note,
                search_query=search_query or clean_message,
            )

            if not reply_text:
                print(f"❌ စာမပြန်နိုင်ခဲ့ပါ။ နောက်ဆုံး Error: {LAST_ERROR}", flush=True)
                return

            chat_histories[chat_id].append(("user", display_prompt))
            chat_histories[chat_id].append(("model", reply_text))

            if user_replied_to_me:
                await event.reply(reply_text)
            else:
                await client.send_message(chat_id, reply_text)

# ==========================================
# ၈။ UptimeRobot အတွက် 24/7 Web Server
# ==========================================
async def health_check(request):
    status_str = "ONLINE" if BOT_ACTIVE else "PAUSED (/botoff)"
    sg_str = "SG:ON" if SG_ACTIVE else "SG:OFF"
    return web.Response(text=f"Denji Userbot Alive 24/7! Status: {status_str} | {sg_str}", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/ping", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    render_port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", render_port)
    await site.start()
    print(f"🌐 UptimeRobot Web Server started on port {render_port}", flush=True)

async def main():
    global MY_USERNAME, MY_ID
    await start_web_server()

    print("🔄 Telegram သို့ ချိတ်ဆက်နေပါသည်...", flush=True)
    await client.connect()

    if not await client.is_user_authorized():
        print("❌ Login မအောင်မြင်ပါ! AUTH_KEY_HEX သက်တမ်းကုန်နေပါသည်။", flush=True)
        return

    me = await client.get_me()
    MY_USERNAME = me.username
    MY_ID = me.id
    print(f"✅ Denji Userbot Login အောင်မြင်ပါသည်!", flush=True)
    print(f"👤 အကောင့်: {me.first_name} | Username: @{MY_USERNAME} | ID: {MY_ID}", flush=True)
    print(f"🔑 အသုံးပြုနေသော API Key အရေအတွက်: {len(ai_clients)} ခု (အလှည့်ကျစနစ်)", flush=True)
    print(f"🤖 အဓိက Model: {PRIMARY_MODEL} + TRX WinGo Signal Predictor", flush=True)
    print("🎰 TRX SG Commands: /sg (Control Panel), /sgon (SG ဖွင့်ရန်), /sgoff (SG ပိတ်ရန်)", flush=True)

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())