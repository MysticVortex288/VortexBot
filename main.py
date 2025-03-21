import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timedelta
import os  # Für Umgebungsvariablen

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

# Datenbank für das Economy-System (Speicherung in einem Dictionary)
economy_data = {}

# Täglicher Bonus
@bot.command()
async def daily(ctx):
    user = ctx.author.id
    now = datetime.utcnow()
    
    if user in economy_data and "last_daily" in economy_data[user]:
        last_claim = economy_data[user]["last_daily"]
        if now - last_claim < timedelta(days=1):
            await ctx.send("❌ Du kannst dein tägliches Einkommen erst morgen wieder beanspruchen!")
            return
    
    amount = random.randint(100, 500)
    economy_data.setdefault(user, {"balance": 0})
    economy_data[user]["balance"] += amount
    economy_data[user]["last_daily"] = now
    
    embed = discord.Embed(
        title="💰 Täglicher Bonus",
        description=f"Du hast {amount} Coins erhalten! Komm morgen wieder für mehr!",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Benutze !balance, um dein Guthaben zu sehen.")
    await ctx.send(embed=embed)

# Arbeiten für Geld
@bot.command()
async def work(ctx):
    user = ctx.author.id
    now = datetime.utcnow()
    
    if user in economy_data and "last_work" in economy_data[user]:
        last_work = economy_data[user]["last_work"]
        if now - last_work < timedelta(hours=4):
            await ctx.send("❌ Du kannst nur alle 4 Stunden arbeiten!")
            return
    
    amount = random.randint(50, 300)
    jobs = ["Programmierer", "Bäcker", "Streamer", "Bauarbeiter", "Arzt"]
    job = random.choice(jobs)
    economy_data.setdefault(user, {"balance": 0})
    economy_data[user]["balance"] += amount
    economy_data[user]["last_work"] = now
    
    embed = discord.Embed(
        title="🔨 Arbeit",
        description=f"Du hast als **{job}** gearbeitet und {amount} Coins verdient!",
        color=discord.Color.green()
    )
    embed.set_footer(text="Benutze !balance, um dein Guthaben zu sehen.")
    await ctx.send(embed=embed)

# Betteln um Geld
@bot.command()
async def beg(ctx):
    user = ctx.author.id
    amount = random.choice([random.randint(10, 50), 0])
    
    if amount == 0:
        message = "Niemand wollte dir Geld geben. 😢"
    else:
        economy_data.setdefault(user, {"balance": 0})
        economy_data[user]["balance"] += amount
        message = f"Jemand hat dir {amount} Coins gegeben! 🎉"
    
    embed = discord.Embed(
        title="🙏 Betteln",
        description=message,
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# Geld überweisen
@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    sender = ctx.author.id
    receiver = member.id
    
    # Validierung des Betrags
    if amount <= 0:
        await ctx.send("❌ Der Betrag muss positiv sein!")
        return
    
    if sender not in economy_data or economy_data[sender]["balance"] < amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return
    
    economy_data[sender]["balance"] -= amount
    economy_data.setdefault(receiver, {"balance": 0})
    economy_data[receiver]["balance"] += amount
    
    embed = discord.Embed(
        title="💸 Geldüberweisung",
        description=f"Du hast {amount} Coins an {member.mention} überwiesen!",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed)

# Bestenliste
@bot.command()
async def leaderboard(ctx):
    sorted_users = sorted(economy_data.items(), key=lambda x: x[1]["balance"], reverse=True)
    
    embed = discord.Embed(
        title="🏆 Leaderboard",
        color=discord.Color.orange()
    )
    
    for i, (user_id, data) in enumerate(sorted_users[:10], start=1):
        user = await bot.fetch_user(user_id)
        embed.add_field(name=f"#{i} {user.name}", value=f"💰 {data['balance']} Coins", inline=False)
    
    await ctx.send(embed=embed)

# Guthaben anzeigen
@bot.command()
async def balance(ctx):
    user = ctx.author.id
    balance = economy_data.get(user, {}).get("balance", 0)
    
    embed = discord.Embed(
        title="💳 Kontostand",
        description=f"Du hast **{balance}** Coins!",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# Starte den Bot
if __name__ == "__main__":
    discord_token = os.getenv("DISCORD_TOKEN")
    
    if discord_token is None:
        raise ValueError("Das Discord-Token wurde nicht gefunden! Bitte überprüfe die Umgebungsvariablen.")
    
    bot.run(discord_token)
