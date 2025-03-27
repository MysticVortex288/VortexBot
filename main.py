import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()  # Lädt Umgebungsvariablen aus der .env-Datei
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True  # Aktiviert das Member-Tracking (wichtig für on_member_join/on_member_remove)

bot = commands.Bot(command_prefix="!", intents=intents)

# Wird ausgelöst, wenn der Bot erfolgreich gestartet ist
@bot.event
async def on_ready():
    print(f"Bot ist bereit als {bot.user}")

# Wird ausgelöst, wenn jemand den Server betritt
@bot.event
async def on_member_join(member):
    print(f"{member} ist dem Server beigetreten.")

# Wird ausgelöst, wenn jemand den Server verlässt
@bot.event
async def on_member_remove(member):
    print(f"{member} hat den Server verlassen.")

# Starte den Bot
print(f"Token gefunden: {TOKEN[:5]}**********")  # Zeigt nur einen Teil des Tokens für Sicherheit
bot.run(TOKEN)
