import discord
from discord.ext import commands
import asyncio
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()  # Lädt Umgebungsvariablen aus der .env-Datei
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
#wenn jemand den server betritt oder verlässt dann wird das ausgegeben
@bot.event
async def on_member_join(member):
    print(f"{member} ist dem Server beigetreten.")
    @bot.event
    async def on_member_remove(member):
        print(f"{member} hat den Server verlassen.")
        #wenn der bot gestartet wird dann wird das ausgegeben
        @bot.event
        async def on_ready():
            print(f"Bot ist bereit als {bot.user}.")



            
        
            

    
    
    

# Starte den Bot
print(f"Token gefunden: {TOKEN[:5]}**********")  # Zeigt nur einen Teil des Tokens für Sicherheit

bot.run(TOKEN)
