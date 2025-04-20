import discord
from discord.ext import commands
from mcstatus import JavaServer

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

@bot.command()
async def status(ctx):
    try:
        server = JavaServer.lookup("mcmodsserver.ddns.net:2740")
        status = server.status()

        online = status.players.online
        max_players = status.players.max

        player_names = ", ".join(player.name for player in status.players.sample) if status.players.sample else "Keine Spieler online"

        embed = discord.Embed(title="🌍 Minecraft Server Status", color=0x00ff00)
        embed.add_field(name="🔌 IP", value="`mcmodsserver.ddns.net:2740`", inline=False)
        embed.add_field(name="👥 Spieler", value=f"`{online} / {max_players}`", inline=True)
        embed.add_field(name="🧑 Online-Spieler", value=player_names, inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        embed = discord.Embed(title="❌ Server nicht erreichbar", description=str(e), color=0xff0000)
        await ctx.send(embed=embed)

bot.run("DEIN_DISCORD_BOT_TOKEN")
