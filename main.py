import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from datetime import timedelta

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Hole den Token aus der .env-Datei
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

# Timeout-Befehl für Minuten
@bot.tree.command(name="timeout", description="Set a timeout for a member")
async def timeout_slash(interaction: discord.Interaction, member: discord.Member, minutes: int):
    try:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)  # Richtige Zeitzone!
        await member.timeout(until, reason="Timeout command")
        await interaction.response.send_message(f"{member.mention} wurde für {minutes} Minuten getimed out.")
    except Exception as e:
        await interaction.response.send_message(f"Fehler: {e}")

# Untimeout-Befehl (Enttimeouten eines Spielers) für Slash
@bot.tree.command(name="untimeout", description="Remove the timeout from a member")
async def untimeout_slash(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout(None, reason="Untimeout command")
        await interaction.response.send_message(f"{member.mention} wurde enttimed out.")
    except Exception as e:
        await interaction.response.send_message(f"Fehler: {e}")

# Online-Befehl für Slash
@bot.tree.command(name="online", description="Check if the bot is online.")
async def online_slash(interaction: discord.Interaction):
    await interaction.response.send_message("✨ **Ich bin jetzt online!** ✨\n"
        "Bereit, dir zu helfen – was kann ich für dich tun? 🤔")

# Setup Invite-Befehl
@bot.command()
async def setupinvite(ctx):
    invite_link = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=8))
    await ctx.send(f"Hier ist der Invite-Link für diesen Bot: {invite_link}\nLade den Bot zu deinem Server ein! 🚀")

# Event, wenn der Bot bereit ist
@bot.event
async def on_ready():
    print(f"Bot ist bereit als {bot.user}.")
    print("Bot ist jetzt online und bereit, Befehle entgegenzunehmen! 🚀")
    try:
        await bot.tree.sync()  # Synchronisiert die Slash-Befehle
        print("Slash-Commands synchronisiert!")
    except Exception as e:
        print(f"Fehler bei der Synchronisation der Slash-Befehle: {e}")

# Starte den Bot mit dem Token
bot.run(TOKEN)
