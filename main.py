import discord
from discord.ext import commands, tasks
import os
import time
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
import certifi

# --- 🟢 1. SETUP & DATABASE ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

# Database Connection
try:
    client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
    db = client['discord_bot']
    collection = db['voice_activity']
    print("✅ [DATABASE] Connected!")
except Exception as e:
    print(f"❌ [DATABASE] Error: {e}")
    collection = None

# --- 🔵 2. CONFIGURATION (IDs) ---
STAY_VOICE_CHANNEL_ID = 1495160098216218675
WELCOME_CHANNEL_ID    = 1492953340584399009
LEADERBOARD_CHANNEL_ID= 1492953771423043695
CREATE_CHANNEL_ID     = 1494254070632939591
PARENT_CATEGORY_ID    = 1494236441725767701

# 🎭 Auto Role — ID of role to give every new member (set your role ID here)
AUTO_ROLE_ID = 0  # ← ដាក់ ID Role របស់អ្នក

# 🏆 Rank Roles — (min_hours, role_id, label)
RANK_ROLES = [
    (1,   0, "🌱 Newcomer"),   # ← ដាក់ Role IDs
    (5,   0, "🔥 Active"),
    (20,  0, "💎 Veteran"),
    (50,  0, "👑 Legend"),
]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='.', intents=intents)
active_sessions = {}

# --- 🟡 3. HELPER FUNCTIONS ---
def format_time(seconds):
    hours, remainder = divmod(int(seconds), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02}h {minutes:02}m"

async def get_leaderboard_embed():
    if collection is None:
        return discord.Embed(description="Database Error")

    data = list(collection.find().sort("total_seconds", -1).limit(10))
    embed = discord.Embed(
        title="✨ TEMPERATURE VOICE LEADERBOARD ✨",
        description="🏆 តារាងអ្នកសកម្មបំផុតក្នុង Voice Channels គ្រប់ជាន់ថ្នាក់\n" + "—" * 25,
        color=0x2b2d31
    )

    if not data:
        embed.description += "\n⌛ មិនទាន់មានទិន្នន័យនៅឡើយទេ..."
    else:
        top1 = data[0]
        try:
            u1 = bot.get_user(int(top1['user_id'])) or await bot.fetch_user(int(top1['user_id']))
        except Exception:
            u1 = None
        u1_text  = u1.mention if u1 else f"ID: {top1['user_id']}"
        join_date = top1.get('first_join', "Unknown")

        if u1:
            embed.set_thumbnail(url=u1.display_avatar.url)

        embed.add_field(
            name="🥇 CURRENT CHAMPION",
            value=(f"┣ 🥇 01 | **{u1_text}**\n"
                   f"┣ ⌚ Time: `{format_time(top1['total_seconds'])}`\n"
                   f"┗ 📅 Joined: `{join_date}`\n" + "—" * 20),
            inline=False
        )

        contenders_text = ""
        medals = {2: "🥈", 3: "🥉"}
        for i, info in enumerate(data[1:], start=2):
            try:
                user = bot.get_user(int(info['user_id'])) or await bot.fetch_user(int(info['user_id']))
            except Exception:
                user = None
            duration    = format_time(info['total_seconds'])
            name_display = (
                user.mention if user and i <= 3
                else (f"**{user.name}**" if user else f"ID: {info['user_id']}")
            )
            medal = medals.get(i, "🏅")
            contenders_text += f"{medal} `{i:02d}` | {name_display} — `{duration}`\n"

        if contenders_text:
            embed.add_field(name="📜 TOP CONTENDERS", value=contenders_text, inline=False)

    embed.set_footer(text="Temperature System • Daily Refresh", icon_url=bot.user.display_avatar.url)
    embed.timestamp = datetime.now()
    return embed

async def force_join_stay_channel():
    channel = bot.get_channel(STAY_VOICE_CHANNEL_ID)
    if not channel:
        print(f"❌ [VOICE ERROR] Could not find channel ID: {STAY_VOICE_CHANNEL_ID}")
        return
    existing_vc = discord.utils.get(bot.voice_clients, guild=channel.guild)
    if existing_vc:
        if existing_vc.channel.id == STAY_VOICE_CHANNEL_ID:
            return
        await existing_vc.disconnect(force=True)
    try:
        await channel.connect(reconnect=True, timeout=20)
        print(f"🎙️ [VOICE] Bot joined: {channel.name}")
    except Exception as e:
        print(f"❌ [VOICE ERROR]: {e}")

async def update_rank_role(member, total_seconds):
    """Give the highest earned rank role and remove lower ones."""
    if not RANK_ROLES or all(r[1] == 0 for r in RANK_ROLES):
        return  # Rank roles not configured yet
    total_hours = total_seconds / 3600
    earned_role_id = None
    for min_hours, role_id, _ in RANK_ROLES:
        if total_hours >= min_hours and role_id != 0:
            earned_role_id = role_id

    all_rank_ids = {r[1] for r in RANK_ROLES if r[1] != 0}
    for role_id in all_rank_ids:
        role = member.guild.get_role(role_id)
        if not role:
            continue
        if role_id == earned_role_id:
            if role not in member.roles:
                await member.add_roles(role)
        else:
            if role in member.roles:
                await member.remove_roles(role)

# --- 🔴 4. EVENTS ---

@bot.event
async def on_ready():
    print(f'✅ Bot Status: ONLINE ({bot.user.name})')
    if not auto_update_leaderboard.is_running():
        auto_update_leaderboard.start()
    await force_join_stay_channel()

@bot.event
async def on_member_join(member):
    """Welcome new member + give Auto Role."""
    # 🎭 Auto Role
    if AUTO_ROLE_ID != 0:
        role = member.guild.get_role(AUTO_ROLE_ID)
        if role:
            try:
                await member.add_roles(role)
                print(f"✅ [AUTO ROLE] Given '{role.name}' to {member.name}")
            except Exception as e:
                print(f"❌ [AUTO ROLE ERROR]: {e}")

    # 👋 Welcome Message
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return

    member_count = member.guild.member_count
    embed = discord.Embed(
        title="🎊 សមាជិកថ្មីបានចូលហើយ! 🎊",
        description=(
            f"សូស្តី {member.mention}! សូមស្វាគមន៍មកកាន់ **{member.guild.name}**!\n\n"
            f"☀️ វីតាយដែលជាអ្នកមកត្រូលរួមមានមូវវ័យព្យួរឈ្នះ!\n"
            f"📋 សូមអានច្បាប់ និងវីតាយដែលអ្នកយការផែកណែណពេលអ្នកព្យួរឈ្នះ!\n"
        ),
        color=0xf1c40f,
        timestamp=datetime.now()
    )
    embed.add_field(name="🔢 សមាជិកទី", value=str(member_count), inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(
        text=f"Welcome to {member.guild.name}",
        icon_url=member.guild.icon.url if member.guild.icon else None
    )
    await channel.send(content=f"សូមស្វាគមន៍សមាជិកថ្មី! {member.mention}", embed=embed)

    # 💾 Save first_join date to MongoDB when user joins server
    if collection is not None:
        collection.update_one(
            {"user_id": str(member.id)},
            {"$setOnInsert": {
                "user_id": str(member.id),
                "total_seconds": 0,
                "first_join": datetime.now().strftime("%b %d, %Y")
            }},
            upsert=True
        )

@bot.event
async def on_member_remove(member):
    """Send a goodbye message when a member leaves."""
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if not channel:
        return

    embed = discord.Embed(
        title="👋 សមាជិកបានចាកចេញ...",
        description=(
            f"**{member.name}** បានចាកចេញពី **{member.guild.name}**។\n\n"
            f"សូមអរគុណដែលបានចូលរួមជាមួយពួកយើង! 🙏"
        ),
        color=0x95a5a6,
        timestamp=datetime.now()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name="👥 សមាជិកសល់",
        value=str(member.guild.member_count),
        inline=False
    )
    embed.set_footer(
        text=f"Temperature System • {member.guild.name}",
        icon_url=member.guild.icon.url if member.guild.icon else None
    )
    await channel.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    u_id = str(member.id)
    now  = time.time()

    # --- Part A: Bot Self-Correction ---
    if member.id == bot.user.id and after.channel is None:
        print("⚠️ Bot was disconnected. Rejoining...")
        await asyncio.sleep(2)
        await force_join_stay_channel()
        return

    # --- Part B: Voice Tracking ---
    joined   = before.channel is None and after.channel is not None
    left     = before.channel is not None and after.channel is None
    switched = (before.channel is not None and after.channel is not None
                and before.channel.id != after.channel.id)

    if joined:
        active_sessions[u_id] = now

    elif left:
        if u_id in active_sessions:
            duration = now - active_sessions.pop(u_id)
            _save_voice_time(u_id, duration)
            # 🏆 Update rank role after saving time
            user_data = collection.find_one({"user_id": u_id}) if collection else None
            if user_data:
                await update_rank_role(member, user_data.get('total_seconds', 0))

    elif switched:
        if u_id in active_sessions:
            duration = now - active_sessions[u_id]
            _save_voice_time(u_id, duration)
        active_sessions[u_id] = now

    # --- Part C: Auto Create System ---
    if after.channel and after.channel.id == CREATE_CHANNEL_ID:
        guild      = member.guild
        parent_cat = guild.get_channel(PARENT_CATEGORY_ID)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True),
            member: discord.PermissionOverwrite(
                manage_channels=True, manage_permissions=True, move_members=True
            )
        }
        new_cat = await guild.create_category(
            name=f"⭐ {member.name}'s Space",
            overwrites=overwrites,
            position=parent_cat.position + 1 if parent_cat else None
        )
        new_ch = await guild.create_voice_channel(
            name=f"🎙️ │ {member.name}'s Room",
            category=new_cat
        )
        await member.move_to(new_ch)

    # --- Part D: Cleanup System ---
    if before.channel and before.channel.category and "⭐" in before.channel.category.name:
        category  = before.channel.category
        all_empty = all(len(ch.members) == 0 for ch in category.voice_channels)
        if all_empty:
            for ch in category.channels:
                await ch.delete()
            await category.delete()

def _save_voice_time(user_id: str, duration: float):
    if collection is None or duration < 1:
        return

    today = datetime.now().strftime("%b %d, %Y")

    # Step 1: Upsert — create document if not exists, always add time
    collection.update_one(
        {"user_id": user_id},
        {"$inc": {"total_seconds": duration}},
        upsert=True
    )

    # Step 2: If first_join is missing (old users or new), set it now
    collection.update_one(
        {"user_id": user_id, "first_join": {"$exists": False}},
        {"$set": {"first_join": today}}
    )

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❌ បញ្ជាមិនត្រឹមត្រូវ!",
            description=f"មិនមានបញ្ជា `{ctx.invoked_with}` ក្នុងប្រព័ន្ធទេ។\n\n💡 បញ្ជាដែលត្រឹមត្រូវគឺ: `.top`, `.me`, `.stats`",
            color=0xff0000
        )
        await ctx.send(embed=embed, delete_after=10)

# --- 🟣 5. TASKS & COMMANDS ---

@tasks.loop(hours=24)
async def auto_update_leaderboard():
    channel = bot.get_channel(LEADERBOARD_CHANNEL_ID)
    if channel:
        await channel.purge(limit=5)
        await channel.send(embed=await get_leaderboard_embed())

@bot.command()
async def top(ctx):
    """View the Top 10 Active Users"""
    await ctx.send(embed=await get_leaderboard_embed())

@bot.command(aliases=['topme', 'profile'])
async def me(ctx):
    """View your personal voice stats — table style like image"""
    u_id      = str(ctx.author.id)
    user_data = collection.find_one({"user_id": u_id}) if collection is not None else None

    if not user_data:
        embed = discord.Embed(
            description="⌛ មិនទាន់មានទិន្នន័យសកម្មភាពរបស់អ្នកនៅឡើយទេ។",
            color=0x2b2d31
        )
        await ctx.send(embed=embed)
        return

    total_seconds = user_data.get('total_seconds', 0)
    join_date     = user_data.get('first_join', "Unknown")

    # Calculate rank position from leaderboard
    all_users = list(collection.find().sort("total_seconds", -1))
    rank_pos  = next((i + 1 for i, d in enumerate(all_users) if d['user_id'] == u_id), None)
    rank_str  = f"🏆 #{rank_pos}" if rank_pos else "—"

    # Build table-style embed matching the image
    embed = discord.Embed(
        title="📊 Your Voice Rank Status",
        color=0x2b2d31,
        timestamp=datetime.now()
    )

    # Table header + row using inline fields (3 columns)
    embed.add_field(name="User",       value=ctx.author.mention,          inline=True)
    embed.add_field(name="Your Rank",  value=rank_str,                    inline=True)
    embed.add_field(name="Total Time", value=format_time(total_seconds),  inline=True)

    # Joined date below table
    embed.add_field(name="​", value=f"Joined: {join_date}", inline=False)

    embed.set_thumbnail(url=ctx.author.display_avatar.url)
    embed.set_footer(
        text=f"Welcome to {ctx.guild.name}",
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )
    await ctx.send(embed=embed)

@bot.command()
async def stats(ctx):
    """View overall server voice statistics"""
    if collection is None:
        await ctx.send("❌ Database មិនអាចភ្ជាប់បានទេ។")
        return

    total_users   = collection.count_documents({})
    total_data    = list(collection.find())
    total_seconds = sum(d.get('total_seconds', 0) for d in total_data)

    # Active right now
    active_now = len(active_sessions)

    embed = discord.Embed(
        title="📊 ស្ថិតិ Server — Temperature",
        color=0x3498db,
        timestamp=datetime.now()
    )
    embed.add_field(name="👥 សមាជិកសរុប",          value=f"`{ctx.guild.member_count}`",     inline=True)
    embed.add_field(name="🎙️ នៅក្នុង Voice ឥឡូវ", value=f"`{active_now} នាក់`",             inline=True)
    embed.add_field(name="📋 អ្នកមានទិន្នន័យ",     value=f"`{total_users} នាក់`",             inline=True)
    embed.add_field(name="⏱️ ម៉ោង Voice សរុប",     value=f"`{format_time(total_seconds)}`",  inline=True)

    # Top 3 quick summary
    top3 = list(collection.find().sort("total_seconds", -1).limit(3))
    top3_text = ""
    medals = ["🥇", "🥈", "🥉"]
    for i, d in enumerate(top3):
        try:
            u = bot.get_user(int(d['user_id'])) or await bot.fetch_user(int(d['user_id']))
            name = u.name if u else f"ID:{d['user_id']}"
        except Exception:
            name = f"ID:{d['user_id']}"
        top3_text += f"{medals[i]} **{name}** — `{format_time(d['total_seconds'])}`\n"

    if top3_text:
        embed.add_field(name="🏆 Top 3", value=top3_text, inline=False)

    embed.set_footer(text="Temperature System", icon_url=bot.user.display_avatar.url)
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else discord.Embed.Empty)
    await ctx.send(embed=embed)

# Run the Bot
bot.run(TOKEN)