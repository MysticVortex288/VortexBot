import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from datetime import timedelta

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()
TOKEN = os.getenv('TOKEN')

# Überprüfen, ob der Token korrekt geladen wurde
if TOKEN is None:
    print("Fehler: Der Token wurde nicht geladen!")

# Prefix für die Befehle
PREFIX = '!'

# Erstelle die Intents für den Bot
intents = discord.Intents.default()
intents.members = True  
intents.message_content = True  

# Initialisiere den Bot
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ===================== TIMEOUT & UNTIMEOUT =====================
@bot.command()
async def timeout(ctx, member: discord.Member, minutes: int):
    try:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason="Timeout command")
        await ctx.send(f"{member.mention} wurde für {minutes} Minuten getimed out.")
    except Exception as e:
        await ctx.send(f"Fehler: {e}")

@bot.command()
async def untimeout(ctx, member: discord.Member):
    try:
        await member.timeout(None, reason="Untimeout command")
        await ctx.send(f"{member.mention} wurde enttimed out.")
    except Exception as e:
        await ctx.send(f"Fehler: {e}")

# ===================== ONLINE CHECK =====================
@bot.command()
async def online(ctx):
    await ctx.send("✨ **Ich bin jetzt online!** ✨\nBereit, dir zu helfen – was kann ich für dich tun? 🤔")

# ===================== INVITE SYSTEM =====================
@bot.command()
async def setupinvite(ctx):
    invite_link = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=8))
    await ctx.send(f"Hier ist der Invite-Link für diesen Bot: {invite_link}\nLade den Bot zu deinem Server ein! 🚀")

@bot.event
async def on_member_join(member):
    if member.guild.system_channel:
        await member.guild.system_channel.send(f"🎉 {member.mention} ist dem Server beigetreten!")

@bot.event
async def on_member_remove(member):
    if member.guild.system_channel:
        await member.guild.system_channel.send(f"😢 {member.mention} hat den Server verlassen.")

@bot.command()
async def invite_tracker(ctx):
    await ctx.send(f"📩 **Invite-Tracker ist aktiv!**")

# ===================== TICKET SYSTEM =====================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton())

class TicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🎟️ Ticket erstellen", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")
        
        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await channel.set_permissions(guild.default_role, read_messages=False)

        await channel.send(
            f"{interaction.user.mention}, dein Ticket wurde erstellt! Ein Support-Mitarbeiter wird sich bald melden. ✅",
            view=CloseTicketView()
        )
        
        await interaction.response.send_message(f"Dein Ticket wurde erstellt: {channel.mention}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseTicketButton())

class CloseTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🔒 Ticket schließen", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        await channel.send("🔒 **Dieses Ticket wurde geschlossen.**", view=DeleteTicketView())
        await interaction.response.defer()

class DeleteTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeleteTicketButton())

class DeleteTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🗑️ Ticket löschen", style=discord.ButtonStyle.gray)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        await channel.send("🗑️ **Dieses Ticket wird in 5 Sekunden gelöscht...**")
        await interaction.response.defer()
        await discord.utils.sleep_until(discord.utils.utcnow().replace(second=discord.utils.utcnow().second + 5))
        await channel.delete()

@bot.command()
async def ticket(ctx):
    await ctx.send("🎟️ **Brauchst du Hilfe? Klicke auf den Button, um ein Ticket zu erstellen!**", view=TicketView())

# ===================== BOT START =====================
@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")
    try:
        await bot.tree.sync()
        print("✅ Slash-Commands synchronisiert!")
    except Exception as e:
        print(f"❌ Fehler bei der Synchronisation der Slash-Befehle: {e}")

bot.run(TOKEN)
