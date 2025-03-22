import os
import random
import discord
import sqlite3
import asyncio
import datetime
from typing import Optional, List, Dict
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from flask import Flask
from threading import Thread

# Flask App für Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Datenbank Setup
conn = sqlite3.connect('casino.db')
cursor = conn.cursor()

# Erstelle Tabellen
cursor.execute('''
CREATE TABLE IF NOT EXISTS economy (
    user_id INTEGER PRIMARY KEY,
    coins INTEGER DEFAULT 0
)
''')
conn.commit()

class CustomBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents, help_command=None)
        self.start_time = None
        self.db_path = "economy.db"
        self.setup_database()
        self.horse_races: Dict[int, HorseRace] = {}  # Speichert aktive Rennen pro Channel

    def setup_database(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Erstelle Tabelle für Benutzer-Konten
            c.execute('''CREATE TABLE IF NOT EXISTS economy
                        (user_id INTEGER PRIMARY KEY,
                         coins INTEGER DEFAULT 0,
                         daily_last_used TEXT,
                         work_last_used TEXT,
                         beg_last_used TEXT,
                         rob_last_used TEXT)''')
            # Erstelle Tabelle für Pferderennen-Wetten
            c.execute('''CREATE TABLE IF NOT EXISTS horse_bets
                        (race_id TEXT,
                         user_id INTEGER,
                         horse_id TEXT,
                         amount INTEGER,
                         PRIMARY KEY (race_id, user_id))''')
            # Erstelle Tabelle für Cooldowns
            c.execute('''CREATE TABLE IF NOT EXISTS cooldowns
                        (user_id INTEGER,
                         command TEXT,
                         last_used TEXT,
                         PRIMARY KEY (user_id, command))''')
            conn.commit()

    async def setup_hook(self):
        await self.tree.sync()

bot = CustomBot()

# Economy Hilfsfunktionen
def get_user_account(user_id: int) -> tuple:
    with sqlite3.connect(bot.db_path) as conn:
        c = conn.cursor()
        c.execute('INSERT OR IGNORE INTO economy (user_id) VALUES (?)', (user_id,))
        c.execute('SELECT * FROM economy WHERE user_id = ?', (user_id,))
        return c.fetchone()

def update_coins(user_id: int, amount: int):
    with sqlite3.connect(bot.db_path) as conn:
        c = conn.cursor()
        c.execute('UPDATE economy SET coins = coins + ? WHERE user_id = ?', (amount, user_id))
        conn.commit()

def get_coins(user_id: int) -> int:
    with sqlite3.connect(bot.db_path) as conn:
        c = conn.cursor()
        c.execute('SELECT coins FROM economy WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result is None:
            # Erstelle neuen Account mit 500 Startcoins
            c.execute('INSERT INTO economy (user_id, coins) VALUES (?, ?)', (user_id, 500))
            conn.commit()
            return 500
        return result[0]

def get_last_used(user_id: int, command: str) -> Optional[datetime.datetime]:
    with sqlite3.connect(bot.db_path) as conn:
        c = conn.cursor()
        c.execute('SELECT last_used FROM cooldowns WHERE user_id = ? AND command = ?', (user_id, command))
        result = c.fetchone()
        if result and result[0]:
            return datetime.datetime.fromisoformat(result[0])
        return None

def update_last_used(user_id: int, command: str):
    with sqlite3.connect(bot.db_path) as conn:
        c = conn.cursor()
        now = datetime.datetime.now().isoformat()
        c.execute('''INSERT OR REPLACE INTO cooldowns (user_id, command, last_used)
                    VALUES (?, ?, ?)''', (user_id, command, now))
        conn.commit()

def check_cooldown(user_id: int, command: str, cooldown_hours: int = 1) -> tuple[bool, int, int]:
    last_used = get_last_used(user_id, command)
    if not last_used:
        return True, 0, 0
    
    now = datetime.datetime.now()
    time_diff = now - last_used
    cooldown = datetime.timedelta(hours=cooldown_hours)
    
    if time_diff < cooldown:
        remaining = cooldown - time_diff
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        return False, hours, minutes
    
    return True, 0, 0

# Economy Commands
@bot.command()
async def daily(ctx):
    # Prüfe ob der Befehl heute schon benutzt wurde
    can_use, hours, minutes = check_cooldown(ctx.author.id, "daily", 24)
    if not can_use:
        await ctx.send(f"❌ Du kannst den Daily-Bonus erst wieder in {hours}h {minutes}m abholen!")
        return

    # Gib dem Benutzer Coins
    coins = random.randint(100, 1000)
    update_coins(ctx.author.id, coins)
    update_last_used(ctx.author.id, "daily")
    await ctx.send(f"💰 Du hast deinen täglichen Bonus von {coins} Coins erhalten!")

@bot.command()
async def work(ctx):
    # Prüfe 1-Stunden-Cooldown
    can_use, hours, minutes = check_cooldown(ctx.author.id, "work", 1)
    if not can_use:
        await ctx.send(f"❌ Du musst noch {hours}h {minutes}m warten, bevor du wieder arbeiten kannst!")
        return

    # Gib dem Benutzer Coins
    coins = random.randint(50, 200)
    update_coins(ctx.author.id, coins)
    update_last_used(ctx.author.id, "work")
    await ctx.send(f"💼 Du hast {coins} Coins durch Arbeit verdient!")

@bot.command()
async def beg(ctx):
    # Prüfe 1-Stunden-Cooldown
    can_use, hours, minutes = check_cooldown(ctx.author.id, "beg", 1)
    if not can_use:
        await ctx.send(f"❌ Du musst noch {hours}h {minutes}m warten, bevor du wieder betteln kannst!")
        return

    # 50% Chance auf Erfolg
    if random.random() < 0.5:
        coins = random.randint(1, 100)
        update_coins(ctx.author.id, coins)
        update_last_used(ctx.author.id, "beg")
        await ctx.send(f"🙏 Jemand hat Mitleid mit dir und gibt dir {coins} Coins!")
    else:
        update_last_used(ctx.author.id, "beg")
        await ctx.send("😔 Niemand wollte dir Coins geben...")

@bot.command()
async def rob(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("❌ Du kannst dich nicht selbst ausrauben!")
        return

    # Prüfe 1-Stunden-Cooldown
    can_use, hours, minutes = check_cooldown(ctx.author.id, "rob", 1)
    if not can_use:
        await ctx.send(f"❌ Du musst noch {hours}h {minutes}m warten, bevor du wieder jemanden ausrauben kannst!")
        return

    victim_coins = get_coins(member.id)
    if victim_coins < 50:
        await ctx.send("❌ Diese Person hat zu wenig Coins zum Ausrauben!")
        return

    # 15% Chance auf Erfolg
    if random.random() < 0.15:
        stolen = random.randint(1, min(victim_coins, 1000))
        update_coins(member.id, -stolen)
        update_coins(ctx.author.id, stolen)
        update_last_used(ctx.author.id, "rob")
        await ctx.send(f"💰 Du hast {stolen} Coins von {member.name} gestohlen!")
    else:
        fine = random.randint(50, 200)
        update_coins(ctx.author.id, -fine)
        update_last_used(ctx.author.id, "rob")
        await ctx.send(f"👮 Du wurdest erwischt und musst {fine} Coins Strafe zahlen!")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        await ctx.send("❌ Du kannst dir nicht selbst Coins überweisen!")
        return
    
    if amount <= 0:
        await ctx.send("❌ Der Betrag muss positiv sein!")
        return
    
    sender_coins = get_coins(ctx.author.id)
    if sender_coins < amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return
    
    update_coins(ctx.author.id, -amount)
    update_coins(member.id, amount)
    
    embed = discord.Embed(
        title="💸 Überweisung",
        description=f"{ctx.author.mention} hat {member.mention} **{amount:,}** Coins überwiesen!",
        color=discord.Color.green()
    )
    embed.set_footer(text="Vielen Dank für die Transaktion! 🙏")
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    with sqlite3.connect(bot.db_path) as conn:
        c = conn.cursor()
        c.execute('SELECT user_id, coins FROM economy ORDER BY coins DESC LIMIT 10')
        top_users = c.fetchall()
    
    if not top_users:
        await ctx.send("❌ Keine Nutzer gefunden!")
        return
    
    embed = discord.Embed(
        title="🏆 Reichste Nutzer",
        description="Die Top 10 reichsten Nutzer des Servers:",
        color=discord.Color.gold()
    )
    
    for i, (user_id, coins) in enumerate(top_users, 1):
        member = ctx.guild.get_member(user_id)
        name = member.name if member else f"Unbekannt ({user_id})"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "👑")
        embed.add_field(
            name=f"{medal} Platz {i}",
            value=f"{name}: **{coins:,}** Coins",
            inline=False
        )
    
    embed.set_footer(text="Werde auch du reich mit unseren Casino-Spielen! 🎰")
    await ctx.send(embed=embed)

# Event: Bot ist bereit
@bot.event
async def on_ready():
    bot.start_time = datetime.datetime.utcnow()
    print(f'{bot.user} ist online!')

# Funktion für Moderations-Embed
def create_mod_embed(action, user, moderator, reason, duration=None):
    embed = discord.Embed(
        title=f"🛠️ Moderation: {action}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now()
    )
    embed.add_field(name="Betroffener User", value=f"{user.mention} ({user.id})", inline=False)
    embed.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.id})", inline=False)
    if duration:
        embed.add_field(name="Dauer", value=duration, inline=False)
    embed.add_field(name="Grund", value=reason or "Kein Grund angegeben", inline=False)
    return embed

# Kick Command (Prefix und Slash)
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_prefix(ctx, member: discord.Member, *, reason=None):
    await kick_user(ctx, member, reason)

@bot.tree.command(name="kick", description="Kickt einen User vom Server")
@app_commands.describe(member="Der User, der gekickt werden soll", reason="Grund für den Kick")
@app_commands.checks.has_permissions(kick_members=True)
async def kick_slash(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await kick_user(interaction, member, reason)

async def kick_user(ctx, member: discord.Member, reason=None):
    if isinstance(ctx, discord.Interaction):
        author = ctx.user
        await ctx.response.defer()
    else:
        author = ctx.author

    # Erstelle Embeds
    mod_embed = create_mod_embed("Kick", member, author, reason)
    
    # DM an den gekickten User
    try:
        user_embed = discord.Embed(
            title="🚫 Du wurdest gekickt!",
            description=f"Du wurdest von **{ctx.guild.name}** gekickt.",
            color=discord.Color.red()
        )
        user_embed.add_field(name="Grund", value=reason or "Kein Grund angegeben")
        await member.send(embed=user_embed)
    except:
        pass  # User hat DMs deaktiviert

    # Kicke den User
    await member.kick(reason=reason)

    # Sende Bestätigung
    if isinstance(ctx, discord.Interaction):
        await ctx.followup.send(embed=mod_embed)
    else:
        await ctx.send(embed=mod_embed)

    # DM an den Moderator
    mod_dm_embed = discord.Embed(
        title="🛠️ Moderation ausgeführt",
        description=f"Deine Moderationsaktion wurde ausgeführt.",
        color=discord.Color.green()
    )
    mod_dm_embed.add_field(name="Aktion", value="Kick", inline=True)
    mod_dm_embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
    try:
        await author.send(embed=mod_dm_embed)
    except:
        pass  # Moderator hat DMs deaktiviert

# Ban Command (Prefix und Slash)
@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_prefix(ctx, member: discord.Member, *, reason=None):
    await ban_user(ctx, member, reason)

@bot.tree.command(name="ban", description="Bannt einen User vom Server")
@app_commands.describe(member="Der User, der gebannt werden soll", reason="Grund für den Bann")
@app_commands.checks.has_permissions(ban_members=True)
async def ban_slash(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await ban_user(interaction, member, reason)

async def ban_user(ctx, member: discord.Member, reason=None):
    if isinstance(ctx, discord.Interaction):
        author = ctx.user
        await ctx.response.defer()
    else:
        author = ctx.author

    # Erstelle Embeds
    mod_embed = create_mod_embed("Bann", member, author, reason)
    
    # DM an den gebannten User
    try:
        user_embed = discord.Embed(
            title="🚫 Du wurdest gebannt!",
            description=f"Du wurdest von **{ctx.guild.name}** gebannt.",
            color=discord.Color.red()
        )
        user_embed.add_field(name="Grund", value=reason or "Kein Grund angegeben")
        await member.send(embed=user_embed)
    except:
        pass

    # Banne den User
    await member.ban(reason=reason)

    # Sende Bestätigung
    if isinstance(ctx, discord.Interaction):
        await ctx.followup.send(embed=mod_embed)
    else:
        await ctx.send(embed=mod_embed)

    # DM an den Moderator
    mod_dm_embed = discord.Embed(
        title="🛠️ Moderation ausgeführt",
        description=f"Deine Moderationsaktion wurde ausgeführt.",
        color=discord.Color.green()
    )
    mod_dm_embed.add_field(name="Aktion", value="Bann", inline=True)
    mod_dm_embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
    try:
        await author.send(embed=mod_dm_embed)
    except:
        pass

# Timeout Command (Prefix und Slash)
@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_prefix(ctx, member: discord.Member, minutes: int, *, reason=None):
    await timeout_user(ctx, member, minutes, reason)

@bot.tree.command(name="timeout", description="Versetzt einen User in einen Timeout")
@app_commands.describe(
    member="Der User, der in Timeout gesetzt werden soll",
    minutes="Dauer des Timeouts in Minuten",
    reason="Grund für den Timeout"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout_slash(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = None):
    await timeout_user(interaction, member, minutes, reason)

async def timeout_user(ctx, member: discord.Member, minutes: int, reason=None):
    if isinstance(ctx, discord.Interaction):
        author = ctx.user
        await ctx.response.defer()
    else:
        author = ctx.author

    # Berechne Timeout-Dauer
    duration = datetime.timedelta(minutes=minutes)
    
    # Erstelle Embeds
    mod_embed = create_mod_embed("Timeout", member, author, reason, f"{minutes} Minuten")
    
    # DM an den User im Timeout
    try:
        user_embed = discord.Embed(
            title="⏰ Du wurdest in Timeout versetzt!",
            description=f"Du wurdest auf **{ctx.guild.name}** in Timeout versetzt.",
            color=discord.Color.orange()
        )
        user_embed.add_field(name="Dauer", value=f"{minutes} Minuten", inline=True)
        user_embed.add_field(name="Grund", value=reason or "Kein Grund angegeben", inline=True)
        await member.send(embed=user_embed)
    except:
        pass

    # Timeout den User
    await member.timeout(duration, reason=reason)

    # Sende Bestätigung
    if isinstance(ctx, discord.Interaction):
        await ctx.followup.send(embed=mod_embed)
    else:
        await ctx.send(embed=mod_embed)

    # DM an den Moderator
    mod_dm_embed = discord.Embed(
        title="🛠️ Moderation ausgeführt",
        description=f"Deine Moderationsaktion wurde ausgeführt.",
        color=discord.Color.green()
    )
    mod_dm_embed.add_field(name="Aktion", value="Timeout", inline=True)
    mod_dm_embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
    mod_dm_embed.add_field(name="Dauer", value=f"{minutes} Minuten", inline=True)
    try:
        await author.send(embed=mod_dm_embed)
    except:
        pass

# Untimeout Command (Prefix und Slash)
@bot.command(name="untimeout")
@commands.has_permissions(moderate_members=True)
async def untimeout_prefix(ctx, member: discord.Member, *, reason=None):
    await untimeout_user(ctx, member, reason)

@bot.tree.command(name="untimeout", description="Hebt den Timeout eines Users auf")
@app_commands.describe(
    member="Der User, dessen Timeout aufgehoben werden soll",
    reason="Grund für die Aufhebung"
)
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout_slash(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    await untimeout_user(interaction, member, reason)

async def untimeout_user(ctx, member: discord.Member, reason=None):
    if isinstance(ctx, discord.Interaction):
        author = ctx.user
        await ctx.response.defer()
    else:
        author = ctx.author

    # Erstelle Embeds
    mod_embed = create_mod_embed("Timeout aufgehoben", member, author, reason)
    
    # DM an den User
    try:
        user_embed = discord.Embed(
            title="⏰ Dein Timeout wurde aufgehoben!",
            description=f"Dein Timeout auf **{ctx.guild.name}** wurde vorzeitig aufgehoben.",
            color=discord.Color.green()
        )
        user_embed.add_field(name="Grund", value=reason or "Kein Grund angegeben")
        await member.send(embed=user_embed)
    except:
        pass

    # Hebe Timeout auf
    await member.timeout(None, reason=reason)

    # Sende Bestätigung
    if isinstance(ctx, discord.Interaction):
        await ctx.followup.send(embed=mod_embed)
    else:
        await ctx.send(embed=mod_embed)

    # DM an den Moderator
    mod_dm_embed = discord.Embed(
        title="🛠️ Moderation ausgeführt",
        description=f"Deine Moderationsaktion wurde ausgeführt.",
        color=discord.Color.green()
    )
    mod_dm_embed.add_field(name="Aktion", value="Timeout aufgehoben", inline=True)
    mod_dm_embed.add_field(name="User", value=f"{member} ({member.id})", inline=True)
    try:
        await author.send(embed=mod_dm_embed)
    except:
        pass

@bot.command()
@commands.has_permissions(administrator=True)
async def online(ctx):
    uptime = datetime.datetime.utcnow() - bot.start_time
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    seconds = uptime.seconds % 60

    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Status",
        value="Online und bereit!",
        inline=False
    )
    
    embed.add_field(
        name="Latenz",
        value=f" {round(bot.latency * 1000)}ms",
        inline=True
    )
    
    embed.add_field(
        name="Uptime",
        value=f" {uptime.days}d {hours}h {minutes}m {seconds}s",
        inline=True
    )
    
    embed.add_field(
        name="Server",
        value=f" {len(bot.guilds)} Server",
        inline=True
    )
    
    embed.set_footer(text=f"Bot Version: 1.0 • Gestartet am {bot.start_time.strftime('%d.%m.%Y um %H:%M:%S')}")
    
    await ctx.send(embed=embed)

@online.error
async def online_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(" Du brauchst Administrator-Rechte um diesen Befehl zu nutzen!")

@bot.command()
async def help(ctx, category: str = None):
    if category is None:
        # Hauptmenü
        embed = discord.Embed(
            title="🤖 Bot Hilfe",
            description="Hier sind die verfügbaren Kategorien:\n\n"
                      "• `!help moderation` - Moderations- und Statusbefehle\n"
                      "• `!help economy` - Wirtschaftssystem und Befehle\n"
                      "• `!help casino` - Casino-Spiele und Glücksspiel\n\n"
                      "**Weitere Kategorien kommen bald!**",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Benutze !help <kategorie> für mehr Details")
        await ctx.send(embed=embed)
        return
    
    if category.lower() == "moderation":
        # Moderations-Hilfe
        embed = discord.Embed(
            title="🛠️ Moderations- und Statusbefehle",
            description="**Diese Befehle können nur von Administratoren verwendet werden!**\n\n"
                       "**Hier sind alle verfügbaren Befehle:**",
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
        embed.set_footer(text=" Diese Befehle erfordern Administrator-Rechte!")
        await ctx.send(embed=embed)
        return
    
    if category.lower() == "economy":
        # Economy-Hilfe
        embed = discord.Embed(
            title="💰 Wirtschaftssystem",
            description="Hier sind alle verfügbaren Economy-Befehle:",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="!daily",
            value="Erhalte täglich zwischen 100-1000 Coins\n Cooldown: 24 Stunden (Reset um 1 Uhr)",
            inline=False
        )
        embed.add_field(
            name="!work",
            value="Arbeite für 50-200 Coins\n Cooldown: 1 Stunde",
            inline=False
        )
        embed.add_field(
            name="!beg",
            value="Bettle um bis zu 100 Coins (50% Chance auf Erfolg!)\n Cooldown: 1 Stunde",
            inline=False
        )
        embed.add_field(
            name="!pay @user <betrag>",
            value="Überweise einem anderen Nutzer Coins",
            inline=False
        )
        embed.add_field(
            name="!rob @user",
            value="Versuche einen anderen Nutzer auszurauben (15% Erfolgschance)\n Cooldown: 1 Stunde",
            inline=False
        )
        embed.add_field(
            name="!leaderboard",
            value="Zeigt die reichsten Nutzer des Servers",
            inline=False
        )
        embed.set_footer(text="Benutze die Befehle um Coins zu verdienen und auszugeben!")
        await ctx.send(embed=embed)
        return
    
    if category.lower() == "casino":
        # Casino-Hilfe
        embed = discord.Embed(
            title="🎲 Casino & Glücksspiel",
            description="Hier sind alle verfügbaren Casino-Spiele:",
            color=discord.Color.purple()
        )
        
        games = [
            ("", "!blackjack <einsatz>\nSpiele Blackjack gegen den Dealer! Versuche 21 zu erreichen."),
            ("", "!slots <einsatz>\nDrehe am einarmigen Banditen und gewinne bis zu 10x deinen Einsatz!"),
            ("", "!roulette <einsatz> <farbe>\nSetze auf Rot oder Schwarz und gewinne das Doppelte!"),
            ("", "!tower <einsatz>\nKlettere den Turm hoch und erhöhe deinen Multiplikator - aber fall nicht runter!"),
            ("", "!dice <einsatz>\nWürfle gegen den Bot - höhere Zahl gewinnt!"),
            ("", "!coinflip <einsatz> <kopf/zahl>\nWette auf Kopf oder Zahl!"),
            ("", "!scratch <einsatz>\nKratze drei gleiche Symbole für einen Gewinn!"),
            ("", "!yahtzee <einsatz>\nSpiele Würfelpoker und gewinne mit der besten Hand!"),
            ("", "!wheel <einsatz>\nDrehe am Glücksrad für verschiedene Multiplikatoren!"),
            ("", "!horserace <einsatz> <pferd>\nWette auf dein Lieblingspferd!")
        ]
        
        for name, description in games:
            embed.add_field(
                name=name,
                value=description,
                inline=False
            )
        
        embed.set_footer(text=" Spiele verantwortungsvoll! Setze nie mehr als du verlieren kannst!")
        await ctx.send(embed=embed)
        return
    
    await ctx.send(f" Die Kategorie `{category}` wurde nicht gefunden. Benutze `!help` für eine Liste aller Kategorien.")

class Card:
    def __init__(self, suit: str, value: str):
        self.suit = suit
        self.value = value
        
    def __str__(self):
        suit_emoji = {
            "♠": "♠️",
            "♣": "♣️",
            "♥": "♥️",
            "♦": "♦️"
        }
        return f"{self.value}{suit_emoji[self.suit]}"

class Deck:
    def __init__(self):
        self.cards = []
        suits = ["♠", "♣", "♥", "♦"]
        values = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        for suit in suits:
            for value in values:
                self.cards.append(Card(suit, value))
        random.shuffle(self.cards)
    
    def draw(self) -> Card:
        return self.cards.pop()

class BlackjackGame:
    def __init__(self, player_id: int, bet: int):
        self.deck = Deck()
        self.player_id = player_id
        self.bet = bet
        self.player_hand = []
        self.dealer_hand = []
        self.game_over = False
        self.player_stood = False
        
        # Initial cards
        self.player_hand.extend([self.deck.draw(), self.deck.draw()])
        self.dealer_hand.extend([self.deck.draw(), self.deck.draw()])
    
    def get_hand_value(self, hand: List[Card]) -> int:
        value = 0
        aces = 0
        
        for card in hand:
            if card.value in ["J", "Q", "K"]:
                value += 10
            elif card.value == "A":
                aces += 1
            else:
                value += int(card.value)
        
        for _ in range(aces):
            if value + 11 <= 21:
                value += 11
            else:
                value += 1
        
        return value
    
    def player_hit(self) -> Card:
        card = self.deck.draw()
        self.player_hand.append(card)
        if self.get_hand_value(self.player_hand) > 21:
            self.game_over = True
        return card
    
    def dealer_play(self) -> List[Card]:
        new_cards = []
        while self.get_hand_value(self.dealer_hand) < 17:
            card = self.deck.draw()
            self.dealer_hand.append(card)
            new_cards.append(card)
        self.game_over = True
        return new_cards
    
    def get_result(self) -> tuple[str, float]:
        player_value = self.get_hand_value(self.player_hand)
        dealer_value = self.get_hand_value(self.dealer_hand)
        
        if player_value > 21:
            return "BUST", 0
        elif dealer_value > 21:
            return "WIN", 2.0
        elif player_value > dealer_value:
            return "WIN", 2.0
        elif player_value < dealer_value:
            return "LOSE", 0
        else:
            return "PUSH", 1.0

class BlackjackView(View):
    def __init__(self, game: BlackjackGame, ctx):
        super().__init__(timeout=30)
        self.game = game
        self.ctx = ctx
        self.message = None
    
    async def update_message(self):
        embed = discord.Embed(
            title="🎲 Blackjack",
            color=discord.Color.gold()
        )
        
        # Zeige Dealer-Karten
        dealer_cards = " ".join(str(card) for card in self.game.dealer_hand)
        dealer_value = self.game.get_hand_value(self.game.dealer_hand)
        if not self.game.game_over and not self.game.player_stood:
            # Verstecke zweite Dealer-Karte
            dealer_cards = f"{self.game.dealer_hand[0]} 🂠"
            dealer_value = "?"
        embed.add_field(
            name="🎭 Dealer",
            value=f"Karten: {dealer_cards}\nWert: {dealer_value}",
            inline=False
        )
        
        # Zeige Spieler-Karten
        player_cards = " ".join(str(card) for card in self.game.player_hand)
        player_value = self.game.get_hand_value(self.game.player_hand)
        embed.add_field(
            name="👤 Deine Hand",
            value=f"Karten: {player_cards}\nWert: {player_value}",
            inline=False
        )
        
        if self.game.game_over:
            result, multiplier = self.game.get_result()
            winnings = int(self.game.bet * multiplier)
            
            if result == "WIN":
                embed.add_field(
                    name="🎉 Gewonnen!",
                    value=f"Du gewinnst **{winnings}** Coins!",
                    inline=False
                )
                update_coins(self.game.player_id, winnings)
            elif result == "LOSE":
                embed.add_field(
                    name="😢 Verloren!",
                    value=f"Du verlierst deinen Einsatz von **{self.game.bet}** Coins!",
                    inline=False
                )
            elif result == "PUSH":
                embed.add_field(
                    name="🤝 Unentschieden!",
                    value=f"Du erhältst deinen Einsatz von **{self.game.bet}** Coins zurück!",
                    inline=False
                )
                update_coins(self.game.player_id, self.game.bet)
            elif result == "BUST":
                embed.add_field(
                    name="💥 Bust!",
                    value=f"Über 21! Du verlierst deinen Einsatz von **{self.game.bet}** Coins!",
                    inline=False
                )
            
            self.clear_items()  # Entferne Buttons
        
        if self.message:
            await self.message.edit(embed=embed, view=self)
        else:
            self.message = await self.ctx.send(embed=embed, view=self)

    @discord.ui.button(label="Hit 🎯", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.game.player_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        self.game.player_hit()
        await interaction.response.defer()
        await self.update_message()

    @discord.ui.button(label="Stand 🛑", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.game.player_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        self.game.player_stood = True
        self.game.dealer_play()
        await interaction.response.defer()
        await self.update_message()

    async def on_timeout(self):
        if not self.game.game_over:
            self.game.player_stood = True
            self.game.dealer_play()
            await self.update_message()

@bot.command()
async def blackjack(ctx, bet: int = None):
    if not bet:
        embed = discord.Embed(
            title="🎲 Blackjack",
            description="Spiele Blackjack gegen den Dealer!\n\n"
                      "**Regeln:**\n"
                      "• Versuche näher an 21 zu kommen als der Dealer\n"
                      "• Ass = 1 oder 11\n"
                      "• Bildkarten = 10\n"
                      "• Dealer muss bei 16 ziehen und bei 17 stehen\n\n"
                      "**Gewinne:**\n"
                      "• Gewinn = 2x Einsatz\n"
                      "• Unentschieden = Einsatz zurück\n\n"
                      "**Verwendung:**\n"
                      "`!blackjack <einsatz>`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet < 50:
        await ctx.send("❌ Der Minimaleinsatz ist 50 Coins!")
        return

    user_coins = get_coins(ctx.author.id)
    if user_coins < bet:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    # Ziehe Einsatz ab
    update_coins(ctx.author.id, -bet)

    # Starte Spiel
    game = BlackjackGame(ctx.author.id, bet)
    view = BlackjackView(game, ctx)
    await view.update_message()

class WheelGame:
    def __init__(self):
        self.segments = [
            ("💎 5.0x", 5.0, 0.05),   # 5% Chance
            ("🌟 3.0x", 3.0, 0.10),   # 10% Chance
            ("💰 2.0x", 2.0, 0.15),   # 15% Chance
            ("✨ 1.5x", 1.5, 0.20),   # 20% Chance
            ("💫 1.2x", 1.2, 0.25),   # 25% Chance
            ("💀 0.0x", 0.0, 0.25)    # 25% Chance
        ]

    def spin(self) -> tuple[str, float]:
        rand = random.random()
        cumulative = 0
        for name, multiplier, chance in self.segments:
            cumulative += chance
            if rand <= cumulative:
                return name, multiplier
        return self.segments[-1][0], self.segments[-1][1]

class WheelView(View):
    def __init__(self, bet: int, player_id: int, ctx):
        super().__init__(timeout=None)
        self.bet = bet
        self.player_id = player_id
        self.ctx = ctx
        self.message = None
        self.wheel = WheelGame()
        self.spinning = False
        self.frames = [
            "🎡 ⬇️\n1.2x 💀 1.5x\n5.0x 🎯 2.0x\n3.0x 1.2x 💀",
            "🎡 ⬇️\n💀 1.2x 1.5x\n3.0x 5.0x 2.0x\n2.0x 3.0x 1.2x",
            "🎡 ⬇️\n1.5x 💀 1.2x\n2.0x 3.0x 5.0x\n5.0x 2.0x 3.0x",
            "🎡 ⬇️\n1.2x 1.5x 💀\n5.0x 2.0x 3.0x\n3.0x 5.0x 2.0x"
        ]
        self.current_frame = 0

    @discord.ui.button(label="Drehen 🎡", style=discord.ButtonStyle.green)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        if self.spinning:
            await interaction.response.send_message("Das Rad dreht sich bereits!", ephemeral=True)
            return

        self.spinning = True
        button.disabled = True
        await interaction.response.defer()

        # Animation des sich drehenden Rads
        for _ in range(12):  # 3 volle Umdrehungen
            embed = discord.Embed(
                title="🎡 Glücksrad",
                description=self.frames[self.current_frame],
                color=discord.Color.gold()
            )
            embed.add_field(
                name="💰 Einsatz",
                value=f"**{self.bet}** Coins",
                inline=False
            )
            await self.message.edit(embed=embed, view=self)
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            await asyncio.sleep(0.5)

        # Endergebnis
        segment_name, multiplier = self.wheel.spin()
        winnings = int(self.bet * multiplier)
        
        # Finale Animation mit Gewinn
        description = (
            f"🎯 Der Zeiger landet auf: **{segment_name}**!\n\n"
            f"{'🎉 Gewonnen!' if multiplier > 0 else '💀 Verloren!'}\n"
            f"Multiplikator: **{multiplier}x**\n"
            f"{'Gewinn' if multiplier > 0 else 'Verlust'}: **{abs(winnings - self.bet)}** Coins"
        )
        
        embed = discord.Embed(
            title="🎡 Glücksrad - Ergebnis",
            description=description,
            color=discord.Color.green() if multiplier > 0 else discord.Color.red()
        )
        
        # Aktualisiere Coins
        if multiplier > 0:
            update_coins(self.player_id, winnings)  # Bei Gewinn: Zahle Gewinn aus
        
        self.clear_items()  # Entferne alle Buttons
        await self.message.edit(embed=embed, view=self)

    async def start(self):
        embed = discord.Embed(
            title="🎡 Glücksrad",
            description="Drücke den Knopf um das Glücksrad zu drehen!\n\n"
                      "**Mögliche Gewinne:**\n"
                      "💎 5.0x (5% Chance)\n"
                      "🌟 3.0x (10% Chance)\n"
                      "💰 2.0x (15% Chance)\n"
                      "✨ 1.5x (20% Chance)\n"
                      "💫 1.2x (25% Chance)\n"
                      "💀 0.0x (25% Chance)",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="💰 Einsatz",
            value=f"**{self.bet}** Coins",
            inline=False
        )
        self.message = await self.ctx.send(embed=embed, view=self)

@bot.command()
async def wheel(ctx, bet: int = None):
    if not bet:
        embed = discord.Embed(
            title="🎡 Glücksrad",
            description="Drehe am Glücksrad und gewinne bis zu 5x deinen Einsatz!\n\n"
                      "**Multiplikatoren:**\n"
                      "• 💎 5.0x (5% Chance)\n"
                      "• 🌟 3.0x (10% Chance)\n"
                      "• 💰 2.0x (15% Chance)\n"
                      "• ✨ 1.5x (20% Chance)\n"
                      "• 💫 1.2x (25% Chance)\n"
                      "• 💀 0.0x (25% Chance)\n\n"
                      "**Verwendung:**\n"
                      "`!wheel <einsatz>`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet < 50:
        await ctx.send("❌ Der Minimaleinsatz ist 50 Coins!")
        return

    user_coins = get_coins(ctx.author.id)
    if user_coins < bet:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    # Ziehe Einsatz ab
    update_coins(ctx.author.id, -bet)

    # Starte Spiel
    view = WheelView(bet, ctx.author.id, ctx)
    await view.start()

class SlotsGame:
    def __init__(self):
        # Symbole mit ihren Wahrscheinlichkeiten und Multiplikatoren
        self.symbols = {
            "💎": {"weight": 1, "multiplier": 50.0},   # Diamant
            "7️⃣": {"weight": 2, "multiplier": 20.0},   # Sieben
            "🍀": {"weight": 3, "multiplier": 10.0},   # Kleeblatt
            "⭐": {"weight": 4, "multiplier": 5.0},    # Stern
            "🔔": {"weight": 5, "multiplier": 3.0},    # Glocke
            "🍒": {"weight": 6, "multiplier": 2.0},    # Kirsche
            "🍋": {"weight": 7, "multiplier": 1.5}     # Zitrone
        }
        
        # Erstelle gewichtete Liste für random.choices
        self.symbols_list = []
        self.weights = []
        for symbol, data in self.symbols.items():
            self.symbols_list.append(symbol)
            self.weights.append(data["weight"])
    
    def spin(self) -> list[str]:
        return random.choices(self.symbols_list, weights=self.weights, k=3)
    
    def get_win_multiplier(self, result: list[str]) -> tuple[float, str]:
        # Alle gleich
        if len(set(result)) == 1:
            symbol = result[0]
            return self.symbols[symbol]["multiplier"], f"3x {symbol}"
        
        # Zwei gleich
        if len(set(result)) == 2:
            for symbol in result:
                if result.count(symbol) == 2:
                    return self.symbols[symbol]["multiplier"] * 0.5, f"2x {symbol}"
        
        return 0, "Keine Gewinnkombination"

class SlotsView(View):
    def __init__(self, bet_amount: int, user_id: int, ctx):
        super().__init__(timeout=30)  # 30 Sekunden Timeout
        self.bet_amount = bet_amount
        self.user_id = user_id
        self.ctx = ctx
        self.message = None
        self.spinning = False

    async def start(self):
        embed = discord.Embed(
            title="🎰 Spielautomat",
            description=f"Einsatz: {self.bet_amount} Coins\n\n"
                      "**Gewinne:**\n"
                      "💎 Diamant: 50x\n"
                      "7️⃣ Sieben: 20x\n"
                      "🍀 Kleeblatt: 10x\n"
                      "⭐ Stern: 5x\n"
                      "🔔 Glocke: 3x\n"
                      "🍒 Kirsche: 2x\n"
                      "🍋 Zitrone: 1.5x\n\n"
                      "Drücke 'Drehen' zum Starten!",
            color=discord.Color.gold()
        )
        self.message = await self.ctx.send(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Drehen", style=discord.ButtonStyle.success, emoji="🎰")
    async def spin(self, interaction: discord.Interaction, button: Button):
        if self.spinning:
            await interaction.response.send_message("Die Walzen drehen sich bereits!", ephemeral=True)
            return

        self.spinning = True
        button.disabled = True
        await interaction.response.edit_message(view=self)

        symbols = ["💎", "7️⃣", "🍀", "⭐", "🔔", "🍒", "🍋"]
        weights = [1, 2, 3, 4, 5, 6, 7]  # Seltenere Symbole = höhere Gewinne
        
        # Animation der Walzen
        for _ in range(3):
            temp_result = random.choices(symbols, weights=weights, k=3)
            display = f"┃ {' '.join(temp_result)} ┃"
            embed = discord.Embed(
                title="🎰 Spielautomat",
                description=f"Die Walzen drehen sich...\n\n{display}",
                color=discord.Color.gold()
            )
            await self.message.edit(embed=embed)
            await asyncio.sleep(0.5)

        # Endgültiges Ergebnis
        result = random.choices(symbols, weights=weights, k=3)
        display = f"┃ {' '.join(result)} ┃"

        # Prüfe auf Gewinn
        if len(set(result)) == 1:  # Alle Symbole gleich
            symbol = result[0]
            multipliers = {"💎": 50, "7️⃣": 20, "🍀": 10, "⭐": 5, "🔔": 3, "🍒": 2, "🍋": 1.5}
            winnings = int(self.bet_amount * multipliers[symbol])
            update_coins(self.user_id, winnings)
            embed = discord.Embed(
                title="🎰 JACKPOT! 🎉",
                description=f"{display}\n\n**Gewonnen!** Du bekommst {winnings} Coins!",
                color=discord.Color.green()
            )
        elif len(set(result)) == 2:  # Zwei gleich
            winnings = int(self.bet_amount * 0.5)
            update_coins(self.user_id, winnings)
            embed = discord.Embed(
                title="🎰 Gewonnen! 🎉",
                description=f"{display}\n\n**Zwei gleiche Symbole!** Du bekommst {winnings} Coins!",
                color=discord.Color.blue()
            )
        else:
            embed = discord.Embed(
                title="🎰 Verloren! 😢",
                description=f"{display}\n\nLeider keine Gewinnkombination!",
                color=discord.Color.red()
            )

        await self.message.edit(embed=embed)

@bot.command()
async def slots(ctx, bet_amount: int = None):
    if not bet_amount:
        embed = discord.Embed(
            title="🎰 Spielautomat",
            description="Drehe am Spielautomaten!\n\n"
                      "**Gewinne:**\n"
                      "💎 Diamant: 50x\n"
                      "7️⃣ Sieben: 20x\n"
                      "🍀 Kleeblatt: 10x\n"
                      "⭐ Stern: 5x\n"
                      "🔔 Glocke: 3x\n"
                      "🍒 Kirsche: 2x\n"
                      "🍋 Zitrone: 1.5x\n\n"
                      "**Verwendung:**\n"
                      "`!slots <einsatz>`\n"
                      "Beispiel: `!slots 100`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 1:
        await ctx.send("❌ Der Mindesteinsatz ist 1 Coin!")
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    update_coins(ctx.author.id, -bet_amount)
    view = SlotsView(bet_amount, ctx.author.id, ctx)
    await view.start()

# Pferderennen Command
@bot.command()
async def horserace(ctx, bet_amount: int = None, horse: str = None):
    valid_horses = {"braun": "🐎", "einhorn": "🦄", "weiss": "🐴"}
    
    if not bet_amount or not horse or horse.lower() not in valid_horses:
        embed = discord.Embed(
            title="🏇 Pferderennen",
            description="Wette auf ein Pferd!\n\n"
                      "**Pferde:**\n"
                      "🐎 Braunes Pferd (braun)\n"
                      "🦄 Einhorn (einhorn)\n"
                      "🐴 Weißes Pferd (weiss)\n\n"
                      "**Gewinne:**\n"
                      "• Gewinner: 3x Einsatz\n\n"
                      "**Verwendung:**\n"
                      "`!horserace <einsatz> <pferd>`\n"
                      "Beispiel: `!horserace 100 einhorn`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 1:
        await ctx.send("❌ Der Mindesteinsatz ist 1 Coin!")
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    update_coins(ctx.author.id, -bet_amount)
    chosen_horse = valid_horses[horse.lower()]
    race = HorseRace(bet_amount, ctx.author.id)

    embed = discord.Embed(
        title="🏇 Pferderennen",
        description=f"Das Rennen beginnt!\nDeine Wette: {chosen_horse}\n\n{race.get_track_display()}",
        color=discord.Color.gold()
    )
    race.message = await ctx.send(embed=embed)

    while not race.winner:
        race.move_horses()
        embed.description = f"Das Rennen läuft!\nDeine Wette: {chosen_horse}\n\n{race.get_track_display()}"
        await race.message.edit(embed=embed)
        await asyncio.sleep(0.3)  # Schnellere Updates

    # Zeige Ergebnis
    if race.winner == chosen_horse:
        winnings = bet_amount * 3
        update_coins(ctx.author.id, winnings)
        embed.description = f"**Gewonnen!** 🎉\nDein Pferd {chosen_horse} hat gewonnen!\nDu bekommst {winnings} Coins!\n\n{race.get_track_display()}"
        embed.color = discord.Color.green()
    else:
        embed.description = f"**Verloren!** 😢\n{race.winner} hat gewonnen!\nDein Pferd: {chosen_horse}\n\n{race.get_track_display()}"
        embed.color = discord.Color.red()

    await race.message.edit(embed=embed)

class RouletteGame:
    def __init__(self):
        # Roulette Zahlen und ihre Eigenschaften
        self.numbers = {
            "0": {"color": "", "value": 0},
            **{str(i): {"color": "" if i in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "", "value": i}
               for i in range(1, 37)}
        }
    
    def get_number_display(self, number: str) -> str:
        return f"{self.numbers[number]['color']}{number.zfill(2)}"
    
    def spin(self) -> str:
        return random.choice(list(self.numbers.keys()))
    
    def check_bet(self, bet_type: str, bet_value: str, result: str) -> tuple[bool, float]:
        result_num = self.numbers[result]["value"]
        result_color = self.numbers[result]["color"]
        
        if bet_type == "number":
            return bet_value == result, 35.0
        elif bet_type == "color":
            return (bet_value == "red" and result_color == "") or (bet_value == "black" and result_color == ""), 2.0
        elif bet_type == "even_odd":
            if result_num == 0:
                return False, 2.0
            return (bet_value == "even" and result_num % 2 == 0) or (bet_value == "odd" and result_num % 2 == 1), 2.0
        elif bet_type == "dozen":
            if result_num == 0:
                return False, 3.0
            dozen = (result_num - 1) // 12
            return str(dozen) == bet_value, 3.0
        elif bet_type == "half":
            if result_num == 0:
                return False, 2.0
            return (bet_value == "first" and result_num <= 18) or (bet_value == "second" and result_num > 18), 2.0
        return False, 0

class RouletteView(View):
    def __init__(self, bet_amount: int, user_id: int, ctx):
        super().__init__(timeout=30)  # 30 Sekunden Timeout
        self.bet_amount = bet_amount
        self.user_id = user_id
        self.ctx = ctx
        self.message = None
        self.spinning = False

    async def start(self):
        embed = discord.Embed(
            title="🎲 Roulette",
            description=f"Einsatz: {self.bet_amount} Coins\n\n"
                      "**Wetten:**\n"
                      "🔴 Rot (2x)\n"
                      "⚫ Schwarz (2x)\n"
                      "🟢 Grün (14x)\n"
                      "🔢 Gerade/Ungerade (2x)\n\n"
                      "Wähle deine Wette!",
            color=discord.Color.gold()
        )
        self.message = await self.ctx.send(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Rot", style=discord.ButtonStyle.danger, emoji="🔴", row=0)
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin_roulette(interaction, "Rot")

    @discord.ui.button(label="Schwarz", style=discord.ButtonStyle.secondary, emoji="⚫", row=0)
    async def black(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin_roulette(interaction, "Schwarz")

    @discord.ui.button(label="Grün", style=discord.ButtonStyle.success, emoji="🟢", row=0)
    async def green(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin_roulette(interaction, "Grün")

    @discord.ui.button(label="Gerade", style=discord.ButtonStyle.primary, emoji="2️⃣", row=1)
    async def even(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin_roulette(interaction, "Gerade")

    @discord.ui.button(label="Ungerade", style=discord.ButtonStyle.primary, emoji="1️⃣", row=1)
    async def odd(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.spin_roulette(interaction, "Ungerade")

    async def spin_roulette(self, interaction: discord.Interaction, bet_type: str):
        if self.spinning:
            await interaction.response.send_message("Das Rad dreht sich bereits!", ephemeral=True)
            return

        self.spinning = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        # Roulette Animation
        numbers = list(range(0, 37))
        colors = {0: "🟢"}
        for i in range(1, 37):
            colors[i] = "🔴" if i in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "⚫"

        embed = discord.Embed(title="🎲 Roulette", color=discord.Color.gold())
        embed.add_field(name="Deine Wette", value=bet_type)
        embed.add_field(name="Einsatz", value=f"{self.bet_amount} Coins")

        # Dreh-Animation
        for _ in range(3):
            temp_number = random.choice(numbers)
            embed.description = f"Das Rad dreht sich... {colors[temp_number]} {temp_number}"
            await self.message.edit(embed=embed)
            await asyncio.sleep(0.7)

        # Endergebnis
        result = random.choice(numbers)
        result_color = colors[result]
        
        won = False
        winnings = 0
        
        # Prüfe Gewinn
        if bet_type == "Rot" and result_color == "🔴":
            won = True
            winnings = self.bet_amount * 2
        elif bet_type == "Schwarz" and result_color == "⚫":
            won = True
            winnings = self.bet_amount * 2
        elif bet_type == "Grün" and result_color == "🟢":
            won = True
            winnings = self.bet_amount * 14
        elif bet_type == "Gerade" and result != 0 and result % 2 == 0:
            won = True
            winnings = self.bet_amount * 2
        elif bet_type == "Ungerade" and result != 0 and result % 2 == 1:
            won = True
            winnings = self.bet_amount * 2

        if won:
            update_coins(self.user_id, winnings)
            embed.description = f"🎯 {result_color} {result}\n\n**Gewonnen!** Du bekommst {winnings} Coins!"
            embed.color = discord.Color.green()
        else:
            embed.description = f"🎯 {result_color} {result}\n\n**Verloren!**"
            embed.color = discord.Color.red()

        await self.message.edit(embed=embed)

@bot.command()
async def roulette(ctx, bet_amount: int = None):
    if not bet_amount:
        embed = discord.Embed(
            title="🎲 Roulette",
            description="Setze auf eine Farbe oder Zahl!\n\n"
                      "**Wetten & Gewinne:**\n"
                      "🔴 Rot: 2x\n"
                      "⚫ Schwarz: 2x\n"
                      "🟢 Grün (0): 14x\n"
                      "2️⃣ Gerade: 2x\n"
                      "1️⃣ Ungerade: 2x\n\n"
                      "**Verwendung:**\n"
                      "`!roulette <einsatz>`\n"
                      "Beispiel: `!roulette 100`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 1:
        await ctx.send("❌ Der Mindesteinsatz ist 1 Coin!")
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    update_coins(ctx.author.id, -bet_amount)
    view = RouletteView(bet_amount, ctx.author.id, ctx)
    await view.start()

class CoinflipView(View):
    def __init__(self, bet_amount: int, user_id: int, ctx):
        super().__init__(timeout=30)  # 30 Sekunden Timeout
        self.bet_amount = bet_amount
        self.user_id = user_id
        self.ctx = ctx
        self.message = None

    async def start(self):
        embed = discord.Embed(
            title="🎰 Coinflip",
            description=f"Wähle Kopf oder Zahl!\nEinsatz: {self.bet_amount} Coins",
            color=discord.Color.gold()
        )
        self.message = await self.ctx.send(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Kopf", style=discord.ButtonStyle.primary, emoji="👑")
    async def heads_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.flip_coin(interaction, "Kopf")

    @discord.ui.button(label="Zahl", style=discord.ButtonStyle.primary, emoji="🔢")
    async def tails_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.flip_coin(interaction, "Zahl")

    async def flip_coin(self, interaction: discord.Interaction, choice: str):
        # Deaktiviere Buttons sofort
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        # Münzwurf Animation
        result = random.choice(["Kopf", "Zahl"])
        embed = discord.Embed(title="🎰 Coinflip", color=discord.Color.gold())
        embed.add_field(name="Deine Wahl", value=choice)
        embed.add_field(name="Einsatz", value=f"{self.bet_amount} Coins")

        # Animiere den Münzwurf
        for _ in range(3):
            embed.description = "Münze wird geworfen... 🔄"
            await self.message.edit(embed=embed)
            await asyncio.sleep(0.5)

        # Zeige Ergebnis
        if choice == result:
            winnings = self.bet_amount * 2
            update_coins(self.user_id, winnings)
            embed.description = f"🎯 **{result}**!\n\n**Gewonnen!** Du bekommst {winnings} Coins!"
            embed.color = discord.Color.green()
        else:
            embed.description = f"🎯 **{result}**!\n\n**Verloren!**"
            embed.color = discord.Color.red()

        embed.add_field(name="Ergebnis", value=result, inline=False)
        await self.message.edit(embed=embed)

@bot.command()
async def coinflip(ctx, bet_amount: int = None, choice: str = None):
    if bet_amount is None or choice is None:
        embed = discord.Embed(
            title="❌ Fehler",
            description="Bitte gib einen Einsatz und deine Wahl (Kopf/Zahl) an!\n\n"
                       "**Verwendung:**\n"
                       "`!coinflip <einsatz> <kopf/zahl>`\n"
                       "Beispiel: `!coinflip 100 kopf`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 1:
        embed = discord.Embed(
            title="❌ Fehler",
            description="Der Mindesteinsatz ist 1 Coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    choice = choice.lower()
    if choice not in ['kopf', 'zahl']:
        embed = discord.Embed(
            title="❌ Fehler",
            description="Bitte wähle 'kopf' oder 'zahl'!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    user_coins = get_coins(ctx.author.id)
    if user_coins < bet_amount:
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Du hast nicht genug Coins! Dir fehlen noch **{bet_amount - user_coins:,}** Coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Münzwurf Animation
    embed = discord.Embed(
        title="🪙 Münzwurf",
        description="Die Münze dreht sich...",
        color=discord.Color.blue()
    )
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(2)

    # Ergebnis
    result = random.choice(['kopf', 'zahl'])
    if result == choice:
        winnings = bet_amount * 2
        update_coins(ctx.author.id, bet_amount)  # Gewinn = Einsatz * 2
        embed = discord.Embed(
            title="🪙 Münzwurf",
            description=f"🎯 **{result.upper()}**!\n\n💰 Du gewinnst **{winnings:,}** Coins!",
            color=discord.Color.green()
        )
    else:
        update_coins(ctx.author.id, -bet_amount)
        embed = discord.Embed(
            title="🪙 Münzwurf",
            description=f"❌ **{result.upper()}**!\n\n💸 Du verlierst **{bet_amount:,}** Coins!",
            color=discord.Color.red()
        )

    await msg.edit(embed=embed)

class ScratchView(View):
    def __init__(self, bet_amount: int, user_id: int, ctx):
        super().__init__(timeout=30)  # 30 Sekunden Timeout
        self.bet_amount = bet_amount
        self.user_id = user_id
        self.ctx = ctx
        self.message = None
        self.revealed = 0
        self.symbols = self.generate_symbols()
        self.revealed_positions = []

    def generate_symbols(self):
        symbols = ["💎", "🎰", "7️⃣", "⭐", "🔔", "🍒", "🍋"]
        weights = [0.1, 0.2, 0.2, 0.2, 0.2, 0.1, 0.1]  # Seltenere Symbole = höhere Gewinne
        return random.choices(symbols, weights=weights, k=9)

    async def start(self):
        embed = discord.Embed(
            title="🎰 Rubbellos",
            description=f"Rubble 3 Felder frei!\nEinsatz: {self.bet_amount} Coins\n\n"
                      "**Gewinne:**\n"
                      "💎 Diamant: 5x\n"
                      "🎰 Slot: 4x\n"
                      "7️⃣ Sieben: 3x\n"
                      "⭐ Stern: 2x\n"
                      "🔔 Glocke: 1.5x",
            color=discord.Color.gold()
        )
        self.message = await self.ctx.send(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    def create_grid(self):
        grid = ""
        for i in range(0, 9, 3):
            row = []
            for j in range(3):
                pos = i + j
                if pos in self.revealed_positions:
                    row.append(self.symbols[pos])
                else:
                    row.append("❓")
            grid += " ".join(row) + "\n"
        return grid

    @discord.ui.button(label="1", style=discord.ButtonStyle.secondary, row=0)
    async def button_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 0, button)

    @discord.ui.button(label="2", style=discord.ButtonStyle.secondary, row=0)
    async def button_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 1, button)

    @discord.ui.button(label="3", style=discord.ButtonStyle.secondary, row=0)
    async def button_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 2, button)

    @discord.ui.button(label="4", style=discord.ButtonStyle.secondary, row=1)
    async def button_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 3, button)

    @discord.ui.button(label="5", style=discord.ButtonStyle.secondary, row=1)
    async def button_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 4, button)

    @discord.ui.button(label="6", style=discord.ButtonStyle.secondary, row=1)
    async def button_6(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 5, button)

    @discord.ui.button(label="7", style=discord.ButtonStyle.secondary, row=2)
    async def button_7(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 6, button)

    @discord.ui.button(label="8", style=discord.ButtonStyle.secondary, row=2)
    async def button_8(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 7, button)

    @discord.ui.button(label="9", style=discord.ButtonStyle.secondary, row=2)
    async def button_9(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.reveal(interaction, 8, button)

    async def reveal(self, interaction: discord.Interaction, position: int, button: discord.ui.Button):
        if self.revealed >= 3:
            await interaction.response.send_message("Du hast bereits 3 Felder aufgedeckt!", ephemeral=True)
            return

        self.revealed += 1
        self.revealed_positions.append(position)
        button.label = self.symbols[position]
        button.disabled = True

        embed = discord.Embed(
            title="🎰 Rubbellos",
            description=f"Noch {3-self.revealed} Felder übrig!\n\n{self.create_grid()}",
            color=discord.Color.gold()
        )

        if self.revealed == 3:
            # Prüfe auf Gewinn
            revealed_symbols = [self.symbols[i] for i in self.revealed_positions]
            if len(set(revealed_symbols)) == 1:  # Alle Symbole gleich
                symbol = revealed_symbols[0]
                multipliers = {"💎": 5, "🎰": 4, "7️⃣": 3, "⭐": 2, "🔔": 1.5}
                winnings = int(self.bet_amount * multipliers[symbol])
                update_coins(self.user_id, winnings)
                embed.description = f"🎯 **{symbol}** gefunden!\n\n**Gewonnen!** Du bekommst {winnings} Coins!\n\n{self.create_grid()}"
                embed.color = discord.Color.green()
            else:
                embed.description = f"**Verloren!**\n\n{self.create_grid()}"
                embed.color = discord.Color.red()

            # Deaktiviere alle Buttons
            for child in self.children:
                child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)

@bot.command()
async def scratch(ctx, bet_amount: int = None):
    if not bet_amount:
        embed = discord.Embed(
            title="🎰 Rubbellos",
            description="Finde 3 gleiche Symbole und gewinne!\n\n"
                      "**Gewinne:**\n"
                      "💎 Diamant: 5x\n"
                      "🎰 Slot: 4x\n"
                      "7️⃣ Sieben: 3x\n"
                      "⭐ Stern: 2x\n"
                      "🔔 Glocke: 1.5x\n\n"
                      "**Verwendung:**\n"
                      "`!scratch <einsatz>`\n"
                      "Beispiel: `!scratch 100`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 1:
        await ctx.send("❌ Der Mindesteinsatz ist 1 Coin!")
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    update_coins(ctx.author.id, -bet_amount)
    view = ScratchView(bet_amount, ctx.author.id, ctx)
    await view.start()

class DiceGame:
    def __init__(self):
        self.dice = []

    def roll(self) -> int:
        return random.randint(1, 6)

class DiceView(View):
    def __init__(self, bet_amount: int, user_id: int, ctx):
        super().__init__(timeout=None)
        self.bet_amount = bet_amount
        self.user_id = user_id
        self.ctx = ctx
        self.message = None
        self.dice = DiceGame()

    async def start(self):
        embed = discord.Embed(
            title="🎲 Würfelspiel",
            description="Wette auf eine Zahl zwischen 1-6!\n\n"
                      "**Gewinne:**\n"
                      "• Richtige Zahl: 5x Einsatz\n"
                      "• ±1 daneben: 2x Einsatz",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="💰 Einsatz",
            value=f"**{self.bet_amount}** Coins",
            inline=False
        )
        self.message = await self.ctx.send(embed=embed, view=self)

    @discord.ui.button(label="1", style=discord.ButtonStyle.primary, row=0)
    async def button_1(self, interaction: discord.Interaction, button: Button):
        await self.roll_dice(interaction, 1)

    @discord.ui.button(label="2", style=discord.ButtonStyle.primary, row=0)
    async def button_2(self, interaction: discord.Interaction, button: Button):
        await self.roll_dice(interaction, 2)

    @discord.ui.button(label="3", style=discord.ButtonStyle.primary, row=0)
    async def button_3(self, interaction: discord.Interaction, button: Button):
        await self.roll_dice(interaction, 3)

    @discord.ui.button(label="4", style=discord.ButtonStyle.primary, row=1)
    async def button_4(self, interaction: discord.Interaction, button: Button):
        await self.roll_dice(interaction, 4)

    @discord.ui.button(label="5", style=discord.ButtonStyle.primary, row=1)
    async def button_5(self, interaction: discord.Interaction, button: Button):
        await self.roll_dice(interaction, 5)

    @discord.ui.button(label="6", style=discord.ButtonStyle.primary, row=1)
    async def button_6(self, interaction: discord.Interaction, button: Button):
        await self.roll_dice(interaction, 6)

    async def roll_dice(self, interaction: discord.Interaction, choice: int):
        # Deaktiviere Buttons sofort
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)

        # Würfel Animation
        result = random.randint(1, 6)
        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        embed = discord.Embed(title="🎲 Würfelspiel", color=discord.Color.gold())
        embed.add_field(name="Deine Wahl", value=str(choice))
        embed.add_field(name="Einsatz", value=f"{self.bet_amount} Coins")

        # Animiere den Würfelwurf
        for _ in range(3):
            temp_roll = random.randint(1, 6)
            embed.description = f"Würfel wird geworfen... {dice_faces[temp_roll-1]}"
            await self.message.edit(embed=embed)
            await asyncio.sleep(0.5)

        # Zeige Ergebnis
        if choice == result:
            winnings = self.bet_amount * 5
            update_coins(self.user_id, winnings)
            embed.description = f"🎯 **{result}**!\n\n**Gewonnen!** Du bekommst {winnings} Coins!"
            embed.color = discord.Color.green()
        elif abs(choice - result) == 1:
            winnings = self.bet_amount * 2
            update_coins(self.user_id, winnings)
            embed.description = f"🎯 **{result}**!\n\n**Fast!** Du bekommst {winnings} Coins!"
            embed.color = discord.Color.blue()
        else:
            embed.description = f"🎯 **{result}**!\n\n**Verloren!**"
            embed.color = discord.Color.red()

        embed.add_field(name="Ergebnis", value=f"{dice_faces[result-1]} ({result})", inline=False)
        await self.message.edit(embed=embed)

@bot.command()
async def dice(ctx, bet_amount: int = None):
    if not bet_amount:
        embed = discord.Embed(
            title="🎲 Würfelspiel",
            description="Wette auf eine Zahl zwischen 1-6!\n\n"
                      "**Gewinne:**\n"
                      "• Richtige Zahl: 5x Einsatz\n"
                      "• ±1 daneben: 2x Einsatz\n\n"
                      "**Verwendung:**\n"
                      "`!dice <einsatz>`\n"
                      "Beispiel: `!dice 100`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 1:
        await ctx.send("❌ Der Mindesteinsatz ist 1 Coin!")
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    update_coins(ctx.author.id, -bet_amount)
    view = DiceView(bet_amount, ctx.author.id, ctx)
    await view.start()

class YahtzeeGame:
    def __init__(self):
        self.dice = []
        self.rolls_left = 3
        self.score = 0
        
    def roll_dice(self, keep_indices=None):
        if keep_indices is None:
            keep_indices = []
            
        for i in range(5):
            if i not in keep_indices:
                if len(self.dice) <= i:
                    self.dice.append(random.randint(1, 6))
                else:
                    self.dice[i] = random.randint(1, 6)
        
        self.rolls_left -= 1
        
    def get_score(self):
        # Zähle die Häufigkeit jeder Zahl
        counts = [self.dice.count(i) for i in range(1, 7)]
        
        # Yahtzee (5 gleiche) - 50 Punkte
        if 5 in counts:
            return 50
            
        # Vierlinge - 40 Punkte
        if 4 in counts:
            return 40
            
        # Full House (3 + 2) - 25 Punkte
        if 3 in counts and 2 in counts:
            return 25
            
        # Große Straße (1-2-3-4-5 oder 2-3-4-5-6) - 30 Punkte
        sorted_dice = sorted(self.dice)
        if sorted_dice in [[1,2,3,4,5], [2,3,4,5,6]]:
            return 30
            
        # Kleine Straße (4 aufeinanderfolgende) - 20 Punkte
        for i in range(1, 4):
            if all(x in sorted_dice for x in range(i, i+4)):
                return 20
                
        # Drilling - 15 Punkte
        if 3 in counts:
            return 15
            
        # Zwei Paare - 10 Punkte
        if counts.count(2) == 2:
            return 10
            
        # Ein Paar - 5 Punkte
        if 2 in counts:
            return 5
            
        # Summe aller Würfel
        return sum(self.dice)

class YahtzeeView(View):
    def __init__(self, bet_amount: int, user_id: int, ctx):
        super().__init__(timeout=30)  # 30 Sekunden Timeout
        self.bet_amount = bet_amount
        self.user_id = user_id
        self.ctx = ctx
        self.message = None
        self.dice = []
        self.rolls_left = 3
        self.kept_dice = [False] * 5
        self.rolling = False

    async def start(self):
        self.roll_dice()
        await self.update_message()

    def roll_dice(self, keep_indices=None):
        if keep_indices is None:
            self.dice = [random.randint(1, 6) for _ in range(5)]
        else:
            new_dice = []
            for i in range(5):
                if i in keep_indices:
                    new_dice.append(self.dice[i])
                else:
                    new_dice.append(random.randint(1, 6))
            self.dice = new_dice
        self.rolls_left -= 1

    def get_dice_display(self):
        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        display = []
        for i, die in enumerate(self.dice):
            face = dice_faces[die-1]
            if self.kept_dice[i]:
                display.append(f"[{face}]")  # Gehaltene Würfel in Klammern
            else:
                display.append(face)
        return " ".join(display)

    async def update_message(self):
        description = (
            f"🎲 Würfel: {self.get_dice_display()}\n"
            f"🎯 Noch **{self.rolls_left}** Würfe übrig\n\n"
            "**Gewinne:**\n"
            "🎯 Yahtzee (5 gleiche): 50x\n"
            "🎲 Vier gleiche: 30x\n"
            "🎲 Full House: 20x\n"
            "🎲 Große Straße: 15x\n"
            "🎲 Kleine Straße: 10x\n"
            "🎲 Drei gleiche: 5x\n"
            "🎲 Zwei Paare: 3x\n"
            "🎲 Ein Paar: 1.5x\n\n"
        )

        if self.rolls_left > 0:
            description += "Wähle Würfel zum Halten und würfle erneut!"
        else:
            description += "Keine Würfe mehr übrig!"

        embed = discord.Embed(
            title="🎲 Yahtzee",
            description=description,
            color=discord.Color.gold()
        )
        embed.add_field(name="Einsatz", value=f"{self.bet_amount} Coins")

        if not self.message:
            self.message = await self.ctx.send(embed=embed, view=self)
        else:
            await self.message.edit(embed=embed, view=self)

    def check_win(self):
        # Zähle Würfel
        counts = {}
        for die in self.dice:
            counts[die] = counts.get(die, 0) + 1
        
        # Sortiere für Straßen
        sorted_dice = sorted(self.dice)
        
        # Prüfe Kombinationen
        if 5 in counts.values():  # Yahtzee
            return 50, "🎯 Yahtzee! (5 gleiche)"
        elif 4 in counts.values():  # Vier gleiche
            return 30, "🎲 Vier gleiche!"
        elif 3 in counts.values() and 2 in counts.values():  # Full House
            return 25, "🎲 Full House!"
        elif (sorted_dice == [1,2,3,4,5] or 
              sorted_dice == [2,3,4,5,6]):  # Große Straße
            return 30, "🎲 Große Straße!"
        elif any(all(x in sorted_dice for x in seq) for seq in [
            [1,2,3,4], [2,3,4,5], [3,4,5,6]]):  # Kleine Straße
            return 20, "🎲 Kleine Straße!"
        elif 3 in counts.values():  # Drei gleiche
            return 15, "🎲 Drei gleiche!"
        elif list(counts.values()).count(2) == 2:  # Zwei Paare
            return 10, "🎲 Zwei Paare!"
        elif 2 in counts.values():  # Ein Paar
            return 5, "🎲 Ein Paar!"
        return 0, "Keine Gewinnkombination"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Würfeln", style=discord.ButtonStyle.success, emoji="🎲", row=0)
    async def roll(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.rolling:
            await interaction.response.send_message("Die Würfel rollen bereits!", ephemeral=True)
            return

        if self.rolls_left <= 0:
            await interaction.response.send_message("Keine Würfe mehr übrig!", ephemeral=True)
            return

        self.rolling = True
        keep_indices = [i for i, kept in enumerate(self.kept_dice) if kept]
        
        # Animation
        for _ in range(3):
            temp_dice = self.dice.copy()
            for i in range(5):
                if i not in keep_indices:
                    temp_dice[i] = random.randint(1, 6)
            self.dice = temp_dice
            await self.update_message()
            await asyncio.sleep(0.3)  # Schnellere Updates

        # Echter Wurf
        self.roll_dice(keep_indices)
        
        if self.rolls_left == 0:
            # Prüfe auf Gewinn
            multiplier, combo_text = self.check_win()
            winnings = int(self.bet_amount * multiplier)
            
            if multiplier > 0:
                update_coins(self.user_id, winnings)
                embed = discord.Embed(
                    title="🎲 Yahtzee - Gewonnen! 🎉",
                    description=f"{self.get_dice_display()}\n\n"
                              f"**{combo_text}**\n"
                              f"Du bekommst {winnings} Coins!",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="🎲 Yahtzee - Verloren! 😢",
                    description=f"{self.get_dice_display()}\n\n"
                              "Keine Gewinnkombination!",
                    color=discord.Color.red()
                )
            
            # Deaktiviere alle Buttons
            for item in self.children:
                item.disabled = True
            await self.message.edit(embed=embed, view=self)
        else:
            self.rolling = False
            await self.update_message()

        await interaction.response.defer()

    @discord.ui.button(label="Würfel 1", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_die_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.rolling:
            await interaction.response.send_message("Warte bis die Würfel aufhören zu rollen!", ephemeral=True)
            return
        self.kept_dice[0] = not self.kept_dice[0]
        button.style = discord.ButtonStyle.primary if self.kept_dice[0] else discord.ButtonStyle.secondary
        await self.update_message()
        await interaction.response.defer()

    @discord.ui.button(label="Würfel 2", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_die_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.rolling:
            await interaction.response.send_message("Warte bis die Würfel aufhören zu rollen!", ephemeral=True)
            return
        self.kept_dice[1] = not self.kept_dice[1]
        button.style = discord.ButtonStyle.primary if self.kept_dice[1] else discord.ButtonStyle.secondary
        await self.update_message()
        await interaction.response.defer()

    @discord.ui.button(label="Würfel 3", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_die_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.rolling:
            await interaction.response.send_message("Warte bis die Würfel aufhören zu rollen!", ephemeral=True)
            return
        self.kept_dice[2] = not self.kept_dice[2]
        button.style = discord.ButtonStyle.primary if self.kept_dice[2] else discord.ButtonStyle.secondary
        await self.update_message()
        await interaction.response.defer()

    @discord.ui.button(label="Würfel 4", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_die_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.rolling:
            await interaction.response.send_message("Warte bis die Würfel aufhören zu rollen!", ephemeral=True)
            return
        self.kept_dice[3] = not self.kept_dice[3]
        button.style = discord.ButtonStyle.primary if self.kept_dice[3] else discord.ButtonStyle.secondary
        await self.update_message()
        await interaction.response.defer()

    @discord.ui.button(label="Würfel 5", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_die_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.rolling:
            await interaction.response.send_message("Warte bis die Würfel aufhören zu rollen!", ephemeral=True)
            return
        self.kept_dice[4] = not self.kept_dice[4]
        button.style = discord.ButtonStyle.primary if self.kept_dice[4] else discord.ButtonStyle.secondary
        await self.update_message()
        await interaction.response.defer()

@bot.command()
async def yahtzee(ctx, bet_amount: int = None):
    if not bet_amount:
        embed = discord.Embed(
            title="🎲 Yahtzee",
            description="Versuche die besten Würfelkombinationen!\n\n"
                      "**Gewinne:**\n"
                      "🎯 Yahtzee (5 gleiche): 50x\n"
                      "🎲 Vier gleiche: 30x\n"
                      "🎲 Full House: 20x\n"
                      "🎲 Große Straße: 15x\n"
                      "🎲 Kleine Straße: 10x\n"
                      "🎲 Drei gleiche: 5x\n"
                      "🎲 Zwei Paare: 3x\n"
                      "🎲 Ein Paar: 1.5x\n\n"
                      "**Verwendung:**\n"
                      "`!yahtzee <einsatz>`\n"
                      "Beispiel: `!yahtzee 100`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 1:
        await ctx.send("❌ Der Mindesteinsatz ist 1 Coin!")
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    update_coins(ctx.author.id, -bet_amount)
    view = YahtzeeView(bet_amount, ctx.author.id, ctx)
    await view.start()

# Globale Fehlermeldungen
INSUFFICIENT_COINS = "❌ Du hast nicht genug Coins!"
MINIMUM_BET = "❌ Der Mindesteinsatz ist {} Coins!"
NOT_YOUR_GAME = "❌ Das ist nicht dein Spiel!"
ALREADY_ROLLING = "❌ Die Würfel rollen bereits!"
ALREADY_SPINNING = "❌ Das Rad dreht sich bereits!"
NO_ROLLS_LEFT = "❌ Keine Würfe mehr übrig!"
WAIT_FOR_ROLL = "❌ Warte bis die Würfel aufhören zu rollen!"

# Hilfe-Texte für Spiele
SLOTS_HELP = """🎰 Drehe am Spielautomaten!

**Gewinne:**
💎 Diamant: 50x
7️⃣ Sieben: 20x
🍀 Kleeblatt: 10x
⭐ Stern: 5x
🔔 Glocke: 3x
🍒 Kirsche: 2x
🍋 Zitrone: 1.5x

**Verwendung:**
`!slots <einsatz>`
Beispiel: `!slots 100`"""

ROULETTE_HELP = """🎲 Setze auf eine Farbe oder Zahl!

**Wetten & Gewinne:**
🔴 Rot: 2x
⚫ Schwarz: 2x
🟢 Grün (0): 14x
2️⃣ Gerade: 2x
1️⃣ Ungerade: 2x

**Verwendung:**
`!roulette <einsatz>`
Beispiel: `!roulette 100`"""

DICE_HELP = """🎲 Wähle eine Zahl und würfle!

**Gewinne:**
• Richtige Zahl: 6x Einsatz
• Falsche Zahl: Verloren

**Verwendung:**
`!dice <einsatz>`
Beispiel: `!dice 100`"""

SCRATCH_HELP = """🎫 Kaufe ein Rubbellos!

**Gewinne:**
💎 Diamant: 50x
7️⃣ Sieben: 20x
🍀 Kleeblatt: 10x
⭐ Stern: 5x
🔔 Glocke: 3x
🍒 Kirsche: 2x
🍋 Zitrone: 1.5x

**Verwendung:**
`!scratch <einsatz>`
Beispiel: `!scratch 100`"""

RACE_HELP = """🏇 Wette auf ein Pferd!

**Wetten:**
• Pferd 1-3
• Gewinn: 3x Einsatz

**Verwendung:**
`!race <einsatz> <pferd>`
Beispiel: `!race 100 1`"""

YAHTZEE_HELP = """🎲 Würfelpoker!

**Gewinne:**
🎯 Yahtzee (5 gleiche): 50x
🎲 Vier gleiche: 30x
🎲 Full House: 20x
🎲 Große Straße: 15x
🎲 Kleine Straße: 10x
🎲 Drei gleiche: 5x
🎲 Zwei Paare: 3x
🎲 Ein Paar: 1.5x

**Verwendung:**
`!yahtzee <einsatz>`
Beispiel: `!yahtzee 100`"""

COINFLIP_HELP = """🪙 Wirf eine Münze!

**Gewinne:**
• Richtig: 2x Einsatz
• Falsch: Verloren

**Verwendung:**
`!coinflip <einsatz> <kopf/zahl>`
Beispiel: `!coinflip 100 kopf`"""

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        minutes = int(error.retry_after / 60)
        seconds = int(error.retry_after % 60)
        embed = discord.Embed(
            title="⏰ Cooldown",
            description=f"Dieser Befehl ist noch im Cooldown!\nVersuche es in {minutes}m {seconds}s erneut.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Keine Berechtigung",
            description="Du hast keine Berechtigung für diesen Befehl!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❓ Unbekannter Befehl",
            description="Dieser Befehl existiert nicht!\nNutze `!help` für eine Liste aller Befehle.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Fehlende Argumente",
            description="Dir fehlen wichtige Angaben für diesen Befehl!\nNutze `!help <befehl>` für Hilfe.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(
            title="❌ Ungültige Argumente",
            description="Deine Eingabe ist ungültig!\nNutze `!help <befehl>` für Hilfe.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Ein Fehler ist aufgetreten:\n```{str(error)}```",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f'🎮 Bot ist online als {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="!help | Casino Games"))

@bot.command()
async def help(ctx, command: str = None):
    if command:
        # Hilfe für spezifischen Befehl
        command = command.lower()
        if command == "slots":
            embed = discord.Embed(title="🎰 Slots - Hilfe", description=SLOTS_HELP, color=discord.Color.blue())
        elif command == "roulette":
            embed = discord.Embed(title="🎲 Roulette - Hilfe", description=ROULETTE_HELP, color=discord.Color.blue())
        elif command == "dice":
            embed = discord.Embed(title="🎲 Würfel - Hilfe", description=DICE_HELP, color=discord.Color.blue())
        elif command == "scratch":
            embed = discord.Embed(title="🎫 Rubbellos - Hilfe", description=SCRATCH_HELP, color=discord.Color.blue())
        elif command == "race":
            embed = discord.Embed(title="🏇 Pferderennen - Hilfe", description=RACE_HELP, color=discord.Color.blue())
        elif command == "yahtzee":
            embed = discord.Embed(title="🎲 Yahtzee - Hilfe", description=YAHTZEE_HELP, color=discord.Color.blue())
        elif command == "coinflip":
            embed = discord.Embed(title="🪙 Münzwurf - Hilfe", description=COINFLIP_HELP, color=discord.Color.blue())
        else:
            embed = discord.Embed(
                title="❓ Unbekannter Befehl",
                description=f"Der Befehl `{command}` wurde nicht gefunden!\nNutze `!help` für eine Liste aller Befehle.",
                color=discord.Color.red()
            )
    else:
        # Allgemeine Hilfe
        embed = discord.Embed(
            title="🎮 Casino Bot - Hilfe",
            description="Hier sind alle verfügbaren Befehle:",
            color=discord.Color.blue()
        )
        
        # Economy Commands
        embed.add_field(
            name="💰 Economy",
            value="```\n"
                  "!daily   - Tägliche Coins\n"
                  "!work    - Arbeiten für Coins\n"
                  "!beg     - Betteln für Coins\n"
                  "!rob     - Andere Spieler ausrauben\n"
                  "!balance - Zeigt dein Guthaben\n"
                  "!top     - Zeigt die reichsten Spieler\n"
                  "```",
            inline=False
        )
        
        # Casino Games
        embed.add_field(
            name="🎲 Casino Spiele",
            value="```\n"
                  "!slots    - Spielautomat\n"
                  "!roulette - Roulette\n"
                  "!coinflip - Münzwurf\n"
                  "!dice     - Würfelspiel\n"
                  "!scratch  - Rubbellos\n"
                  "!race     - Pferderennen\n"
                  "!yahtzee  - Würfelpoker\n"
                  "```",
            inline=False
        )
        
        embed.set_footer(text="Nutze !help <befehl> für mehr Infos zu einem Befehl")
    
    await ctx.send(embed=embed)

@bot.command()
async def balance(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    
    coins = get_coins(member.id)
    embed = discord.Embed(
        title="💰 Guthaben",
        description=f"{member.mention} hat **{coins:,}** Coins",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command()
async def top(ctx):
    cursor.execute("SELECT user_id, coins FROM economy ORDER BY coins DESC LIMIT 10")
    top_users = cursor.fetchall()
    
    description = ""
    for i, (user_id, coins) in enumerate(top_users, 1):
        user = bot.get_user(user_id)
        if user:
            medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
            description += f"{medal} **{i}.** {user.mention}: **{coins:,}** Coins\n"
    
    embed = discord.Embed(
        title="🏆 Reichste Spieler",
        description=description,
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)  # 24h cooldown
async def daily(ctx):
    amount = random.randint(1000, 2000)
    update_coins(ctx.author.id, amount)
    
    embed = discord.Embed(
        title="📅 Tägliche Belohnung",
        description=f"Du hast **{amount:,}** Coins erhalten!\nKomm morgen wieder!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.user)  # 1h cooldown
async def work(ctx):
    amount = random.randint(100, 500)
    update_coins(ctx.author.id, amount)
    
    jobs = [
        "🏢 Als Bürokaufmann",
        "🚕 Als Taxifahrer",
        "👨‍🍳 Als Koch",
        "🎨 Als Künstler",
        "🔧 Als Mechaniker",
        "💻 Als Programmierer",
        "📦 Als Paketbote",
        "🏪 Als Kassierer",
        "🌳 Als Gärtner",
        "🎵 Als Straßenmusiker"
    ]
    
    embed = discord.Embed(
        title="💼 Arbeit",
        description=f"{random.choice(jobs)} hast du **{amount:,}** Coins verdient!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 300, commands.BucketType.user)  # 5min cooldown
async def beg(ctx):
    amount = random.randint(1, 100)
    update_coins(ctx.author.id, amount)
    
    responses = [
        "🥺 Ein Passant hat Mitleid",
        "👵 Eine alte Dame ist großzügig",
        "🎭 Ein Straßenkünstler teilt",
        "🎪 Ein Zirkusclown ist nett",
        "🎸 Ein Musiker ist beeindruckt",
        "🎨 Ein Künstler ist inspiriert",
        "🌟 Ein Fan erkennt dich",
        "🍀 Dein Glückstag",
        "💝 Jemand mag dich",
        "🎁 Ein Geschenk vom Himmel"
    ]
    
    embed = discord.Embed(
        title="🙏 Betteln",
        description=f"{random.choice(responses)} und gibt dir **{amount:,}** Coins!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 7200, commands.BucketType.user)  # 2h cooldown
async def rob(ctx, victim: discord.Member):
    if victim.id == ctx.author.id:
        embed = discord.Embed(
            title="🤔 Moment mal...",
            description="Du kannst dich nicht selbst ausrauben!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    victim_coins = get_coins(victim.id)
    if victim_coins < 100:
        embed = discord.Embed(
            title="❌ Zu arm",
            description=f"{victim.mention} hat zu wenig Coins zum Ausrauben!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    success = random.random() < 0.4  # 40% Chance
    
    if success:
        amount = random.randint(1, min(1000, victim_coins))
        update_coins(victim.id, -amount)
        update_coins(ctx.author.id, amount)
        
        embed = discord.Embed(
            title="💰 Erfolgreicher Raub",
            description=f"Du hast {victim.mention} **{amount:,}** Coins geklaut!",
            color=discord.Color.green()
        )
    else:
        fine = random.randint(100, 500)
        update_coins(ctx.author.id, -fine)
        
        embed = discord.Embed(
            title="🚔 Erwischt",
            description=f"Du wurdest gefasst und musst **{fine:,}** Coins Strafe zahlen!",
            color=discord.Color.red()
        )
    
    await ctx.send(embed=embed)

# Wenn die Datei direkt ausgeführt wird
if __name__ == "__main__":
    keep_alive()  # Startet den Webserver für 24/7 Uptime
    bot.run(os.getenv('DISCORD_TOKEN'))
