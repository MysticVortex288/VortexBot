import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
from dotenv import load_dotenv
import sqlite3
import random
import asyncio
from typing import Optional, List, Dict
import time
from discord.ui import Button, View

# Lade Umgebungsvariablen
load_dotenv()

# Bot-Konfiguration
intents = discord.Intents.all()
intents.members = True
intents.message_content = True

class HorseRace:
    def __init__(self):
        self.horses = {
            "1": {"name": "Blitz ", "emoji": "", "position": 0, "speed": 1.2},
            "2": {"name": "Thunder ", "emoji": "", "position": 0, "speed": 1.1},
            "3": {"name": "Star ", "emoji": "", "position": 0, "speed": 1.0},
            "4": {"name": "Lucky ", "emoji": "", "position": 0, "speed": 0.9},
            "5": {"name": "Rainbow ", "emoji": "", "position": 0, "speed": 0.8}
        }
        self.track_length = 15
        self.running = False
        self.winner = None

    def reset(self):
        for horse in self.horses.values():
            horse["position"] = 0
        self.running = False
        self.winner = None

    def move_horses(self) -> bool:
        moved = False
        for horse in self.horses.values():
            if random.random() < horse["speed"] * 0.3:
                horse["position"] += 1
                moved = True
                if horse["position"] >= self.track_length:
                    self.winner = horse["name"]
                    self.running = False
                    return False
        return moved

    def get_track_display(self) -> str:
        display = ""
        for horse_id, horse in self.horses.items():
            pos = horse["position"]
            track = "." * pos + horse["emoji"] + "." * (self.track_length - pos - 1)
            display += f"`{horse_id}` {horse['name']}: |{track}|\n"
        return display

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

def update_last_used(user_id: int, command: str):
    with sqlite3.connect(bot.db_path) as conn:
        c = conn.cursor()
        c.execute(f'UPDATE economy SET {command}_last_used = ? WHERE user_id = ?',
                 (datetime.datetime.now().isoformat(), user_id))
        conn.commit()

def get_last_used(user_id: int, command: str) -> Optional[datetime.datetime]:
    with sqlite3.connect(bot.db_path) as conn:
        c = conn.cursor()
        c.execute(f'SELECT {command}_last_used FROM economy WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result and result[0]:
            return datetime.datetime.fromisoformat(result[0])
        return None

# Economy Commands
@bot.command()
async def daily(ctx):
    user_id = ctx.author.id
    last_used = get_last_used(user_id, 'daily')
    now = datetime.datetime.now()
    next_reset = now.replace(hour=1, minute=0, second=0, microsecond=0)
    
    if last_used:
        if last_used.date() == now.date() and now.hour >= 1:
            next_reset = next_reset + datetime.timedelta(days=1)
            await ctx.send(f" Du hast deine tägliche Belohnung bereits abgeholt! Komm zurück um {next_reset.strftime('%H:%M')} Uhr!")
            return

    coins = random.randint(300, 500)
    update_coins(user_id, coins)
    update_last_used(user_id, 'daily')
    
    embed = discord.Embed(
        title=" Tägliche Belohnung!",
        description=f"Du hast **{coins}** Coins erhalten!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
async def work(ctx):
    user_id = ctx.author.id
    last_used = get_last_used(user_id, 'work')
    now = datetime.datetime.now()
    
    if last_used:
        cooldown = datetime.timedelta(hours=4)
        time_left = (last_used + cooldown) - now
        if time_left.total_seconds() > 0:
            hours = int(time_left.total_seconds() // 3600)
            minutes = int((time_left.total_seconds() % 3600) // 60)
            await ctx.send(f" Du musst noch {hours}h {minutes}m warten, bevor du wieder arbeiten kannst!")
            return

    coins = random.randint(100, 200)
    update_coins(user_id, coins)
    update_last_used(user_id, 'work')
    
    messages = [
        f"Du hast hart gearbeitet und **{coins}** Coins verdient! ",
        f"Dein Chef ist zufrieden und gibt dir **{coins}** Coins! ",
        f"Ein erfolgreicher Arbeitstag! Du erhältst **{coins}** Coins! "
    ]
    
    embed = discord.Embed(
        title=" Arbeit",
        description=random.choice(messages),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
async def beg(ctx):
    user_id = ctx.author.id
    last_used = get_last_used(user_id, 'beg')
    now = datetime.datetime.now()
    
    if last_used:
        cooldown = datetime.timedelta(minutes=10)
        time_left = (last_used + cooldown) - now
        if time_left.total_seconds() > 0:
            minutes = int(time_left.total_seconds() // 60)
            await ctx.send(f" Du musst noch {minutes}m warten, bevor du wieder betteln kannst!")
            return

    is_crit = random.random() < 0.10  # 10% Chance auf Krit
    coins = random.randint(50, 100) if is_crit else random.randint(1, 50)
    update_coins(user_id, coins)
    update_last_used(user_id, 'beg')
    
    if is_crit:
        embed = discord.Embed(
            title=" Kritischer Erfolg beim Betteln!",
            description=f"Jemand war besonders großzügig! Du erhältst **{coins}** Coins!",
            color=discord.Color.gold()
        )
    else:
        messages = [
            f"Ein Passant gibt dir **{coins}** Coins...",
            f"Du findest **{coins}** Coins auf dem Boden!",
            f"Jemand hat Mitleid und gibt dir **{coins}** Coins."
        ]
        embed = discord.Embed(
            title=" Betteln",
            description=random.choice(messages),
            color=discord.Color.greyple()
        )
    await ctx.send(embed=embed)

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    if member.id == ctx.author.id:
        await ctx.send(" Du kannst dir nicht selbst Coins überweisen!")
        return
    
    if amount <= 0:
        await ctx.send(" Der Betrag muss positiv sein!")
        return
    
    sender_coins = get_coins(ctx.author.id)
    if sender_coins < amount:
        await ctx.send(" Du hast nicht genug Coins!")
        return
    
    update_coins(ctx.author.id, -amount)
    update_coins(member.id, amount)
    
    embed = discord.Embed(
        title=" Überweisung",
        description=f"{ctx.author.mention} hat {member.mention} **{amount}** Coins überwiesen!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
async def rob(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send(" Du kannst dich nicht selbst ausrauben!")
        return
    
    user_id = ctx.author.id
    last_used = get_last_used(user_id, 'rob')
    now = datetime.datetime.now()
    
    if last_used:
        cooldown = datetime.timedelta(hours=1)
        time_left = (last_used + cooldown) - now
        if time_left.total_seconds() > 0:
            minutes = int(time_left.total_seconds() // 60)
            await ctx.send(f" Du musst noch {minutes}m warten, bevor du wieder jemanden ausrauben kannst!")
            return
    
    victim_coins = get_coins(member.id)
    if victim_coins < 50:
        await ctx.send(f" {member.mention} hat zu wenig Coins zum Ausrauben!")
        return
    
    success = random.random() < 0.15  # 15% Erfolgschance
    update_last_used(user_id, 'rob')
    
    if success:
        stolen = random.randint(50, min(victim_coins, 500))
        update_coins(member.id, -stolen)
        update_coins(user_id, stolen)
        
        embed = discord.Embed(
            title=" Erfolgreicher Raub!",
            description=f"Du hast {member.mention} **{stolen}** Coins gestohlen!",
            color=discord.Color.dark_red()
        )
    else:
        fine = random.randint(50, 200)
        update_coins(user_id, -fine)
        
        embed = discord.Embed(
            title=" Erwischt!",
            description=f"Du wurdest beim Versuch {member.mention} auszurauben erwischt und musst **{fine}** Coins Strafe zahlen!",
            color=discord.Color.red()
        )
    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx):
    with sqlite3.connect(bot.db_path) as conn:
        c = conn.cursor()
        c.execute('SELECT user_id, coins FROM economy ORDER BY coins DESC LIMIT 10')
        top_users = c.fetchall()
    
    if not top_users:
        await ctx.send(" Noch keine Einträge im Leaderboard!")
        return
    
    embed = discord.Embed(
        title=" Reichste Nutzer",
        color=discord.Color.gold()
    )
    
    for i, (user_id, coins) in enumerate(top_users, 1):
        member = ctx.guild.get_member(user_id)
        name = member.name if member else f"Unbekannt ({user_id})"
        medal = {1: "", 2: "", 3: ""}.get(i, "")
        embed.add_field(
            name=f"{medal} Platz {i}",
            value=f"{name}: **{coins:,}** Coins",
            inline=False
        )
    
    await ctx.send(embed=embed)

# Event: Bot ist bereit
@bot.event
async def on_ready():
    bot.start_time = datetime.datetime.utcnow()
    print(f'{bot.user} ist online!')

# Funktion für Moderations-Embed
def create_mod_embed(action, user, moderator, reason, duration=None):
    embed = discord.Embed(
        title=f" Moderation: {action}",
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
            title=" Du wurdest gekickt!",
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
        title=" Moderation ausgeführt",
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
            title=" Du wurdest gebannt!",
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
        title=" Moderation ausgeführt",
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
            title=" Du wurdest in Timeout versetzt!",
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
        title=" Moderation ausgeführt",
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
            title=" Dein Timeout wurde aufgehoben!",
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
        title=" Moderation ausgeführt",
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
        title=" Bot Status",
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
            title=" Bot Hilfe",
            description="Hier sind die verfügbaren Kategorien:\n\n"
                      "• `!help moderation` - Moderations- und Statusbefehle\n"
                      "• `!help economy` - Wirtschaftssystem und Befehle\n"
                      "• `!help casino` - Casino-Spiele und Glücksspiel\n\n"
                      "Weitere Kategorien kommen bald!",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Benutze !help <kategorie> für mehr Details")
        await ctx.send(embed=embed)
        return
    
    if category.lower() == "moderation":
        # Moderations-Hilfe
        embed = discord.Embed(
            title=" Moderations- und Statusbefehle",
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
        embed.set_footer(text=" Diese Befehle erfordern Administrator-Rechte!")
        await ctx.send(embed=embed)
        return
    
    if category.lower() == "economy":
        # Economy-Hilfe
        embed = discord.Embed(
            title=" Wirtschaftssystem",
            description="Hier sind alle verfügbaren Economy-Befehle:",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="!daily",
            value="Erhalte täglich zwischen 300-500 Coins\n Cooldown: 24 Stunden (Reset um 1 Uhr nachts)",
            inline=False
        )
        embed.add_field(
            name="!work",
            value="Arbeite für 100-200 Coins\n Cooldown: 4 Stunden",
            inline=False
        )
        embed.add_field(
            name="!beg",
            value="Bettle um bis zu 100 Coins (10% Chance auf Kritischen Erfolg!)\n Cooldown: 10 Minuten",
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
            title=" Casino & Glücksspiel",
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
            title="🎰 Blackjack",
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
            title="🎰 Blackjack",
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
    async def spin(self, interaction: discord.Interaction, button: Button):
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
    def __init__(self, bet: int, player_id: int, ctx):
        super().__init__(timeout=None)
        self.bet = bet
        self.player_id = player_id
        self.ctx = ctx
        self.message = None
        self.slots = SlotsGame()
        self.spinning = False
        
        # Animations-Frames
        self.symbols = list(self.slots.symbols.keys())
        self.current_frame = 0
    
    def get_random_reel(self) -> str:
        return " ".join(random.choices(self.symbols, k=3))
    
    @discord.ui.button(label="Drehen 🎰", style=discord.ButtonStyle.green)
    async def spin(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        if self.spinning:
            await interaction.response.send_message("Die Walzen drehen sich bereits!", ephemeral=True)
            return

        self.spinning = True
        button.disabled = True
        await interaction.response.defer()

        # Animation der sich drehenden Walzen
        for i in range(8):  # 8 Frames Animation
            speed = min(0.8, 0.2 + (i * 0.1))  # Wird langsamer
            
            reel1 = self.get_random_reel()
            reel2 = self.get_random_reel()
            reel3 = self.get_random_reel()
            
            display = (
                "╔══════ SLOTS ══════╗\n"
                f"║  {reel1}  ║\n"
                f"║➤ {reel2}  ║ ← \n"
                f"║  {reel3}  ║\n"
                "╚══════════════════╝"
            )
            
            embed = discord.Embed(
                title="🎰 Spielautomat",
                description=display,
                color=discord.Color.gold()
            )
            embed.add_field(
                name="💰 Einsatz",
                value=f"**{self.bet}** Coins",
                inline=False
            )
            await self.message.edit(embed=embed, view=self)
            await asyncio.sleep(speed)

        # Endergebnis
        result = self.slots.spin()
        multiplier, combo_text = self.slots.get_win_multiplier(result)
        winnings = int(self.bet * multiplier)
        
        # Finale Animation
        display = (
            "╔══════ SLOTS ══════╗\n"
            f"║  {' '.join(self.get_random_reel())}  ║\n"
            f"║➤ {' '.join(result)}  ║ ← \n"
            f"║  {' '.join(self.get_random_reel())}  ║\n"
            "╚══════════════════╝"
        )
        
        description = (
            f"{display}\n\n"
            f"**{combo_text}**\n"
            f"{'🎉 Gewonnen!' if multiplier > 0 else '😢 Verloren!'}\n"
            f"Multiplikator: **{multiplier}x**\n"
            f"{'Gewinn' if multiplier > 0 else 'Verlust'}: **{abs(winnings - self.bet)}** Coins"
        )
        
        embed = discord.Embed(
            title="🎰 Spielautomat - Ergebnis",
            description=description,
            color=discord.Color.green() if multiplier > 0 else discord.Color.red()
        )
        
        # Aktualisiere Coins
        if multiplier > 0:
            update_coins(self.player_id, winnings)
        
        self.clear_items()
        await self.message.edit(embed=embed, view=self)

    async def start(self):
        # Zeige initiales Display
        display = (
            "╔══════ SLOTS ══════╗\n"
            "║  🎰 🎰 🎰  ║\n"
            "║➤ 🎯 🎯 🎯  ║ ← \n"
            "║  🎰 🎰 🎰  ║\n"
            "╚══════════════════╝"
        )
        
        embed = discord.Embed(
            title="🎰 Spielautomat",
            description=f"{display}\n\n"
                      "**Gewinnkombinationen:**\n"
                      "3x 💎 = 50.0x\n"
                      "3x 7️⃣ = 20.0x\n"
                      "3x 🍀 = 10.0x\n"
                      "3x ⭐ = 5.0x\n"
                      "3x 🔔 = 3.0x\n"
                      "3x 🍒 = 2.0x\n"
                      "3x 🍋 = 1.5x\n\n"
                      "2 gleiche Symbole = 0.5x des normalen Gewinns",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="💰 Einsatz",
            value=f"**{self.bet}** Coins",
            inline=False
        )
        self.message = await self.ctx.send(embed=embed, view=self)

@bot.command()
async def slots(ctx, bet: int = None):
    if not bet:
        embed = discord.Embed(
            title="🎰 Spielautomat",
            description="Drehe am einarmigen Banditen!\n\n"
                      "**Gewinnkombinationen:**\n"
                      "• 3x 💎 = 50.0x\n"
                      "• 3x 7️⃣ = 20.0x\n"
                      "• 3x 🍀 = 10.0x\n"
                      "• 3x ⭐ = 5.0x\n"
                      "• 3x 🔔 = 3.0x\n"
                      "• 3x 🍒 = 2.0x\n"
                      "• 3x 🍋 = 1.5x\n"
                      "• 2 gleiche = 0.5x des normalen Gewinns\n\n"
                      "**Verwendung:**\n"
                      "`!slots <einsatz>`",
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
    view = SlotsView(bet, ctx.author.id, ctx)
    await view.start()

# Pferderennen Command
@bot.command()
async def horserace(ctx, bet_amount: int = None, horse_number: str = None):
    if not bet_amount or not horse_number or horse_number not in "12345":
        embed = discord.Embed(
            title=" Pferderennen",
            description="Wette auf dein Lieblingspferd!\n\n"
                      "**Verfügbare Pferde:**\n"
                      "1. Blitz  (Sehr schnell)\n"
                      "2. Thunder  (Schnell)\n"
                      "3. Star  (Normal)\n"
                      "4. Lucky  (Langsam, aber glücklich)\n"
                      "5. Rainbow  (Langsam, hoher Gewinn)\n\n"
                      "**Verwendung:**\n"
                      "`!horserace <einsatz> <pferd-nummer>`\n\n"
                      "**Gewinnchancen:**\n"
                      "Je langsamer das Pferd, desto höher der Gewinn!",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    bet_amount = int(bet_amount)
    if bet_amount < 50:
        await ctx.send(" Minimaleinsatz ist 50 Coins!")
        return

    user_coins = get_coins(ctx.author.id)
    if user_coins < bet_amount:
        await ctx.send(" Du hast nicht genug Coins für diese Wette!")
        return

    # Starte neues Rennen wenn keins läuft
    if ctx.channel.id not in bot.horse_races or not bot.horse_races[ctx.channel.id].running:
        bot.horse_races[ctx.channel.id] = HorseRace()
        race = bot.horse_races[ctx.channel.id]
        race.running = True
        
        # Speichere Wette
        race_id = f"{ctx.channel.id}-{int(time.time())}"
        with sqlite3.connect(bot.db_path) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO horse_bets (race_id, user_id, horse_id, amount) VALUES (?, ?, ?, ?)',
                     (race_id, ctx.author.id, horse_number, bet_amount))
            conn.commit()

        # Ziehe Einsatz ab
        update_coins(ctx.author.id, -bet_amount)

        # Sende Start-Nachricht
        embed = discord.Embed(
            title=" Pferderennen startet!",
            description=f"{ctx.author.mention} wettet **{bet_amount}** Coins auf {race.horses[horse_number]['name']}!\n\n"
                      f"Das Rennen beginnt in 5 Sekunden...",
            color=discord.Color.blue()
        )
        start_msg = await ctx.send(embed=embed)
        await asyncio.sleep(5)

        # Rennen-Animation
        race_msg = None
        while race.running:
            if race.move_horses():
                embed = discord.Embed(
                    title=" Pferderennen",
                    description=race.get_track_display(),
                    color=discord.Color.blue()
                )
                if race_msg:
                    await race_msg.edit(embed=embed)
                else:
                    race_msg = await ctx.send(embed=embed)
                await asyncio.sleep(1)

        # Gewinner verkünden
        multiplier = {"1": 1.5, "2": 2.0, "3": 2.5, "4": 3.0, "5": 4.0}
        winner_horse_id = next(k for k, v in race.horses.items() if v["name"] == race.winner)
        
        # Hole alle Wetten für dieses Rennen
        with sqlite3.connect(bot.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT user_id, horse_id, amount FROM horse_bets WHERE race_id = ?', (race_id,))
            bets = c.fetchall()

        # Verarbeite Gewinne
        winners_text = ""
        for user_id, bet_horse_id, amount in bets:
            bettor = ctx.guild.get_member(user_id)
            if bet_horse_id == winner_horse_id:
                winnings = int(amount * multiplier[bet_horse_id])
                update_coins(user_id, winnings)
                winners_text += f" {bettor.mention} gewinnt **{winnings}** Coins!\n"
            else:
                winners_text += f" {bettor.mention} verliert **{amount}** Coins!\n"

        embed = discord.Embed(
            title=f" {race.winner} gewinnt das Rennen!",
            description=f"{race.get_track_display()}\n\n"
                      f"**Ergebnisse:**\n{winners_text}",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        
        # Reset für nächstes Rennen
        race.reset()
    else:
        await ctx.send(" Es läuft bereits ein Rennen in diesem Channel!")

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
    def __init__(self, bet: int, player_id: int, ctx):
        super().__init__(timeout=None)
        self.bet = bet
        self.player_id = player_id
        self.ctx = ctx
        self.message = None
        self.roulette = RouletteGame()
        self.spinning = False
        self.bet_type = None
        self.bet_value = None
        
        # Füge Wett-Buttons hinzu
        self.add_bet_buttons()
    
    def add_bet_buttons(self):
        # Erste Reihe: Farben
        self.add_item(Button(label="Rot ", custom_id="color_red", style=discord.ButtonStyle.red))
        self.add_item(Button(label="Schwarz ", custom_id="color_black", style=discord.ButtonStyle.gray))
        
        # Zweite Reihe: Gerade/Ungerade und Hälften
        self.add_item(Button(label="Gerade 2", custom_id="even_odd_even", style=discord.ButtonStyle.blurple))
        self.add_item(Button(label="Ungerade 1", custom_id="even_odd_odd", style=discord.ButtonStyle.blurple))
        self.add_item(Button(label="1-18", custom_id="half_first", style=discord.ButtonStyle.gray))
        self.add_item(Button(label="19-36", custom_id="half_second", style=discord.ButtonStyle.gray))
        
        # Dritte Reihe: Dutzende
        self.add_item(Button(label="1-12", custom_id="dozen_0", style=discord.ButtonStyle.green))
        self.add_item(Button(label="13-24", custom_id="dozen_1", style=discord.ButtonStyle.green))
        self.add_item(Button(label="25-36", custom_id="dozen_2", style=discord.ButtonStyle.green))
    
    async def update_message(self):
        wheel_display = (
            " ROULETTE \n"
            "╔════════════════╗\n"
            "║ 00  03  06 ║\n"
            "║ 27  30  33 ║\n"
            "║ 02  05  08 ║\n"
            "║    ...mehr...   ║\n"
            "╚════════════════╝"
        )
        
        embed = discord.Embed(
            title=" ROULETTE",
            description=f"{wheel_display}\n\n"
                      "**Wettmöglichkeiten:**\n"
                      "• Rot/Schwarz (2x)\n"
                      "• Gerade/Ungerade (2x)\n"
                      "• 1-18/19-36 (2x)\n"
                      "• Dutzend (3x)\n"
                      "• Einzelne Zahl (35x)",
            color=discord.Color.gold()
        )
        embed.add_field(
            name=" Einsatz",
            value=f"**{self.bet}** Coins",
            inline=False
        )
        
        if not self.message:
            self.message = await self.ctx.send(embed=embed, view=self)
        else:
            await self.message.edit(embed=embed, view=self)
    
    async def spin_animation(self):
        frames = []
        # Generiere 8 zufällige Frames für die Animation
        for _ in range(8):
            numbers = [self.roulette.get_number_display(self.roulette.spin()) for _ in range(6)]
            frame = (
                " ROULETTE \n"
                "╔════════════════╗\n"
                f"║ {numbers[0]} {numbers[1]} {numbers[2]} ║\n"
                f"║ {numbers[3]} {numbers[4]} {numbers[5]} ║\n"
                "║     ⬇️ ⬇️ ⬇️     ║\n"
                "╚════════════════╝"
            )
            frames.append(frame)
        
        # Zeige Animation
        for i in range(len(frames)):
            speed = min(1.0, 0.2 + (i * 0.1))
            embed = discord.Embed(
                title=" ROULETTE - Kugel rollt...",
                description=frames[i],
                color=discord.Color.gold()
            )
            await self.message.edit(embed=embed)
            await asyncio.sleep(speed)
    
    async def handle_bet(self, interaction: discord.Interaction):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        if self.spinning:
            await interaction.response.send_message("Das Rad dreht sich bereits!", ephemeral=True)
            return

        # Parse bet type and value from button custom_id
        bet_type, bet_value = interaction.custom_id.split("_")
        self.bet_type = bet_type
        self.bet_value = bet_value
        
        self.spinning = True
        for item in self.children:
            item.disabled = True
        await interaction.response.defer()
        
        # Animation
        await self.spin_animation()
        
        # Ergebnis
        result = self.roulette.spin()
        won, multiplier = self.roulette.check_bet(bet_type, bet_value, result)
        winnings = int(self.bet * multiplier) if won else 0
        
        # Ergebnis anzeigen
        result_display = (
            " ROULETTE \n"
            "╔════════════════╗\n"
            "║                ║\n"
            f"║      {self.roulette.get_number_display(result)}      ║\n"
            "║                ║\n"
            "╚════════════════╝"
        )
        
        description = (
            f"{result_display}\n\n"
            f"Kugel landet auf: **{self.roulette.get_number_display(result)}**\n"
            f"Deine Wette: **{self.get_bet_description()}**\n\n"
            f"{' Gewonnen!' if won else ' Verloren!'}\n"
            f"{'Gewinn' if won else 'Verlust'}: **{abs(winnings - self.bet)}** Coins"
        )
        
        embed = discord.Embed(
            title=" ROULETTE - Ergebnis",
            description=description,
            color=discord.Color.green() if won else discord.Color.red()
        )
        
        # Aktualisiere Coins
        if won:
            update_coins(self.player_id, winnings)
        
        self.clear_items()
        await self.message.edit(embed=embed, view=self)
    
    def get_bet_description(self) -> str:
        if self.bet_type == "color":
            return "Rot" if self.bet_value == "red" else "Schwarz"
        elif self.bet_type == "even_odd":
            return "Gerade" if self.bet_value == "even" else "Ungerade"
        elif self.bet_type == "half":
            return "1-18" if self.bet_value == "first" else "19-36"
        elif self.bet_type == "dozen":
            dozens = ["1-12", "13-24", "25-36"]
            return dozens[int(self.bet_value)]
        return "Unbekannt"
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.custom_id:
            await self.handle_bet(interaction)
        return True

    async def start(self):
        await self.update_message()

@bot.command()
async def roulette(ctx, bet: int = None):
    if not bet:
        embed = discord.Embed(
            title=" ROULETTE",
            description="Setze auf eine Zahl oder eine Farbe!\n\n"
                      "**Wettmöglichkeiten:**\n"
                      "• Rot/Schwarz (2x)\n"
                      "• Gerade/Ungerade (2x)\n"
                      "• 1-18/19-36 (2x)\n"
                      "• Dutzend (3x)\n"
                      "• Einzelne Zahl (35x)\n\n"
                      "**Verwendung:**\n"
                      "`!roulette <einsatz>`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet < 50:
        await ctx.send(" Der Minimaleinsatz ist 50 Coins!")
        return

    user_coins = get_coins(ctx.author.id)
    if user_coins < bet:
        await ctx.send(" Du hast nicht genug Coins!")
        return

    # Ziehe Einsatz ab
    update_coins(ctx.author.id, -bet)

    # Starte Spiel
    view = RouletteView(bet, ctx.author.id, ctx)
    await view.start()

# Wenn die Datei direkt ausgeführt wird
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
