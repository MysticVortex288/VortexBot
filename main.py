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


@bot.command(name="hilfe")  # Neuer Name, um Konflikte zu vermeiden
async def hilfe(ctx):
    embed = discord.Embed(title="Befehlsliste", description="Hier sind alle verfügbaren Befehle:", color=discord.Color.blue())
    embed.add_field(name="`!timeout [@User] [Minuten] [Grund]`", value="Timeoutet einen User für eine bestimmte Zeit.", inline=False)
    embed.add_field(name="`/timeout [@User] [Minuten] [Grund]`", value="Slash-Command-Version von `!timeout`.", inline=False)
    embed.add_field(name="`!hilfe`", value="Zeigt diese Hilfeseite an.", inline=False)
    await ctx.send(embed=embed)
    #jemanden timeout geben
    @bot.prefix_command(name="timeout")
    async def timeout(ctx, member: discord.Member, minutes: int, *, reason: Optional[str] = "Kein Grund angegeben."):
        if ctx.author.guild_permissions.administrator:
            await member.add_roles(discord.utils.get(ctx.guild.roles, name="Timeout"))
            await ctx.send(f"{member.mention} wurde für {minutes} Minuten getimeoutet. Grund: {reason}")
            await asyncio.sleep(minutes * 60)
            await member.remove_roles(discord.utils.get(ctx.guild.roles, name="Timeout"))
            await ctx.send(f"{member.mention} ist wieder enttimeoutet.")
            
        
            

    
    
    

# Starte den Bot
print(f"Token gefunden: {TOKEN[:5]}**********")  # Zeigt nur einen Teil des Tokens für Sicherheit

bot.run(TOKEN)
