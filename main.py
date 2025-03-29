import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from datetime import timedelta

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Hole den Token aus der .env-Datei
TOKEN = os.getenv('TOKEN')

# Überprüfen, ob der Token korrekt geladen wurde
if TOKEN is None:
    print("Fehler: Der Token wurde nicht geladen!")

# Prefix für die Befehle
PREFIX = '!'

# Erstelle die Intents für den Bot
intents = discord.Intents.default()
intents.members = True  
intents.message_content = True  

# Initialisiere den Bot
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Timeout-Befehl für Minuten (Prefix)
@bot.command()
async def timeout(ctx, member: discord.Member, minutes: int):
    try:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)  # Richtige Zeitzone!
        await member.timeout(until, reason="Timeout command")
        await ctx.send(f"{member.mention} wurde für {minutes} Minuten getimed out.")
    except Exception as e:
        await ctx.send(f"Fehler: {e}")

# Timeout-Befehl für Minuten (Slash)
@bot.tree.command(name="timeout", description="Set a timeout for a member")
async def timeout_slash(interaction: discord.Interaction, member: discord.Member, minutes: int):
    try:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)  # Richtige Zeitzone!
        await member.timeout(until, reason="Timeout command")
        await interaction.response.send_message(f"{member.mention} wurde für {minutes} Minuten getimed out.")
    except Exception as e:
        await interaction.response.send_message(f"Fehler: {e}")

# Untimeout-Befehl (Prefix)
@bot.command()
async def untimeout(ctx, member: discord.Member):
    try:
        await member.timeout(None, reason="Untimeout command")
        await ctx.send(f"{member.mention} wurde enttimed out.")
    except Exception as e:
        await ctx.send(f"Fehler: {e}")

# Untimeout-Befehl (Slash)
@bot.tree.command(name="untimeout", description="Remove the timeout from a member")
async def untimeout_slash(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout(None, reason="Untimeout command")
        await interaction.response.send_message(f"{member.mention} wurde enttimed out.")
    except Exception as e:
        await interaction.response.send_message(f"Fehler: {e}")

# Online-Befehl (Prefix)
@bot.command()
async def online(ctx):
    await ctx.send("✨ **Ich bin jetzt online!** ✨\n"
        "Bereit, dir zu helfen – was kann ich für dich tun? 🤔")

# Online-Befehl (Slash)
@bot.tree.command(name="online", description="Check if the bot is online.")
async def online_slash(interaction: discord.Interaction):
    await interaction.response.send_message("✨ **Ich bin jetzt online!** ✨\n"
        "Bereit, dir zu helfen – was kann ich für dich tun? 🤔")

# Setup Invite-Befehl (Prefix)
@bot.command()
async def setupinvite(ctx):
    invite_link = discord.utils.oauth_url(bot.user.id, permissions=discord.Permissions(permissions=8))
    await ctx.send(f"Hier ist der Invite-Link für diesen Bot: {invite_link}\nLade den Bot zu deinem Server ein! 🚀")

# Invite-Tracker: Wenn ein Mitglied dem Server beitritt (Prefix)
@bot.event
async def on_member_join(member):
    print(f"{member} ist dem Server beigetreten.")
    await member.guild.system_channel.send(f"{member.mention} ist dem Server beigetreten! 🎉")

# Invite-Tracker: Wenn ein Mitglied den Server verlässt (Prefix)
@bot.event
async def on_member_remove(member):
    print(f"{member} hat den Server verlassen.")
    await member.guild.system_channel.send(f"{member.mention} hat den Server verlassen. 😢")

# Invite-Tracker aktivieren (Prefix)
@bot.command()
async def invite_tracker(ctx):
    await ctx.send(f"Invite-Tracker ist aktiv! :tickets:")

# Ticket-Befehl (Prefix)
@bot.command()
async def ticket(ctx):
    await ctx.send(f"Du brauchst Hilfe? Klicke hier, um ein Ticket zu erstellen! :tickets:\n"
                   "Wenn du ein Ticket öffnest, wird ein privater Kanal für dich und das Support-Team erstellt.")

    # Erstelle den Ticket-Button
    ticket_button = discord.ui.Button(label="Ticket erstellen", style=discord.ButtonStyle.primary)

    # Erstelle eine View, um den Button anzuzeigen
    ticket_view = discord.ui.View()
    ticket_view.add_item(ticket_button)

    # Callback für den Ticket-Button
    async def ticket_callback(interaction: discord.Interaction):
        guild = interaction.guild
        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=None)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await channel.set_permissions(guild.default_role, read_messages=False)
        await channel.send(f"{interaction.user.mention}, dein Ticket wurde erstellt!")
        await interaction.response.send_message(f"Dein Ticket wurde erstellt: {channel.mention}", ephemeral=True)

    # Setze die Callback-Funktion
    ticket_button.callback = ticket_callback

    # Sende die Nachricht mit der View (der Button)
    await ctx.send("Klicke auf den Button, um ein Ticket zu erstellen.", view=ticket_view)

# Event, wenn der Bot bereit ist
@bot.event
async def on_ready():
    print(f"Bot ist bereit als {bot.user}.")
    print("Bot ist jetzt online und bereit, Befehle entgegenzunehmen! 🚀")
    try:
        await bot.tree.sync()  # Synchronisiert die Slash-Befehle
        print("Slash-Commands synchronisiert!")
    except Exception as e:
        print(f"Fehler bei der Synchronisation der Slash-Befehle: {e}")

# Starte den Bot mit dem Token
bot.run(TOKEN)
