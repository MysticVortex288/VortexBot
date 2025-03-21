import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()

# Bot-Konfiguration
intents = discord.Intents.all()
intents.members = True
intents.message_content = True

class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        self.start_time = None

    async def setup_hook(self):
        await self.tree.sync()

bot = CustomBot()

# Event: Bot ist bereit
@bot.event
async def on_ready():
    bot.start_time = datetime.datetime.utcnow()
    print(f'{bot.user} ist online!')

@bot.command()
@commands.has_permissions(administrator=True)
async def online(ctx):
    uptime = datetime.datetime.utcnow() - bot.start_time
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    embed = discord.Embed(
        title="🟢 Bot Status",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Status",
        value="Online und bereit!",
        inline=False
    )
    
    embed.add_field(
        name="Latenz",
        value=f"🏓 {round(bot.latency * 1000)}ms",
        inline=True
    )
    
    embed.add_field(
        name="Uptime",
        value=f"⏰ {uptime.days}d {hours}h {minutes}m {seconds}s",
        inline=True
    )
    
    embed.add_field(
        name="Server",
        value=f"🌐 {len(bot.guilds)} Server",
        inline=True
    )
    
    embed.set_footer(text=f"Bot Version: 1.0 • Gestartet am {bot.start_time.strftime('%d.%m.%Y um %H:%M:%S')}")
    
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx, category: str = None):
    if category is None:
        embed = discord.Embed(
            title="🤖 Bot Hilfe",
            description="Hier sind die verfügbaren Kategorien:\n\n"
                        "• `!help moderation` - Moderations- und Statusbefehle\n"
                        "• `!help economy` - Wirtschaftsbefehle\n\n"
                        "Weitere Kategorien kommen bald!",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Benutze !help <kategorie> für mehr Details")
        await ctx.send(embed=embed)
        return
    
    if category.lower() == "moderation":
        embed = discord.Embed(
            title="🛡️ Moderations- und Statusbefehle",
            description="**Diese Befehle können nur von Administratoren verwendet werden!**\n\n"
                        "Hier sind alle verfügbaren Befehle:",
            color=discord.Color.green()
        )
        embed.add_field(
            name="!online",
            value="Zeigt detaillierte Statusinformationen des Bots",
            inline=False
        )
        embed.add_field(
            name="!kick @user [grund]",
            value="Kickt einen Benutzer vom Server",
            inline=False
        )
        embed.add_field(
            name="!ban @user [grund]",
            value="Bannt einen Benutzer vom Server",
            inline=False
        )
        embed.add_field(
            name="!timeout @user [dauer] [grund]",
            value="Timeout für einen Benutzer (Standard: 5 Minuten)",
            inline=False
        )
        embed.add_field(
            name="!untimeout @user",
            value="Entfernt den Timeout eines Benutzers",
            inline=False
        )
        embed.set_footer(text="⚠️ Diese Befehle erfordern Administrator-Rechte!")
        await ctx.send(embed=embed)
        return
    
    if category.lower() == "economy":
        embed = discord.Embed(
            title="💰 Wirtschaftsbefehle",
            description="**Hier sind alle verfügbaren Wirtschaftsbefehle:**",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="!daily",
            value="Erhalte täglich eine zufällige Menge Geld. Verfügbar ab 1 Uhr nachts.",
            inline=False
        )
        embed.add_field(
            name="!work",
            value="Verdiene Geld mit Arbeiten. Kann alle 4 Stunden benutzt werden.",
            inline=False
        )
        embed.add_field(
            name="!beg",
            value="Bettel um Geld. Geringe Belohnung, 15% Chance, nichts zu bekommen.",
            inline=False
        )
        embed.add_field(
            name="!pay @user [betrag]",
            value="Überweise Geld an andere Spieler.",
            inline=False
        )
        embed.add_field(
            name="!leaderboard",
            value="Zeigt die reichsten Spieler in einer Rangliste.",
            inline=False
        )
        embed.set_footer(text="Nutze diese Befehle, um Geld zu verdienen und mit anderen zu interagieren!")
        await ctx.send(embed=embed)
        return
    
    await ctx.send(f"❌ Die Kategorie `{category}` wurde nicht gefunden. Benutze `!help` für eine Liste aller Kategorien.")

# Wenn die Datei direkt ausgeführt wird
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
