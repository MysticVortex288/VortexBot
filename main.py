import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
from dotenv import load_dotenv
import sqlite3
import random
import asyncio
from typing import Optional

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
        self.db_path = "economy.db"
        self.setup_database()

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
        return result[0] if result else 0

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
            await ctx.send(f"❌ Du hast deine tägliche Belohnung bereits abgeholt! Komm zurück um {next_reset.strftime('%H:%M')} Uhr!")
            return

    coins = random.randint(300, 500)
    update_coins(user_id, coins)
    update_last_used(user_id, 'daily')
    
    embed = discord.Embed(
        title="💰 Tägliche Belohnung!",
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
            await ctx.send(f"❌ Du musst noch {hours}h {minutes}m warten, bevor du wieder arbeiten kannst!")
            return

    coins = random.randint(100, 200)
    update_coins(user_id, coins)
    update_last_used(user_id, 'work')
    
    messages = [
        f"Du hast hart gearbeitet und **{coins}** Coins verdient! 💼",
        f"Dein Chef ist zufrieden und gibt dir **{coins}** Coins! 👔",
        f"Ein erfolgreicher Arbeitstag! Du erhältst **{coins}** Coins! 💪"
    ]
    
    embed = discord.Embed(
        title="💼 Arbeit",
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
            await ctx.send(f"❌ Du musst noch {minutes}m warten, bevor du wieder betteln kannst!")
            return

    is_crit = random.random() < 0.10  # 10% Chance auf Krit
    coins = random.randint(50, 100) if is_crit else random.randint(1, 50)
    update_coins(user_id, coins)
    update_last_used(user_id, 'beg')
    
    if is_crit:
        embed = discord.Embed(
            title="🌟 Kritischer Erfolg beim Betteln!",
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
            title="🙏 Betteln",
            description=random.choice(messages),
            color=discord.Color.greyple()
        )
    await ctx.send(embed=embed)

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
        description=f"{ctx.author.mention} hat {member.mention} **{amount}** Coins überwiesen!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
async def rob(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        await ctx.send("❌ Du kannst dich nicht selbst ausrauben!")
        return
    
    user_id = ctx.author.id
    last_used = get_last_used(user_id, 'rob')
    now = datetime.datetime.now()
    
    if last_used:
        cooldown = datetime.timedelta(hours=1)
        time_left = (last_used + cooldown) - now
        if time_left.total_seconds() > 0:
            minutes = int(time_left.total_seconds() // 60)
            await ctx.send(f"❌ Du musst noch {minutes}m warten, bevor du wieder jemanden ausrauben kannst!")
            return
    
    victim_coins = get_coins(member.id)
    if victim_coins < 50:
        await ctx.send(f"❌ {member.mention} hat zu wenig Coins zum Ausrauben!")
        return
    
    success = random.random() < 0.15  # 15% Erfolgschance
    update_last_used(user_id, 'rob')
    
    if success:
        stolen = random.randint(50, min(victim_coins, 500))
        update_coins(member.id, -stolen)
        update_coins(user_id, stolen)
        
        embed = discord.Embed(
            title="🦹 Erfolgreicher Raub!",
            description=f"Du hast {member.mention} **{stolen}** Coins gestohlen!",
            color=discord.Color.dark_red()
        )
    else:
        fine = random.randint(50, 200)
        update_coins(user_id, -fine)
        
        embed = discord.Embed(
            title="👮 Erwischt!",
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
        await ctx.send("❌ Noch keine Einträge im Leaderboard!")
        return
    
    embed = discord.Embed(
        title="🏆 Reichste Nutzer",
        color=discord.Color.gold()
    )
    
    for i, (user_id, coins) in enumerate(top_users, 1):
        member = ctx.guild.get_member(user_id)
        name = member.name if member else f"Unbekannt ({user_id})"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "👤")
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
        title=f"👮‍♂️ Moderation: {action}",
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
            title="❌ Du wurdest gekickt!",
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
        title="✅ Moderation ausgeführt",
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
            title="🔨 Du wurdest gebannt!",
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
        title="✅ Moderation ausgeführt",
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
        title="✅ Moderation ausgeführt",
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
            title="✅ Dein Timeout wurde aufgehoben!",
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
        title="✅ Moderation ausgeführt",
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

@online.error
async def online_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Du brauchst Administrator-Rechte um diesen Befehl zu nutzen!")

@bot.command()
async def help(ctx, category: str = None):
    if category is None:
        # Hauptmenü
        embed = discord.Embed(
            title="🤖 Bot Hilfe",
            description="Hier sind die verfügbaren Kategorien:\n\n"
                      "• `!help moderation` - Moderations- und Statusbefehle\n"
                      "• `!help economy` - Wirtschaftssystem und Befehle\n\n"
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
        # Economy-Hilfe
        embed = discord.Embed(
            title="💰 Wirtschaftssystem",
            description="Hier sind alle verfügbaren Economy-Befehle:",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="!daily",
            value="Erhalte täglich zwischen 300-500 Coins\n⏰ Cooldown: 24 Stunden (Reset um 1 Uhr nachts)",
            inline=False
        )
        embed.add_field(
            name="!work",
            value="Arbeite für 100-200 Coins\n⏰ Cooldown: 4 Stunden",
            inline=False
        )
        embed.add_field(
            name="!beg",
            value="Bettle um bis zu 100 Coins (10% Chance auf Kritischen Erfolg!)\n⏰ Cooldown: 10 Minuten",
            inline=False
        )
        embed.add_field(
            name="!pay @user <betrag>",
            value="Überweise einem anderen Nutzer Coins",
            inline=False
        )
        embed.add_field(
            name="!rob @user",
            value="Versuche einen anderen Nutzer auszurauben (15% Erfolgschance)\n⏰ Cooldown: 1 Stunde",
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
    
    await ctx.send(f"❌ Die Kategorie `{category}` wurde nicht gefunden. Benutze `!help` für eine Liste aller Kategorien.")

# Wenn die Datei direkt ausgeführt wird
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
