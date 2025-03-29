import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from datetime import timedelta

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()
TOKEN = os.getenv('TOKEN')

if TOKEN is None:
    print("Fehler: Der Token wurde nicht geladen!")

# Prefix für die Befehle
PREFIX = '!'

# Intents setzen
intents = discord.Intents.default()
intents.members = True  
intents.message_content = True  

# Initialisiere den Bot
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# ===================== TIMEOUT & UNTIMEOUT =====================
@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, minutes: int):
    try:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason="Timeout command")
        await ctx.send(f"🔒 {member.mention} wurde für {minutes} Minuten getimed out.")
    except Exception as e:
        await ctx.send(f"❌ Fehler: {e}")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member):
    try:
        await member.timeout(None, reason="Untimeout command")
        await ctx.send(f"✅ {member.mention} wurde enttimed out.")
    except Exception as e:
        await ctx.send(f"❌ Fehler: {e}")

# ===================== ONLINE CHECK =====================
@bot.command()
async def online(ctx):
    await ctx.send("✨ **Ich bin online!** 🚀")

# ===================== INVITE SYSTEM =====================
@bot.command()
async def setupinvite(ctx):
    invite_link = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=8))
    await ctx.send(f"📩 **Hier ist der Invite-Link:**\n{invite_link}")

@bot.event
async def on_member_join(member):
    if member.guild.system_channel:
        await member.guild.system_channel.send(f"🎉 {member.mention} ist dem Server beigetreten!")

@bot.event
async def on_member_remove(member):
    if member.guild.system_channel:
        await member.guild.system_channel.send(f"😢 {member.mention} hat den Server verlassen.")

# ===================== TICKET SYSTEM =====================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketButton())

class TicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🎟️ Ticket erstellen", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")
        
        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await channel.set_permissions(guild.default_role, read_messages=False)

        await channel.send(
            f"{interaction.user.mention}, dein Ticket wurde erstellt! ✅\nEin Support-Mitarbeiter wird sich bald melden.",
            view=CloseTicketView()
        )
        
        await interaction.response.send_message(f"🎟️ Dein Ticket wurde erstellt: {channel.mention}", ephemeral=True)

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(CloseTicketButton())

class CloseTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🔒 Ticket schließen", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        await channel.send("🔒 **Dieses Ticket wurde geschlossen.**", view=DeleteTicketView())
        await interaction.response.defer()

class DeleteTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DeleteTicketButton())

class DeleteTicketButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🗑️ Ticket löschen", style=discord.ButtonStyle.gray)

    async def callback(self, interaction: discord.Interaction):
        channel = interaction.channel
        await channel.send("🗑️ **Dieses Ticket wird in 5 Sekunden gelöscht...**")
        await interaction.response.defer()
        await asyncio.sleep(5)
        await channel.delete()

@bot.command()
@commands.has_permissions(moderate_members=True)
async def ticket(ctx):
    await ctx.send("🎟️ **Klicke auf den Button, um ein Ticket zu erstellen!**", view=TicketView())

# ===================== KICK COMMAND =====================
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="Kein Grund angegeben."):
    if member == ctx.author:
        await ctx.send("❌ Du kannst dich nicht selbst kicken!")
        return

    try:
        await member.kick(reason=reason)
        await ctx.send(f"✅ {member.mention} wurde gekickt. Grund: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ Ich habe nicht die Berechtigung, diesen Benutzer zu kicken!")
    except Exception as e:
        await ctx.send(f"❌ Fehler: {e}")

# ===================== HELP COMMAND =====================
@bot.command()
async def hilfe(ctx):
    embed = discord.Embed(title="📜 Befehlsübersicht", description="Hier sind die verfügbaren Befehle:", color=discord.Color.blue())
    embed.add_field(name="🔹 **Moderation**", value="⚠️ Diese Befehle sind nur für Moderatoren!", inline=False)
    embed.add_field(name="`!timeout @User Minuten`", value="Setzt einen Timeout für den Benutzer.", inline=True)
    embed.add_field(name="`!untimeout @User`", value="Hebt den Timeout auf.", inline=True)
    embed.add_field(name="`!kick @User Grund`", value="Kickt den Benutzer vom Server.", inline=True)
    embed.add_field(name="🔹 **Allgemeine Befehle**", value="Diese Befehle kann jeder nutzen.", inline=False)
    embed.add_field(name="`!online`", value="Zeigt an, dass der Bot online ist.", inline=True)
    embed.add_field(name="`!setupinvite`", value="Erstellt einen Invite-Link für den Bot.", inline=True)
    embed.add_field(name="`!invite_tracker`", value="Aktiviert den Invite-Tracker.", inline=True)
    
    embed.add_field(name="🎟️ **Ticketsystem**", value="Unterstützung per Ticket.", inline=False)
    embed.add_field(name="`!ticket`", value="Erstellt ein Support-Ticket.", inline=True)
    
    embed.set_footer(text="⚡ Mehr Funktionen folgen bald!")
    await ctx.send(embed=embed)

# ===================== BOT START =====================
@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

bot.run(TOKEN)
