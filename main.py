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
                      "• `!help moderation` - Moderations- und Statusbefehle\n\n"
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
    
    await ctx.send(f"❌ Die Kategorie `{category}` wurde nicht gefunden. Benutze `!help` für eine Liste aller Kategorien.")

# Wenn die Datei direkt ausgeführt wird
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
