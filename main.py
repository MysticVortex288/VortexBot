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
    # Begrüßungsnachricht senden
    if member.guild.system_channel:
        await member.guild.system_channel.send(f"🎉 {member.mention} ist dem Server beigetreten!")

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

# ================= Reaction-Roles =====================
@bot.command()
async def reactionrole(ctx):
    # Erste Rolle ist Altersgruppe 12+, dann 16+ und dann 18+
    role_12 = discord.utils.get(ctx.guild.roles, name="12+")
    role_16 = discord.utils.get(ctx.guild.roles, name="16+")
    role_18 = discord.utils.get(ctx.guild.roles, name="18+")

    # Wenn die Rollen nicht existieren, erstelle sie
    if not role_12:
        role_12 = await ctx.guild.create_role(name="12+")
    if not role_16:
        role_16 = await ctx.guild.create_role(name="16+")
    if not role_18:
        role_18 = await ctx.guild.create_role(name="18+")

    # Erstelle die Nachricht, in der die Rollen ausgewählt werden können
    embed = discord.Embed(title=":performing_arts: Wähle deine Altersgruppe", description="Klicke auf die Knöpfe, um deine Altersgruppe auszuwählen.", color=discord.Color.blue())
    embed.add_field(name=":one: 12+", value="Klicke auf den Knopf, um die Rolle 12+ zu erhalten.", inline=False) 
    embed.add_field(name=":two: 16+", value="Klicke auf den Knopf, um die Rolle 16+ zu erhalten.", inline=False)
    embed.add_field(name=":three: 18+", value="Klicke auf den Knopf, um die Rolle 18+ zu erhalten.", inline=False)

    message = await ctx.send(embed=embed)

    # Erstelle die Knöpfe für die Rollen
    view = discord.ui.View(timeout=None)

    async def add_remove_role(interaction: discord.Interaction, role):
        # Überprüfe, ob der Benutzer bereits die Rolle hat
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"Die Rolle **{role.name}** wurde entfernt.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Die Rolle **{role.name}** wurde hinzugefügt.", ephemeral=True)

    button_12 = discord.ui.Button(label="12+", style=discord.ButtonStyle.primary)
    button_12.callback = lambda interaction: add_remove_role(interaction, role_12)
    
    button_16 = discord.ui.Button(label="16+", style=discord.ButtonStyle.primary)
    button_16.callback = lambda interaction: add_remove_role(interaction, role_16)
    
    button_18 = discord.ui.Button(label="18+", style=discord.ButtonStyle.primary)
    button_18.callback = lambda interaction: add_remove_role(interaction, role_18)

    # Füge die Buttons der Ansicht hinzu
    view.add_item(button_12)
    view.add_item(button_16)
    view.add_item(button_18)

    await message.edit(view=view)


# ===================== BOT START =====================
@bot.event
async def on_ready():
    print(f"✅ Bot ist online als {bot.user}")

bot.run(TOKEN)
