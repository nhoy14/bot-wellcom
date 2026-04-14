import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# --- ១. ទាញយក Token ពី Environment ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# --- ២. កំណត់ Intents (សិទ្ធិរបស់ Bot) ---
intents = discord.Intents.default()
intents.members = True          # សំខាន់៖ ដើម្បីដឹងពេលមានសមាជិកចូល
intents.message_content = True  # សំខាន់៖ ដើម្បីឱ្យ Command .tes ដើរ

bot = commands.Bot(command_prefix='.', intents=intents)

# --- ៣. កំណត់ ID របស់ Channel Welcome ---
WELCOME_CHANNEL_ID = 1492953340584399009 

@bot.event
async def on_ready():
    print(f'-------------------------------------')
    print(f'✅ Bot Online: {bot.user.name}')
    print(f'🚀 Hosted on Render successfully!')
    print(f'-------------------------------------')

# --- ៤. មុខងារស្វាគមន៍ពេលមានសមាជិកចូល ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    
    if channel:
        embed = discord.Embed(
            title="🌸 សមាជិកថ្មីបានមកដល់ហើយ! 🌸",
            description=f"សួស្តី {member.mention}! ស្វាគមន៍មកកាន់ Server **{member.guild.name}**។\nរីករាយដែលបានអ្នកមកចូលរួមជាមួយពួកយើង!",
            color=0xFFA2D2
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url="https://i.pinimg.com/originals/07/33/ba/0733ba76ca26955a3059293144930d31.gif")
        
        guild_icon = member.guild.icon.url if member.guild.icon else None
        embed.set_footer(text=f"អ្នកគឺជាសមាជិកទី {len(member.guild.members)}!", icon_url=guild_icon)
        
        await channel.send(content=f"សួស្តី {member.mention}! 🤗", embed=embed)
        print(f"✅ បានផ្ញើសារស្វាគមន៍ទៅកាន់: {member.name}")

# --- ៥. Command សម្រាប់តេស្ត (.tes) ---
@bot.command()
async def tes(ctx):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await ctx.send("⌛ កំពុងតេស្តផ្ញើសារស្វាគមន៍...")
        embed = discord.Embed(
            title="✨ Test Message ✨",
            description="Bot របស់អ្នកកំពុងដំណើរការបានយ៉ាងល្អលើ Cloud!",
            color=0x00FF00
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await channel.send(embed=embed)
    else:
        await ctx.send(f"❌ រក Channel ID `{WELCOME_CHANNEL_ID}` មិនឃើញ!")

# --- ៦. ចាប់ផ្ដើម Bot ---
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ Error: រកមិនឃើញ DISCORD_TOKEN ក្នុង Environment Variables ទេ។")