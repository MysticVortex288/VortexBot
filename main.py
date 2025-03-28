import discord
from discord.ext import commands
from discord import app_commands
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

# Timeout-Befehl für Slash-Commands
@bot.tree.command(name="timeout", description="Time out a member for a specific duration.")
async def timeout_slash(interaction: discord.Interaction, member: discord.Member, seconds: int):
    try:
        await member.timeout(discord.utils.utcnow() + discord.timedelta(seconds=seconds), reason="Timeout command")
        await interaction.response.send_message(f"{member.mention} wurde für {seconds} Sekunden getimed out.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Fehler: {e}", ephemeral=True)

# Online-Befehl für Prefix
@bot.command()
async def online(ctx):
    await ctx.send("Ich bin online!")

# Online-Befehl für Slash-Commands
@bot.tree.command(name="online", description="Check if the bot is online.")
async def online_slash(interaction: discord.Interaction):
    await interaction.response.send_message("Ich bin online!", ephemeral=True)

# Event, wenn der Bot bereit ist
@bot.event
async def on_ready():
    print(f"Bot ist bereit als {bot.user}.")
    try:
        await bot.tree.sync()  # Synchronisiert die Slash-Befehle
        print("Slash-Commands synchronisiert!")
    except Exception as e:
        print(f"Fehler bei der Synchronisation der Slash-Commands: {e}")

# Starte den Bot mit dem Token
bot.run(TOKEN)
