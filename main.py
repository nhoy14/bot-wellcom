import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os

# --- ផ្នែកសម្រាប់ Hosting (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is Online!"

def run():
    # Render ប្រើ Port 10000 ជាទូទៅ ប៉ុន្តែយើងប្រើ os.getenv ដើម្បីសុវត្ថិភាព
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- ផ្នែក Bot របស់អ្នក ---
intents = discord.Intents.default()
intents.members = True          
intents.message_content = True  

bot = commands.Bot(command_prefix='.', intents=intents)

WELCOME_CHANNEL_ID = 1492953340584399009 

@bot.event
async def on_ready():
    print(f'-------------------------------------')
    print(f'✅ បុបបុប! {bot.user.name} Is Online on Render!')
    print(f'-------------------------------------')

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🌸 សមាជិកថ្មីបានមកដល់ហើយ! 🌸",
            description=f"សួស្តី {member.mention}! ស្វាគមន៍មកកាន់ Server **{member.guild.name}**។",
            color=0xFFA2D2
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url="https://i.pinimg.com/originals/07/33/ba/0733ba76ca26955a3059293144930d31.gif")
        embed.set_footer(text=f"សមាជិកទី {len(member.guild.members)}")
        await channel.send(content=f"សួស្តី {member.mention}! 🤗", embed=embed)

@bot.command()
async def tes(ctx):
    await ctx.send("⌛ Bot ដំណើរការបានយ៉ាងល្អលើ Hosting!")

# --- ដំណើរការ Web Server និង Bot ---
keep_alive()
bot.run('MTQ5MzM0NTU3NTcwNDE5OTE4OA.GJlfou.oNhS3hpDU1X3c_1oNuGoYgzdivsZ-TvNHZ3J_4')