import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

TOKEN = os.getenv('TOKEN')
PREFIX = '!'

intents = discord.Intents.default()
intents.members = True  # Aktiviert die Mitglieder-Intents

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Timeout-Befehl für Prefix
@bot.command()
async def timeout(ctx, member: discord.Member, seconds: int):
    until = datetime.utcnow() + timedelta(seconds=seconds)
    await member.timeout(until, reason="Timeout command")
    await ctx.send(f"{member.mention} wurde für {seconds} Sekunden getimed out.")

# Timeout-Befehl für Slash-Commands
@bot.tree.command(name="timeout", description="Time out a member for a specific duration.")
async def timeout_slash(interaction: discord.Interaction, member: discord.Member, seconds: int):
    until = datetime.utcnow() + timedelta(seconds=seconds)
    await member.timeout(until, reason="Timeout command")
    await interaction.response.send_message(f"{member.mention} wurde für {seconds} Sekunden getimed out.", ephemeral=True)

# Online-Befehl für Prefix
@bot.command()
async def online(ctx):
    await ctx.send("Ich bin online!")

# Online-Befehl für Slash-Commands
@bot.tree.command(name="online", description="Check if the bot is online.")
async def online_slash(interaction: discord.Interaction):
    await interaction.response.send_message("Ich bin online!", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot ist bereit als {bot.user}.")
    try:
        await bot.tree.sync()  # Synchronisiert die Slash-Befehle
        print("Slash-Commands synchronisiert!")
    except Exception as e:
        print(f"Fehler bei der Synchronisation der Slash-Commands: {e}")

# Starte den Bot (MUSS am Ende des Skripts stehen!)
bot.run(TOKEN)
