import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import time
from datetime import datetime
from pymongo import MongoClient
import certifi # ប្រើសម្រាប់ដោះស្រាយបញ្ហា SSL Handshake Failed

# --- ១. ការកំណត់សុវត្ថិភាព និងការភ្ជាប់ Database ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
MONGO_URL = os.getenv('MONGO_URL')

# ប្រកាស Variable ជាសកលសិន ដើម្បីកុំឱ្យ Error NameError
db = None
collection = None

try:
    # បន្ថែម tlsCAFile=certifi.where() ដើម្បីឱ្យការភ្ជាប់មានសុវត្ថិភាពលើ Server ក្រៅ
    client = MongoClient(
        MONGO_URL, 
        serverSelectionTimeoutMS=5000, 
        tlsCAFile=certifi.where()
    )
    client.server_info() 
    db = client['discord_bot']
    collection = db['voice_activity']
    print("✅ [DATABASE] MongoDB Atlas Connected Successfully!")
except Exception as e:
    print(f"❌ [DATABASE] Connection Error: {e}")
    # បើ Connect មិនជាប់ collection នឹងនៅតែ None ដែលយើងនឹងឆែកក្នុង code បន្តទៀត

# --- ការកំណត់ ID Channels ---
GET_ROLES_CHANNEL_ID = 1492953771423043695 
WELCOME_CHANNEL_ID = 1492953340584399009 

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix='.', intents=intents)
dashboard_msg_id = None 
active_sessions = {}

# --- ២. មុខងារជំនួយ (Utility Functions) ---
def format_time(seconds):
    hours, remainder = divmod(int(seconds), 3600)
    minutes, _ = divmod(remainder, 60)
    return f"{hours:02d}h {minutes:02d}m"

async def create_leaderboard_embed():
    """បង្កើត UI សម្រាប់ Dashboard និង .topall"""
    # ឆែកមើលក្រែងលោ Database Connect មិនជាប់
    if collection is None:
        return discord.Embed(title="⚠️ Database Error", description="មិនអាចទាក់ទងទៅកាន់ Database បានទេ!", color=discord.Color.red())

    try:
        data = list(collection.find().sort("total_seconds", -1).limit(10))
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        data = []
    
    embed = discord.Embed(
        title="✨ TEMPERATURE VOICE LEADERBOARD ✨",
        description="🏆 តារាងអ្នកសកម្មបំផុតក្នុង Voice Channels គ្រប់ជាន់ថ្នាក់\n" + "—" * 25,
        color=0x2b2d31, 
        timestamp=datetime.now()
    )

    if not data:
        embed.description += "\n\n*⌛ មិនទាន់មានទិន្នន័យនៅឡើយទេ...*"
    else:
        # TOP 1 Profile
        top1_info = data[0]
        top1_user = bot.get_user(int(top1_info['user_id']))
        t1_name = f"**{top1_user.name}**" if top1_user else f"`ID: {top1_info['user_id']}`"
        
        if top1_user and top1_user.display_avatar:
            embed.set_thumbnail(url=top1_user.display_avatar.url)
        
        embed.add_field(
            name="🥇 CURRENT CHAMPION",
            value=f"{t1_name}\n"
                  f"┣ ⏱️ Time: `{format_time(top1_info['total_seconds'])}`\n"
                  f"┗ 📅 Joined: `{top1_info.get('first_join_server', 'N/A')}`\n" + "—" * 15,
            inline=False
        )

        others_list = ""
        for i, info in enumerate(data[1:10], start=2):
            user = bot.get_user(int(info['user_id']))
            user_display = f"**{user.name}**" if user else f"User({info['user_id']})"
            icon = "🥈" if i == 2 else "🥉" if i == 3 else f"🏅"
            others_list += f"{icon} `{i:02d}` | {user_display} — `{format_time(info['total_seconds'])}`\n"

        if others_list:
            embed.add_field(name="📜 TOP CONTENDERS", value=others_list, inline=False)

    embed.set_footer(text="Temperature System • Daily Refresh", icon_url=bot.user.display_avatar.url)
    return embed

# --- ៣. Welcome System Event ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🎊 សមាជិកថ្មីបានមកដល់ហើយ! 🎊",
            description=f"សួស្តី {member.mention}! ស្វាគមន៍មកកាន់ **Server Temperament**។\n\n"
                        f"🌟 រីករាយដែលបានអ្នកមកចូលរួមជាមួយពួកយើង!\n"
                        f"📜 សូមអានច្បាប់ និងរីករាយជាមួយការជជែកលេងជាមួយពួកយើង!",
            color=0xFFA2D2,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(name=member.name, icon_url=member.display_avatar.url)
        embed.add_field(name="🔢 សមាជិកទី", value=f"{member.guild.member_count}", inline=True)
        embed.set_footer(text=f"Welcome to Temperament", icon_url=member.guild.icon.url if member.guild.icon else None)
        await channel.send(f"ស្វាគមន៍សមាជិកថ្មី! {member.mention}", embed=embed)

# --- ៤. Commands ---
@bot.command()
async def topall(ctx):
    embed = await create_leaderboard_embed()
    await ctx.send(embed=embed)

@bot.command()
async def topme(ctx):
    if collection is None: return await ctx.send("❌ Database មិនទាន់ដំណើរការ។")
    
    all_data = list(collection.find().sort("total_seconds", -1))
    user_id = str(ctx.author.id)
    rank = next((i for i, info in enumerate(all_data, 1) if info['user_id'] == user_id), 0)
    
    if rank:
        user_info = all_data[rank-1]
        embed = discord.Embed(title="📊 Your Voice Rank Status", color=0x3498db)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="User", value=ctx.author.mention, inline=True)
        embed.add_field(name="Your Rank", value=f"🏆 **#{rank}**", inline=True)
        embed.add_field(name="Total Time", value=f"`{format_time(user_info['total_seconds'])}`", inline=True)
        embed.set_footer(text=f"Joined: {user_info.get('first_join_server', 'N/A')}")
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {ctx.author.mention} មិនទាន់មានទិន្នន័យឡើយទេ។")

# --- ៥. Tasks: Auto-Update Dashboard (២៤ ម៉ោងម្ដង) ---
@tasks.loop(hours=24)
async def auto_update_dashboard():
    global dashboard_msg_id
    channel = bot.get_channel(GET_ROLES_CHANNEL_ID)
    if not channel: return
    embed = await create_leaderboard_embed()
    try:
        if dashboard_msg_id:
            msg = await channel.fetch_message(dashboard_msg_id)
            await msg.edit(embed=embed)
        else:
            msg = await channel.send(embed=embed)
            dashboard_msg_id = msg.id
    except:
        msg = await channel.send(embed=embed)
        dashboard_msg_id = msg.id

# --- ៦. Events: Tracking Voice ---
@bot.event
async def on_ready():
    print(f'✅ Bot Status: Online ({bot.user.name})')
    if not auto_update_dashboard.is_running():
        auto_update_dashboard.start()

@bot.event
async def on_voice_state_update(member, before, after):
    if collection is None: return
    u_id = str(member.id)
    now = time.time()
    join_date = member.joined_at.strftime("%b %d, %Y") if member.joined_at else "N/A"

    if before.channel is None and after.channel is not None:
        active_sessions[u_id] = now
    elif before.channel is not None and after.channel is None:
        if u_id in active_sessions:
            try:
                duration = now - active_sessions.pop(u_id)
                collection.update_one(
                    {"user_id": u_id},
                    {"$inc": {"total_seconds": duration}, "$setOnInsert": {"first_join_server": join_date}},
                    upsert=True
                )
            except Exception as e:
                print(f"❌ [DB ERROR] {e}")

bot.run(TOKEN)