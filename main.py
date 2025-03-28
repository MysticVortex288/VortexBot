import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Hole den Token aus der .env-Datei
TOKEN = os.getenv('TOKEN')

# Überprüfen, ob der Token korrekt geladen wurde
if TOKEN is None:
    print("Fehler: Der Token wurde nicht geladen!")
else:
    print(f"TOKEN: {TOKEN}")  # Zeigt den Token zur Überprüfung an, sollte aber im echten Einsatz entfernt werden.

# Prefix für die Befehle
PREFIX = '!'

# Erstelle die Intents für den Bot (Aktivierung der Privileged Intents)
intents = discord.Intents.default()
intents.members = True  # Aktiviert die Mitglieder-Intents
intents.message_content = True  # Aktiviert den Nachrichteninhalt-Intent

# Initialisiere den Bot mit dem Prefix und den Intents
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Timeout-Befehl für Prefix
@bot.command()
async def timeout(ctx, member: discord.Member, seconds: int):
    try:
        await member.timeout(discord.utils.utcnow() + discord.timedelta(seconds=seconds), reason="Timeout command")
        await ctx.send(f"{member.mention} wurde für {seconds} Sekunden getimed out.")
    except Exception as e:
        await ctx.send(f"Fehler: {e}")

# Online-Befehl für Prefix
@bot.command()
async def online(ctx):
    await ctx.send("✨ **Ich bin jetzt online!** ✨\n"
        "Bereit, dir zu helfen – was kann ich für dich tun? 🤔")

# Setup Invite-Befehl für Prefix
@bot.command()
async def setupinvite(ctx):
    # Hier wird der Invite-Link generiert
    invite_link = discord.utils.oauth_url(bot.user.id)
    await ctx.send(f"Hier ist der Invite-Link für diesen Bot: {invite_link}\nLade den Bot zu deinem Server ein! 🚀")

# Event, wenn der Bot bereit ist
@bot.event
async def on_ready():
    print(f"Bot ist bereit als {bot.user}.")
    print("Bot ist jetzt online und bereit, Befehle entgegenzunehmen! 🚀")

# Starte den Bot mit dem Token
bot.run(TOKEN)
