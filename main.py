from math import remainder
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from datetime import timedelta
import datetime


from requests import delete

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
# ===================== HELP COMMAND =====================
@bot.command()
async def hilfe(ctx):
    embed = discord.Embed(title="📜 Befehlsübersicht", description="Hier sind die verfügbaren Befehle:", color=discord.Color.blue())
    embed.add_field(name="🔹 **Moderation**", value="⚠️ Diese Befehle sind nur für Moderatoren!", inline=False)
    embed.add_field(name="!timeout @User Minuten", value="Setzt einen Timeout für den Benutzer.", inline=True)
    embed.add_field(name="!untimeout @User", value="Hebt den Timeout auf.", inline=True)
    embed.add_field(name="!kick @User Grund", value="Kickt den Benutzer vom Server.", inline=True)
    embed.add_field(name="🔹 **Allgemeine Befehle**", value="Diese Befehle kann jeder nutzen.", inline=False)
    embed.add_field(name="!online", value="Zeigt an, dass der Bot online ist.", inline=True)
    embed.add_field(name="!setupinvite", value="Erstellt einen Invite-Link für den Bot.", inline=True)
    embed.add_field(name="!invite_tracker", value="Aktiviert den Invite-Tracker.", inline=True)
    embed.add_field(name="🔹 **Counting Befehle**", value="Diese Befehle kann jeder nutzen.", inline=False)
    embed.add_field(name="!setupcounting #channel", value="Setzt den Counting-Channel.", inline=True)
    embed.add_field(name="!countingstop", value="Stoppt das Counting.", inline=True)
    embed.add_field(name="🎟️ **Ticketsystem**", value="Unterstützung per Ticket.", inline=False)
    embed.add_field(name="!ticket", value="Erstellt ein Ticket.", inline=True)
    embed.add_field(name="🔹 **Economy-Befehle**", value="Diese Befehle sind für Credits da.", inline=False)
    embed.add_field(name="!daily", value="Gibt dir jeden Tag 1000 Credits.", inline=True)

    # Hier fehlt das Senden des Embeds
    await ctx.send(embed=embed)

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
    await ctx.send("✨ **Ich bin online!** 🚀"
    "Was kann ich für dich tun mein Lieber:wink:")

# ===================== INVITE SYSTEM =====================
@bot.command()
async def setupinvite(ctx):
    invite_link = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=8))
    await ctx.send(f"📩 **Hier ist der Invite-Link:**\n{invite_link}")

@bot.event
async def on_member_join(member):
    # Begrüßungsnachricht senden
    if member.guild.system_channel:
        await member.guild.system_channel.send(f"🎉 {member.mention} ist dem Server beigetreten!")
        # Nachricht senden wenn jemand den Server verlässt
        @bot.event
        async def on_member_remove(member):
         if member.guild.system_channel:
          await member.guild.system_channel.send(f":wave: {member.mention} hat den Server verlassen!")
    # Rolle "Unverified" holen oder erstellen
    role = discord.utils.get(member.guild.roles, name="Unverified")
    if not role:
        role = await member.guild.create_role(name="Unverified", reason="Verifizierungsrolle für neue Mitglieder")

    # Rolle "Unverified" zuweisen, damit der User keine Nachrichten schreiben kann
    await member.add_roles(role)

    # Verifizierungsnachricht in DMs senden
    await member.send(
        f"Willkommen {member.mention}! Bitte verifiziere dich, indem du auf den Button unten klickst.\n\n"
        "Wenn du dich nicht verifizierst, kannst du keine Nachrichten im Server senden."
    )

    # Verifizierungsbutton hinzufügen
    view = discord.ui.View()
    button = discord.ui.Button(label="Verifizieren", style=discord.ButtonStyle.green)

    async def button_callback(interaction: discord.Interaction):
        if interaction.user == member:  # Sicherstellen, dass nur der Benutzer selbst den Button drückt
            # Rolle "Unverified" entfernen
            await member.remove_roles(role)
            # Bestätigung senden
            await interaction.response.send_message(f"Du bist jetzt verifiziert, {member.mention}!", ephemeral=True)
        else:
            await interaction.response.send_message("Du kannst diesen Button nur für dich selbst verwenden.", ephemeral=True)

    button.callback = button_callback
    view.add_item(button)

    # Verifizierungsbutton in der DM-Nachricht anhängen
    await member.send("Klicke den Button, um dich zu verifizieren!", view=view)

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

# ===================== COUNTING GAME =====================
# Zählerstand wird in einer globalen Variable gespeichert
counting_channel = None
current_count = 1
last_user = None

@bot.command()
@commands.has_permissions(manage_channels=True)
async def setupcounting(ctx, channel: discord.TextChannel):
    global counting_channel
    counting_channel = channel
    await ctx.send(f"✅ Counting-Channel wurde auf {channel.mention} gesetzt!")
    await channel.send("Zähle mit mir! :1234:")
    await channel.send("Der Zähler beginnt bei 1! :one:")
    await channel.send("Wenn du einen Fehler machst, wird der Zähler zurückgesetzt! :warning:")
    await channel.send("Viel Spaß beim Zählen! :smiley:")

@bot.event
async def on_message(message):
    global counting_channel, current_count, last_user

    # Stelle sicher, dass der Bot nicht auf seine eigenen Nachrichten reagiert
    if message.author == bot.user:
        return

    # Wenn es eine Nachricht im Zählkanal ist
    if counting_channel and message.channel == counting_channel:
        try:
            # Überprüfe, ob die Nachricht eine Zahl ist und ob sie der aktuellen Zahl entspricht
            user_number = int(message.content)

            if user_number == current_count and message.author != last_user:
                current_count += 1
                last_user = message.author
                await message.add_reaction("✅")  # Häkchen für korrekte Zahl
            else:
                # Setze den Zähler zurück, wenn ein Fehler gemacht wird
                current_count = 1
                last_user = None  # Reset für den Benutzer, der zuletzt gezählt hat
                await message.add_reaction("❌")  # Kreuz für falsche Zahl oder hintereinander zählen
                await message.channel.send(f"❌ **Falsche Zahl oder hintereinander gezählt!** Der Zähler wird zurückgesetzt. :warning: Der Zähler startet wieder bei 1!")
        except ValueError:
            # Wenn die Nachricht keine Zahl ist
            await message.channel.send("❌ Bitte gib nur eine Zahl ein! :warning:")

    # Verarbeite andere Nachrichten
    await bot.process_commands(message)

@bot.command()
async def countingstop(ctx):
    global counting_channel, current_count, last_user
    counting_channel = None
    current_count = 1
    last_user = None
    await ctx.send("🛑 Das Zählen wurde gestoppt!")
# ===================== ECONOMY SYSTEM =====================
# Ein daily Befehl, wo man jeden Tag nach 24 Stunden 1000 Credits bekommt
daily_users = {}  # Speichert die letzten Daily-Nutzungen

@bot.command()
async def daily(ctx):
    user_id = ctx.author.id
    current_time = discord.utils.utcnow()

    if user_id in daily_users:
        last_claimed = daily_users[user_id]
        time_difference = current_time - last_claimed

        if time_difference < timedelta(days=1):
            remaining_time = timedelta(days=1) - time_difference
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f":x: Du kannst deinen Daily-Bonus erst in **{hours} Stunden, {minutes} Minuten und {seconds} Sekunden** wieder beanspruchen.")
            return

    # Credits vergeben
    await ctx.send(f"💰 {ctx.author.mention}, du hast **1000 Credits** erhalten!")
    daily_users[user_id] = current_time
    # Einen work Befehl wo man 100-300 Credits bekommt
    @bot.command()
    async def work(ctx):
        credits = random.randint(100, 150, 200, 250, 300)
        await ctx.send(f":briefcase: {ctx.author.mention}, du hast **{credits} Credits** verdient!")
        # Einen bal Befehl damit man seinen Credit stand sieht
        @bot.command()
        async def bal(ctx):
            credits = daily_users.get(ctx.author.id, 0)
            await ctx.send(f":credit_card: {ctx.author.mention}, du hast **{credits} Credits**!")
            


# ===================== BOT START =====================
@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

bot.run(TOKEN)
