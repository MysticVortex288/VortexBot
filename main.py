import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import random
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
        self.economy = {}

    async def setup_hook(self):
        await self.tree.sync()

bot = CustomBot()

# Economy-Befehle
@bot.command(name="daily")
async def daily(ctx):
    user = ctx.author.id
    now = datetime.datetime.utcnow()
    last_claim = bot.economy.get(user, {}).get("daily", datetime.datetime.min)
    if (now - last_claim).total_seconds() < 86400:
        await ctx.send("❌ Du kannst dein tägliches Geld erst morgen wieder beanspruchen!")
        return
    amount = random.randint(100, 500)
    bot.economy.setdefault(user, {}).update({"balance": bot.economy.get(user, {}).get("balance", 0) + amount, "daily": now})
    await ctx.send(f"💰 Du hast {amount} Münzen erhalten!")

@bot.command(name="work")
async def work(ctx):
    user = ctx.author.id
    now = datetime.datetime.utcnow()
    last_work = bot.economy.get(user, {}).get("work", datetime.datetime.min)
    if (now - last_work).total_seconds() < 14400:
        await ctx.send("❌ Du kannst erst in 4 Stunden wieder arbeiten!")
        return
    amount = random.randint(50, 300)
    bot.economy.setdefault(user, {}).update({"balance": bot.economy.get(user, {}).get("balance", 0) + amount, "work": now})
    await ctx.send(f"💼 Du hast {amount} Münzen verdient!")

@bot.command(name="beg")
async def beg(ctx):
    user = ctx.author.id
    if random.random() < 0.15:
        await ctx.send("❌ Niemand wollte dir Geld geben!")
        return
    amount = random.randint(10, 100)
    bot.economy.setdefault(user, {}).update({"balance": bot.economy.get(user, {}).get("balance", 0) + amount})
    await ctx.send(f"🪙 Jemand war großzügig und gab dir {amount} Münzen!")

@bot.command(name="pay")
async def pay(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        await ctx.send("❌ Du kannst kein negatives oder null Münzen überweisen!")
        return
    user = ctx.author.id
    if bot.economy.get(user, {}).get("balance", 0) < amount:
        await ctx.send("❌ Du hast nicht genug Münzen!")
        return
    bot.economy[user]["balance"] -= amount
    bot.economy.setdefault(member.id, {}).update({"balance": bot.economy.get(member.id, {}).get("balance", 0) + amount})
    await ctx.send(f"✅ Du hast {amount} Münzen an {member.mention} überwiesen!")

@bot.command(name="leaderboard")
async def leaderboard(ctx):
    sorted_users = sorted(bot.economy.items(), key=lambda x: x[1].get("balance", 0), reverse=True)[:10]
    embed = discord.Embed(title="🏆 Leaderboard", color=discord.Color.gold())
    for i, (user_id, data) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(user_id)
        name = member.name if member else "Unbekannt"
        embed.add_field(name=f"#{i} {name}", value=f"💰 {data.get('balance', 0)} Münzen", inline=False)
    await ctx.send(embed=embed)

# Hilfe-Befehl aktualisieren
@bot.command()
async def help(ctx, category: str = None):
    if category is None:
        embed = discord.Embed(
            title="🤖 Bot Hilfe",
            description="Hier sind die verfügbaren Kategorien:\n\n"
                        "• `!help moderation` - Moderations- und Statusbefehle\n"
                        "• `!help economy` - Wirtschaftsbefehle\n",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Benutze !help <kategorie> für mehr Details")
        await ctx.send(embed=embed)
        return
    
    if category.lower() == "economy":
        embed = discord.Embed(
            title="💰 Economy-Befehle",
            description="Hier sind alle verfügbaren Wirtschafts-Befehle:",
            color=discord.Color.green()
        )
        embed.add_field(name="!daily", value="Erhalte täglich eine zufällige Menge Münzen", inline=False)
        embed.add_field(name="!work", value="Arbeite und verdiene Geld (alle 4 Stunden)", inline=False)
        embed.add_field(name="!beg", value="Bettle um etwas Geld (15% Chance, nichts zu bekommen)", inline=False)
        embed.add_field(name="!pay @user <betrag>", value="Überweise Münzen an einen anderen Spieler", inline=False)
        embed.add_field(name="!leaderboard", value="Zeigt die reichsten Spieler an", inline=False)
        await ctx.send(embed=embed)
        return
    
    await ctx.send(f"❌ Die Kategorie `{category}` wurde nicht gefunden. Benutze `!help` für eine Liste aller Kategorien.")

# Online-Befehl reparieren
@bot.command()
@commands.has_permissions(administrator=True)
async def online(ctx):
    uptime = datetime.datetime.utcnow() - bot.start_time
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    embed = discord.Embed(title="🟢 Bot Status", color=discord.Color.green())
    embed.add_field(name="Status", value="Online und bereit!", inline=False)
    embed.add_field(name="Latenz", value=f"🏓 {round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="Uptime", value=f"⏰ {uptime.days}d {hours}h {minutes}m {seconds}s", inline=True)
    embed.add_field(name="Server", value=f"🌐 {len(bot.guilds)} Server", inline=True)
    embed.set_footer(text=f"Bot Version: 1.0 • Gestartet am {bot.start_time.strftime('%d.%m.%Y um %H:%M:%S')}")
    await ctx.send(embed=embed)

if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
