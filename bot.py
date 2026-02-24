from keep_alive import keep_alive
keep_alive()
import discord
from discord.ext import commands, tasks
import requests
import json
import os

# ===== ตั้งค่า =====
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHANNEL_ID = 1475704537334415594  # ใส่ ID ช่องที่ต้องการส่งแจ้งเตือน
TARGET_USER = "DistrokidOfficial"  # ชื่อผู้ใช้ Roblox ที่ต้องการดัก

# ===== เก็บ ID เพลงที่เคยแจ้งแล้ว =====
SEEN_FILE = "seen_sounds.json"

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seen(seen_set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen_set), f)

seen_sounds = load_seen()

# ===== ดึงข้อมูล User ID จากชื่อ =====
def get_user_id(username):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": False}
    r = requests.post(url, json=payload)
    data = r.json()
    if data.get("data"):
        return data["data"][0]["id"]
    return None

# ===== ดึงเพลงของผู้ใช้ =====
def get_user_sounds(user_id):
    url = f"https://catalog.roblox.com/v1/search/items"
    params = {
        "category": "Audio",
        "creatorTargetId": user_id,
        "creatorType": "User",
        "limit": 30,
        "sortType": "3"  # ล่าสุดก่อน
    }
    r = requests.get(url, params=params)
    return r.json().get("data", [])

# ===== ดึงรายละเอียดเพลง =====
def get_sound_detail(asset_id):
    url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
    r = requests.get(url)
    return r.json()

# ===== ดึงรูป Thumbnail ของเพลง =====
def get_sound_thumbnail(asset_id):
    url = "https://thumbnails.roblox.com/v1/assets"
    params = {
        "assetIds": asset_id,
        "size": "150x150",
        "format": "Png"
    }
    r = requests.get(url, params=params)
    data = r.json()
    if data.get("data"):
        return data["data"][0].get("imageUrl", "")
    return ""

# ===== ตั้งค่าบอท =====
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ บอทออนไลน์แล้ว: {bot.user}")
    if not check_new_sounds.is_running():
        check_new_sounds.start()

# ===== Loop ตรวจสอบเพลงใหม่ทุก 60 วินาที =====
@tasks.loop(seconds=60)
async def check_new_sounds():
    global seen_sounds
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ ไม่พบช่อง Discord")
        return

    user_id = get_user_id(TARGET_USER)
    if not user_id:
        print(f"❌ ไม่พบผู้ใช้ {TARGET_USER}")
        return

    sounds = get_user_sounds(user_id)

    for sound in sounds:
        asset_id = sound.get("id")
        if asset_id and str(asset_id) not in seen_sounds:
            seen_sounds.add(str(asset_id))
            save_seen(seen_sounds)

            # ดึงรายละเอียด
            detail = get_sound_detail(asset_id)
            thumbnail = get_sound_thumbnail(asset_id)

            name = detail.get("Name", "ไม่ทราบชื่อ")
            description = detail.get("Description", "-")
            play_url = f"https://www.roblox.com/catalog/{asset_id}"
            sound_url = f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"

            # สร้าง Embed
            embed = discord.Embed(
                title=f"🎵 เพลงใหม่จาก {TARGET_USER}!",
                description=f"**{name}**",
                color=0x00ff99,
                url=play_url
            )
            embed.add_field(name="🆔 Sound ID", value=str(asset_id), inline=True)
            embed.add_field(name="📝 คำอธิบาย", value=description[:100] if description else "-", inline=False)
            embed.add_field(name="🔗 กดฟังเพลง", value=f"[คลิกที่นี่]({play_url})", inline=False)
            embed.add_field(name="📥 ลิงก์ไฟล์เสียง", value=f"[เปิดไฟล์เสียง]({sound_url})", inline=False)

            if thumbnail:
                embed.set_thumbnail(url=thumbnail)

            embed.set_footer(text=f"ผู้สร้าง: {TARGET_USER} | User ID: {user_id}")

            await channel.send(embed=embed)
            print(f"✅ ส่งแจ้งเตือนเพลง: {name} (ID: {asset_id})")

# ===== คำสั่ง !sounds ดูเพลงล่าสุดทันที =====
@bot.command()
async def sounds(ctx):
    await ctx.send(f"🔍 กำลังดึงเพลงล่าสุดของ **{TARGET_USER}**...")
    user_id = get_user_id(TARGET_USER)
    if not user_id:
        await ctx.send("❌ ไม่พบผู้ใช้")
        return

    sounds_list = get_user_sounds(user_id)[:5]
    for sound in sounds_list:
        asset_id = sound.get("id")
        detail = get_sound_detail(asset_id)
        thumbnail = get_sound_thumbnail(asset_id)
        name = detail.get("Name", "ไม่ทราบชื่อ")
        play_url = f"https://www.roblox.com/catalog/{asset_id}"
        sound_url = f"https://assetdelivery.roblox.com/v1/asset/?id={asset_id}"

        embed = discord.Embed(
            title=f"🎵 {name}",
            color=0x5865F2,
            url=play_url
        )
        embed.add_field(name="🆔 Sound ID", value=str(asset_id), inline=True)
        embed.add_field(name="🔗 กดฟังเพลง", value=f"[คลิกที่นี่]({play_url})", inline=False)
        embed.add_field(name="📥 ไฟล์เสียง", value=f"[เปิดไฟล์เสียง]({sound_url})", inline=False)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        await ctx.send(embed=embed)

bot.run(BOT_TOKEN)
