import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# --- ១. ទាញយក Token ពី Environment Variables ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# --- ២. ការកំណត់សិទ្ធិ (Intents) ---
intents = discord.Intents.default()
intents.members = True          # ចាំបាច់ដើម្បីដឹងពេលមានសមាជិកចូល
intents.message_content = True  # ចាំបាច់ដើម្បីឱ្យ Bot អាន Command .tes បាន

bot = commands.Bot(command_prefix='.', intents=intents)

# --- ៣. ការកំណត់ ID របស់ Channel Welcome ---
# សូមប្រាកដថា ID នេះត្រឹមត្រូវតាម Server របស់អ្នក
WELCOME_CHANNEL_ID = 1492953340584399009 

@bot.event
async def on_ready():
    print(f'-------------------------------------')
    print(f'✅ បុបបុប! {bot.user.name} ត្រៀមខ្លួនរួចរាល់!')
    print(f'🚀 Bot កំពុងដំណើរការលើ Cloud ហើយ!')
    print(f'-------------------------------------')

# --- ៤. មុខងារស្វាគមន៍ពេលមានសមាជិកចូល (on_member_join) ---
@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    
    if channel:
        embed = discord.Embed(
            title="🌸 សមាជិកថ្មីបានមកដល់ហើយ! 🌸",
            description=f"សួស្តី {member.mention}! ស្វាគមន៍មកកាន់ Server **{member.guild.name}**។\nរីករាយដែលបានអ្នកមកចូលរួមជាមួយពួកយើង! សូមអានច្បាប់ និងរីករាយជាមួយការជជែកលេង!",
            color=0xFFA2D2  # ពណ៌ផ្កាឈូក
        )
        
        # បង្ហាញរូប Profile របស់អ្នកចូលថ្មី
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # រូបភាព GIF ស្វាគមន៍ (អាចដូរ Link នេះបាន)
        embed.set_image(url="https://i.pinimg.com/originals/07/33/ba/0733ba76ca26955a3059293144930d31.gif")
        
        # បង្ហាញចំនួនសមាជិក និង Icon Server
        guild_icon = member.guild.icon.url if member.guild.icon else None
        embed.set_footer(
            text=f"អ្នកគឺជាសមាជិកទី {len(member.guild.members)} របស់យើង!", 
            icon_url=guild_icon
        )
        
        await channel.send(content=f"សួស្តី {member.mention}! 🤗", embed=embed)
        print(f"✅ បានផ្ញើសារស្វាគមន៍ទៅកាន់: {member.name}")

# --- ៥. Command សម្រាប់តេស្ត (.tes) ---
@bot.command()
async def tes(ctx):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await ctx.send("⌛ កំពុងតេស្តផ្ញើសារស្វាគមន៍គំរូ...")
        embed = discord.Embed(
            title="✨ តេស្តសារស្វាគមន៍ (Demo) ✨",
            description=f"សួស្តី {ctx.author.mention}! នេះគឺជាឧទាហរណ៍នៃសារស្វាគមន៍ចេញពី Cloud Hosting។",
            color=0x00FF00
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Bot System: Functional ✅")
        await channel.send(embed=embed)
    else:
        await ctx.send(f"❌ រក Channel ID `{WELCOME_CHANNEL_ID}` មិនឃើញ!")

# --- ៦. ចាប់ផ្ដើមដំណើរការ Bot ---
if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        # បើសិនជា Error ត្រង់នេះ មានន័យថាអ្នកមិនទាន់បានដាក់ DISCORD_TOKEN ក្នុង Variables របស់ Railway ទេ
        print("❌ Error: រកមិនឃើញ DISCORD_TOKEN ក្នុង Environment Variables ទេ។")