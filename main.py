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
async def help(ctx, category: str = None):
    if category is None:
        # Hauptmenü
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
        # Moderations-Hilfe
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
        # Wirtschaft-Hilfe (Hier kannst du weitere Infos hinzufügen)
        embed = discord.Embed(
            title="💰 Wirtschaftsbefehle",
            description="Hier sind alle verfügbaren Befehle für das Wirtschaftssystem:",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="Platzhalter",
            value="Hier kommen deine Economy-Befehle hin!",
            inline=False
        )
        await ctx.send(embed=embed)
        return
    
    await ctx.send(f"❌ Die Kategorie `{category}` wurde nicht gefunden. Benutze `!help` für eine Liste aller Kategorien.")

# Wenn die Datei direkt ausgeführt wird
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
