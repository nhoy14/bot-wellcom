import discord
from discord.ext import commands, tasks
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

# --- 🟢 ១. SETUP & DATABASE ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

try:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
    db = client['discord_bot']
    collection = db['voice_activity']
    print("✅ [DATABASE] Connected!")
except Exception as e:
    print(f"❌ [DATABASE] Error: {e}")
    collection = None

# --- 🔵 ២. CONFIGURATION (IDs) ---
WELCOME_CHANNEL_ID = 1492953340584399009
LEADERBOARD_CHANNEL_ID = 1492953771423043695 
CREATE_CHANNEL_ID = 1494254070632939591      
PARENT_CATEGORY_ID = 1494236441725767701     

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)
active_sessions = {}

# --- 🟡 ៣. UI FUNCTIONS ---
def format_time(seconds):
    hours, remainder = divmod(int(seconds), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02}h {minutes:02}m"

async def get_leaderboard_embed():
    if collection is None: return discord.Embed(description="Database Error")
    
    data = list(collection.find().sort("total_seconds", -1).limit(10))
    
    embed = discord.Embed(
        title="✨ TEMPERATURE VOICE LEADERBOARD ✨",
        description="🏆 តារាងអ្នកសកម្មបំផុតក្នុង Voice Channels គ្រប់ជាន់ថ្នាក់\n" + "—" * 25,
        color=0x2b2d31
    )

    if not data:
        embed.description += "\n⌛ មិនទាន់មានទិន្នន័យនៅឡើយទេ..."
    else:
        # --- 🥇 CURRENT CHAMPION (លេខ ១) ---
        top1 = data[0]
        u1 = bot.get_user(int(top1['user_id']))
        u1_text = u1.mention if u1 else f"ID: {top1['user_id']}"
        join_date = top1.get('first_join', "Apr 09, 2026")
        
        if u1:
            embed.set_thumbnail(url=u1.display_avatar.url)
            
        embed.add_field(
            name="🥇 CURRENT CHAMPION",
            value=(
                f"┣ 🥇 01 | **{u1_text}**\n"
                f"┣ ⌚ Time: `{format_time(top1['total_seconds'])}`\n"
                f"┗ 📅 Joined: `{join_date}`\n"
                + "—" * 20
            ),
            inline=False
        )

        # --- 📜 TOP CONTENDERS (លេខ ២ ដល់ ១០) ---
        contenders_text = ""
        medals = {2: "🥈", 3: "🥉"}
        
        for i, info in enumerate(data[1:], start=2):
            user = bot.get_user(int(info['user_id']))
            duration = format_time(info['total_seconds'])
            
            if i <= 3:
                name_display = user.mention if user else f"ID: {info['user_id']}"
                medal = medals[i]
            else:
                name_display = f"**{user.name}**" if user else f"ID: {info['user_id']}"
                medal = "🏅"

            contenders_text += f"{medal} `{i:02d}` | {name_display} — `{duration}`\n"

        if contenders_text:
            embed.add_field(name="📜 TOP CONTENDERS", value=contenders_text, inline=False)

    embed.set_footer(text=f"Temperature System • Daily Refresh", icon_url=bot.user.display_avatar.url)
    embed.timestamp = datetime.now()
    return embed

# --- 🔴 ៤. EVENTS & LOGIC ---

@bot.event
async def on_ready():
    print(f'✅ Bot Status: ONLINE ({bot.user.name})')
    if not auto_update_leaderboard.is_running():
        auto_update_leaderboard.start()

@bot.event
async def on_voice_state_update(member, before, after):
    u_id = str(member.id)
    now = time.time()

    # Voice Tracking
    if before.channel is None and after.channel is not None:
        active_sessions[u_id] = now
    elif before.channel is not None and after.channel is None:
        if u_id in active_sessions:
            duration = now - active_sessions.pop(u_id)
            if collection is not None:
                collection.update_one(
                    {"user_id": u_id},
                    {"$inc": {"total_seconds": duration}, "$setOnInsert": {"first_join": datetime.now().strftime("%b %d, %Y")}},
                    upsert=True
                )

    # Auto Create System
    if after.channel and after.channel.id == CREATE_CHANNEL_ID:
        guild = member.guild
        parent_cat = guild.get_channel(PARENT_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            member: discord.PermissionOverwrite(manage_channels=True, manage_permissions=True, move_members=True)
        }
        new_cat = await guild.create_category(name=f"⭐ {member.name}'s Space", overwrites=overwrites, position=parent_cat.position + 1 if parent_cat else None)
        new_ch = await guild.create_voice_channel(name=f"🎙️ │ {member.name}'s Room", category=new_cat)
        await member.move_to(new_ch)

    # Cleanup System
    if before.channel and before.channel.category and "⭐" in before.channel.category.name:
        if len(before.channel.members) == 0:
            category = before.channel.category
            await before.channel.delete()
            await category.delete()

# --- 🟠 ៥. ERROR HANDLING (ពេល User វាយបញ្ជាខុស) ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❌ បញ្ជាមិនត្រឹមត្រូវ!",
            description=f"មិនមានបញ្ជា `{ctx.invoked_with}` ក្នុងប្រព័ន្ធទេ។\n\n💡 បញ្ជាដែលត្រឹមត្រូវគឺ: `.top` ឬ `.me`",
            color=0xff0000
        )
        await ctx.send(embed=embed, delete_after=10)

# --- 🟣 ៦. TASKS & COMMANDS ---

@tasks.loop(hours=5)
async def auto_update_leaderboard():
    channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
    if channel:
        await channel.purge(limit=5)
        await channel.send(embed=await get_leaderboard_embed())

@bot.command()
async def top(ctx):
    """មើលតារាងអ្នកសកម្មបំផុតទាំង ១០"""
    await ctx.send(embed=await get_leaderboard_embed())

@bot.command(aliases=['topme', 'profile'])
async def me(ctx):
    """មើលព័ត៌មានផ្ទាល់ខ្លួនរបស់អ្នក"""
    u_id = str(ctx.author.id)
    user_data = collection.find_one({"user_id": u_id}) if collection is not None else None
    
    embed = discord.Embed(
        title=f"👤 ព័ត៌មានរបស់ {ctx.author.name}",
        color=ctx.author.color,
        timestamp=datetime.now()
    )
    
    if user_data:
        total_seconds = user_data.get('total_seconds', 0)
        join_date = user_data.get('first_join', "មិនមានទិន្នន័យ")
        
        embed.add_field(name="⏱️ ម៉ោងសរុបក្នុង Voice", value=f"`{format_time(total_seconds)}`", inline=True)
        embed.add_field(name="📅 ថ្ងៃចូល Server", value=f"`{join_date}`", inline=True)
    else:
        embed.description = "⌛ មិនទាន់មានទិន្នន័យសកម្មភាពរបស់អ្នកនៅឡើយទេ។"

    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"ID: {ctx.author.id}")
    await ctx.send(embed=embed)

bot.run(TOKEN)