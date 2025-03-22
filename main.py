import os
import discord
from discord.ext import commands
import random
import datetime
import sqlite3
from dotenv import load_dotenv
from typing import Optional, List, Dict
import asyncio
from discord.ui import Button, View
import time
from discord import app_commands

# Lade Umgebungsvariablen
load_dotenv()

# Bot-Konfiguration
intents = discord.Intents.all()
intents.members = True
intents.message_content = True

class HorseRace:
    def __init__(self):
        self.horses = {
            "1": {"name": "Blitz", "emoji": "🐎", "position": 0, "speed": 1.2, "place": None},
            "2": {"name": "Thunder", "emoji": "🦄", "position": 0, "speed": 1.1, "place": None},
            "3": {"name": "Star", "emoji": "🏇", "position": 0, "speed": 1.0, "place": None},
            "4": {"name": "Lucky", "emoji": "🐴", "position": 0, "speed": 0.9, "place": None},
            "5": {"name": "Rainbow", "emoji": "🦓", "position": 0, "speed": 0.8, "place": None}
        }
        self.track_length = 15  # Kürzere Rennstrecke
        self.running = False
        self.finished_horses = 0
        
    def reset(self):
        for horse in self.horses.values():
            horse["position"] = 0
            horse["place"] = None
        self.running = False
        self.finished_horses = 0
        
    def move_horses(self):
        if not self.running:
            return False
            
        moved = False
        for horse in self.horses.values():
            if horse["place"] is not None:
                continue
                
            if random.random() < horse["speed"] * 0.3:
                horse["position"] += random.randint(1, 3)
                moved = True
                
                if horse["position"] >= self.track_length:
                    self.finished_horses += 1
                    horse["place"] = self.finished_horses
                    if self.finished_horses >= 3:  # Rennen endet nach 3 Pferden
                        self.running = False
                        return False
        return moved
        
    def get_track_display(self):
        display = ["🎪 **PFERDERENNEN** 🎪\n\n"]
        
        # Füge Legende hinzu
        display.append("**Pferde und ihre Chancen:**\n")
        for num, horse in self.horses.items():
            medal = ""
            if horse["place"]:
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(horse["place"], "")
            display.append(f"`{num}.` {horse['name']} {horse['emoji']} - {horse['speed']}x Speed {medal}\n")
        
        display.append("\n**🏁 RENNSTRECKE:**\n")
        display.append("```")
        
        # Zeige Rennstrecke für jedes Pferd
        for num, horse in self.horses.items():
            pos = horse["position"]
            
            # Erstelle die Rennstrecke
            track = "." * self.track_length
            if pos > 0:
                track = "." * (pos - 1) + horse["emoji"] + "." * (self.track_length - pos)
            else:
                track = horse["emoji"] + "." * (self.track_length - 1)
            
            # Füge Start- und Ziellinie hinzu
            track = "🏁" + track + "🏁"
            
            # Füge Pferdenummer und Name hinzu
            place_str = f" [{horse['place']}.]" if horse["place"] else ""
            display.append(f"{num}. {horse['name']:<8}{track}{place_str}\n")
        
        display.append("```")
        return "".join(display)

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
            title="🐎 Pferderennen",
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
            title="🐎 Pferderennen startet!",
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
                    title="🐎 Pferderennen",
                    description=race.get_track_display(),
                    color=discord.Color.blue()
                )
                if race_msg:
                    await race_msg.edit(embed=embed)
                else:
                    race_msg = await ctx.send(embed=embed)
                await asyncio.sleep(0.5)

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
            name="💰 Einsatz",
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
        if interaction.custom_id:
            await self.handle_bet(interaction)
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.custom_id:
            await self.handle_bet(interaction)
        return True

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
        winnings = int(self.bet * multiplier)
        
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

@bot.command()
async def coinflip(ctx, bet_amount: int = None, number: int = None):
    if not bet_amount or not number or number not in range(1, 7):
        embed = discord.Embed(
            title="🎰 Coinflip",
            description="Wirf eine Münze und wette auf Kopf oder Zahl!\n\n"
                      "**Regeln:**\n"
                      "• Wähle zwischen Kopf und Zahl\n"
                      "• Gewinn = 2x Einsatz\n"
                      "• 50/50 Gewinnchance\n\n"
                      "**Verwendung:**\n"
                      "`!coinflip <einsatz>`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 50:
        await ctx.send("❌ Der Minimaleinsatz ist 50 Coins!")
        return

    user_coins = get_coins(ctx.author.id)
    if user_coins < bet_amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    # Ziehe Einsatz ab
    update_coins(ctx.author.id, -bet_amount)

    # Starte Spiel
    view = CoinflipView(bet_amount, ctx.author.id, ctx)
    await view.start()

class CoinflipView(View):
    def __init__(self, bet: int, player_id: int, ctx):
        super().__init__(timeout=None)
        self.bet = bet
        self.player_id = player_id
        self.ctx = ctx
        self.message = None
        self.flipping = False
        
        # Animations-Frames für die Münze
        self.frames = [
            "  _______________\n /      KOPF     \\ \n|    ◕ 👑 ◕     |\n \\_______________/",
            "      ▃▃▃▃▃\n    ▃╱     ╲▃\n   ╱         ╲\n   ╲         ╱\n    ▔╲     ╱▔\n      ▔▔▔▔",
            "  _______________\n /      ZAHL     \\ \n|       💫       |\n \\_______________/",
            "    ╱▔▔▔▔╲\n  ╱         ╲\n ╱           ╲\n  ╲           ╱\n   ╲         ╱\n    ╲▁▁▁▁▁╱"
        ]
    
    @discord.ui.button(label="Kopf 👑", style=discord.ButtonStyle.blurple, custom_id="heads")
    async def heads(self, interaction: discord.Interaction, button: Button):
        await self.flip(interaction, "heads")
    
    @discord.ui.button(label="Zahl 💫", style=discord.ButtonStyle.gray, custom_id="tails")
    async def tails(self, interaction: discord.Interaction, button: Button):
        await self.flip(interaction, "tails")
    
    async def flip(self, interaction: discord.Interaction, choice: str):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("Das ist nicht dein Spiel!", ephemeral=True)
            return
        
        if self.flipping:
            await interaction.response.send_message("Die Münze wird bereits geworfen!", ephemeral=True)
            return

        self.flipping = True
        for item in self.children:
            item.disabled = True
        await interaction.response.defer()

        # Animation der Münze
        for i in range(8):  # 8 Frames Animation
            speed = min(0.8, 0.2 + (i * 0.1))  # Wird langsamer
            frame = self.frames[i % len(self.frames)]
            
            embed = discord.Embed(
                title="🎰 Coinflip",
                description=f"```{frame}```",
                color=discord.Color.gold()
            )
            embed.add_field(
                name="💰 Einsatz",
                value=f"**{self.bet}** Coins",
                inline=True
            )
            embed.add_field(
                name="🎯 Deine Wahl",
                value=f"**{'Kopf' if choice == 'heads' else 'Zahl'}**",
                inline=True
            )
            await self.message.edit(embed=embed, view=self)
            await asyncio.sleep(speed)
        
        # Ergebnis
        result = random.choice(["heads", "tails"])
        won = choice == result
        winnings = self.bet * 2 if won else 0
        
        # Zeige Endergebnis
        final_frame = self.frames[0] if result == "heads" else self.frames[2]
        description = (
            f"```{final_frame}```\n\n"
            f"Ergebnis: **{'Kopf' if result == 'heads' else 'Zahl'}**\n"
            f"Deine Wahl: **{'Kopf' if choice == 'heads' else 'Zahl'}**\n\n"
            f"{'🎉 Gewonnen!' if won else '😢 Verloren!'}\n"
            f"{'Gewinn' if won else 'Verlust'}: **{abs(winnings - self.bet)}** Coins"
        )
        
        embed = discord.Embed(
            title="🎰 Coinflip - Ergebnis",
            description=description,
            color=discord.Color.green() if won else discord.Color.red()
        )
        
        # Aktualisiere Coins
        if won:
            update_coins(self.player_id, winnings)
        
        self.clear_items()
        await self.message.edit(embed=embed, view=self)
    
    async def start(self):
        embed = discord.Embed(
            title="🎰 Coinflip",
            description=f"```{self.frames[0]}```\n\n"
                      "Wähle **Kopf** oder **Zahl**!\n"
                      "• Gewinn = 2x Einsatz\n"
                      "• 50/50 Chance",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="💰 Einsatz",
            value=f"**{self.bet}** Coins",
            inline=False
        )
        self.message = await self.ctx.send(embed=embed, view=self)

@bot.command()
async def scratch(ctx, bet_amount: int = None):
    if not bet_amount:
        embed = discord.Embed(
            title="🎰 Rubbellos",
            description="Rubbel drei gleiche Symbole für einen Gewinn!\n\n"
                      "**Gewinne:**\n"
                      "🍒 Cherry: 1.5x\n"
                      "🍊 Orange: 2x\n"
                      "🍇 Grape: 3x\n"
                      "💎 Diamond: 5x\n\n"
                      "**Verwendung:**\n"
                      "`!scratch <einsatz>`\n"
                      "Beispiel: `!scratch 100`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 50:
        await ctx.send("❌ Der Minimaleinsatz ist 50 Coins!")
        return

    user_coins = get_coins(ctx.author.id)
    if user_coins < bet_amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    update_coins(ctx.author.id, -bet_amount)

    # Symbole und ihre Multiplikatoren
    symbols = {
        "🍒": 1.5,  # Cherry
        "🍊": 2.0,  # Orange
        "🍇": 3.0,  # Grape
        "💎": 5.0   # Diamond
    }

    # Gewichtete Wahrscheinlichkeiten (seltener = wertvoller)
    weights = [0.4, 0.3, 0.2, 0.1]
    
    # Generiere 9 zufällige Symbole
    grid = []
    for _ in range(9):
        symbol = random.choices(list(symbols.keys()), weights=weights)[0]
        grid.append(symbol)

    # Prüfe auf Gewinnlinien (horizontal, vertikal, diagonal)
    winning_lines = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # Horizontal
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # Vertikal
        [0, 4, 8], [2, 4, 6]              # Diagonal
    ]

    won = False
    multiplier = 0
    winning_symbol = None
    
    for line in winning_lines:
        if grid[line[0]] == grid[line[1]] == grid[line[2]]:
            won = True
            winning_symbol = grid[line[0]]
            multiplier = symbols[winning_symbol]
            break

    # Erstelle das Rubbellos-Display
    display = "```\n"
    for i in range(0, 9, 3):
        display += f"│ {grid[i]} │ {grid[i+1]} │ {grid[i+2]} │\n"
    display += "```"

    if won:
        winnings = int(bet_amount * multiplier)
        update_coins(ctx.author.id, winnings)
        
        embed = discord.Embed(
            title="🎉 Gewonnen!",
            description=f"Du hast **{winnings}** Coins gewonnen! (x{multiplier})\n\n{display}",
            color=discord.Color.green()
        )
    else:
        embed = discord.Embed(
            title="😢 Verloren!",
            description=f"Leider keine Gewinnlinie gefunden!\n\n{display}",
            color=discord.Color.red()
        )

    embed.set_footer(text="Viel Glück beim nächsten Mal! 🍀")
    await ctx.send(embed=embed)

@bot.command()
async def dice(ctx, bet_amount: int = None, number: int = None):
    if not bet_amount or not number or number not in range(1, 7):
        embed = discord.Embed(
            title="🎲 Würfelspiel",
            description="Wette auf eine Zahl zwischen 1-6!\n\n"
                      "**Gewinne:**\n"
                      "• Richtige Zahl: 5x Einsatz\n"
                      "• ±1 daneben: 2x Einsatz\n\n"
                      "**Verwendung:**\n"
                      "`!dice <einsatz> <zahl>`\n"
                      "Beispiel: `!dice 100 6`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 50:
        await ctx.send("❌ Der Minimaleinsatz ist 50 Coins!")
        return

    user_coins = get_coins(ctx.author.id)
    if user_coins < bet_amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    update_coins(ctx.author.id, -bet_amount)

    # Würfle eine Zahl
    dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    result = random.randint(1, 6)
    
    # Bestimme den Gewinn
    if result == number:
        multiplier = 5
        title = "🎉 Volltreffer!"
        color = discord.Color.green()
    elif abs(result - number) == 1:
        multiplier = 2
        title = "🎯 Fast getroffen!"
        color = discord.Color.blue()
    else:
        multiplier = 0
        title = "😢 Daneben!"
        color = discord.Color.red()

    description = f"Du hast auf **{number}** gewettet.\n"
    description += f"Gewürfelt wurde: {dice_faces[result-1]} **({result})**\n\n"

    if multiplier > 0:
        winnings = int(bet_amount * multiplier)
        update_coins(ctx.author.id, winnings)
        description += f"Du gewinnst **{winnings}** Coins! (x{multiplier})"
    else:
        description += "Du verlierst deinen Einsatz!"

    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="Viel Glück beim nächsten Mal! 🎲")
    await ctx.send(embed=embed)

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

class YahtzeeView(discord.ui.View):
    def __init__(self, ctx, bet_amount):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet_amount = bet_amount
        self.game = YahtzeeGame()
        self.message = None
        self.keep_dice = [False] * 5
        
    async def start(self):
        self.game.roll_dice()
        embed = self.get_game_embed()
        self.message = await self.ctx.send(embed=embed, view=self)
        
    def get_game_embed(self):
        dice_faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        dice_display = " ".join([dice_faces[d-1] for d in self.game.dice])
        keep_display = " ".join(["🔒" if k else "🔓" for k in self.keep_dice])
        
        embed = discord.Embed(
            title="🎲 Yahtzee",
            description=f"**Würfel:**\n{dice_display}\n{keep_display}\n\n"
                      f"**Würfe übrig:** {self.game.rolls_left}\n"
                      f"**Aktueller Wert:** {self.game.get_score()} Punkte",
            color=discord.Color.blue()
        )
        
        if self.game.rolls_left == 0:
            score = self.game.get_score()
            multiplier = score / 10  # Jeder Punkt ist 0.1x Multiplikator
            winnings = int(self.bet_amount * multiplier)
            
            if winnings > self.bet_amount:
                embed.color = discord.Color.green()
                embed.add_field(
                    name="🎉 Gewonnen!",
                    value=f"**{winnings}** Coins (x{multiplier:.1f})",
                    inline=False
                )
            else:
                embed.color = discord.Color.red()
                embed.add_field(
                    name="😢 Verloren!",
                    value=f"Einsatz verloren!",
                    inline=False
                )
                
            self.disable_all_buttons()
            
        return embed
        
    def disable_all_buttons(self):
        for item in self.children:
            item.disabled = True
            
    @discord.ui.button(label="Würfeln", style=discord.ButtonStyle.green, emoji="🎲")
    async def roll_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return
            
        keep_indices = [i for i, k in enumerate(self.keep_dice) if k]
        self.game.roll_dice(keep_indices)
        
        if self.game.rolls_left == 0:
            score = self.game.get_score()
            multiplier = score / 10
            winnings = int(self.bet_amount * multiplier)
            
            if winnings > self.bet_amount:
                update_coins(self.ctx.author.id, winnings)
            
        await interaction.response.edit_message(embed=self.get_game_embed(), view=self)

    @discord.ui.button(label="Würfel behalten", style=discord.ButtonStyle.blurple, emoji="🔒")
    async def toggle_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            return
            
        # Modal zum Auswählen der Würfel
        modal = ToggleDiceModal(self)
        await interaction.response.send_modal(modal)

class ToggleDiceModal(discord.ui.Modal, title="Würfel behalten"):
    def __init__(self, view: YahtzeeView):
        super().__init__()
        self.view = view
        
        self.dice_input = discord.ui.TextInput(
            label="Würfel (1-5, mit Leerzeichen getrennt)",
            placeholder="z.B. '1 3 5' für den ersten, dritten und fünften Würfel",
            required=True,
            max_length=9
        )
        self.add_item(self.dice_input)
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Setze alle Würfel zurück
            self.view.keep_dice = [False] * 5
            
            # Markiere ausgewählte Würfel
            dice_numbers = [int(x) for x in self.dice_input.value.split()]
            for num in dice_numbers:
                if 1 <= num <= 5:
                    self.view.keep_dice[num-1] = True
                    
            await interaction.response.edit_message(embed=self.view.get_game_embed(), view=self.view)
            
        except ValueError:
            await interaction.response.send_message("❌ Ungültige Eingabe! Bitte gib die Würfelnummern (1-5) mit Leerzeichen getrennt ein.", ephemeral=True)

@bot.command()
async def yahtzee(ctx, bet_amount: int = None):
    if not bet_amount:
        embed = discord.Embed(
            title="🎲 Yahtzee",
            description="Würfle die besten Kombinationen!\n\n"
                      "**Kombinationen & Multiplikatoren:**\n"
                      "• Yahtzee (5 gleiche): x5.0\n"
                      "• Vierlinge: x4.0\n"
                      "• Full House: x2.5\n"
                      "• Große Straße: x3.0\n"
                      "• Kleine Straße: x2.0\n"
                      "• Drilling: x1.5\n"
                      "• Zwei Paare: x1.0\n"
                      "• Ein Paar: x0.5\n\n"
                      "**Verwendung:**\n"
                      "`!yahtzee <einsatz>`\n"
                      "Beispiel: `!yahtzee 100`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet_amount < 50:
        await ctx.send("❌ Der Minimaleinsatz ist 50 Coins!")
        return

    user_coins = get_coins(ctx.author.id)
    if user_coins < bet_amount:
        await ctx.send("❌ Du hast nicht genug Coins!")
        return

    update_coins(ctx.author.id, -bet_amount)
    
    view = YahtzeeView(ctx, bet_amount)
    await view.start()

# Wenn die Datei direkt ausgeführt wird
if __name__ == "__main__":
    from server import keep_alive
    keep_alive()  # Startet den Webserver für 24/7 Uptime
    bot.run(os.getenv('DISCORD_TOKEN'))
