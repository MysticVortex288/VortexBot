from cProfile import label
from email import message
from math import remainder
import random
from tarfile import data_filter
from unittest import result
from click import style
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from datetime import timedelta
import datetime
import openai


from flask import ctx
import openai
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
    embed.add_field(name="!work", value="Gibt dir alle 3 Stunden Credits.", inline=True)
    embed.add_field(name="!bal", value="Zeigt dein Guthaben an.", inline=True)
    embed.add_field(name="!pay @User Betrag", value="Überweist Credits an einen anderen Benutzer.", inline=True)
    embed.add_field(name="!bal @User", value="Zeigt das Guthaben eines anderen Benutzers an.", inline=True)
    embed.add_field(name="🔹 **Casino Befehle**", value="Spiele mit deinen Credits Casino.", inline=False)
    embed.add_field(name="!blackjack (Betrag)", value="Spiele Blackjack mit deinen Credits.", inline=True)
    embed.add_field(name="!coinflip (Betrag)", value="Spiele Kopf oder Zahl mit deinen Credits.", inline=True)
    embed.set_footer(text="Designed by MysticVortex")
    embed.timestamp = datetime.datetime.utcnow()



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
  # Online Nachricht embed machen
    embed = discord.Embed(title="Bot Status", description="Der Bot ist online!", color=discord.Color.green())


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
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(TicketButton(bot))

class TicketButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="🎟️ Ticket erstellen", style=discord.ButtonStyle.primary)
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        existing_ticket = discord.utils.get(category.channels, name=f"ticket-{interaction.user.name}")
        if existing_ticket:
            await interaction.response.send_message(":x: Du hast bereits ein offenes Ticket!", ephemeral=True)
            return

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
        await channel.send("\ud83d\udd12 **Dieses Ticket wurde geschlossen.**", view=DeleteTicketView())
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

@commands.has_permissions(moderate_members=True)
@commands.command()
async def ticket(ctx):
    await ctx.send("🎟️ **Klicke auf den Button, um ein Ticket zu erstellen!**", view=TicketView(ctx.bot))

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
# Speichert die letzten Daily-Nutzungen
credits_data = {}
daily_users = {}
work_users = {}

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
    credits_data[user_id] = credits_data.get(user_id, 0) + 1000
    daily_users[user_id] = current_time
    await ctx.send(f"💰 {ctx.author.mention}, du hast **1000 Credits** erhalten!")

@bot.command()
async def work(ctx):
    user_id = ctx.author.id
    current_time = discord.utils.utcnow()

    if user_id in work_users:
        last_worked = work_users[user_id]
        time_difference = current_time - last_worked

        if time_difference < timedelta(hours=3):
            remaining_time = timedelta(hours=3) - time_difference
            hours, remainder = divmod(remaining_time.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            await ctx.send(f":x: Du kannst erst in **{hours} Stunden, {minutes} Minuten und {seconds} Sekunden** wieder arbeiten.")
            return

    credits = random.randint(100, 300)
    credits_data[user_id] = credits_data.get(user_id, 0) + credits
    work_users[user_id] = current_time
    await ctx.send(f":briefcase: {ctx.author.mention}, du hast **{credits} Credits** verdient!")

@bot.command()
async def bal(ctx):
    user_id = ctx.author.id
    credits = credits_data.get(user_id, 0)
    await ctx.send(f":credit_card: {ctx.author.mention}, du hast **{credits} Credits**!")
    # Einen Befehl damit die Credits Stand von anderen sehen kann
    @bot.command()
    async def bal(ctx, member: discord.Member):
        user_id = member.id
        credits = credits_data.get(user_id, 0)
        await ctx.send(f":credit_card: {member.mention}, hat **{credits} Credits**!")

@bot.command()
async def pay(ctx, member: discord.Member, amount: int):
    sender_id = ctx.author.id
    receiver_id = member.id

    if amount <= 0:
        await ctx.send(":x: Der Betrag muss größer als 0 sein!")
        return

    if sender_id not in credits_data or credits_data[sender_id] < amount:
        await ctx.send(":x: Du hast nicht genug Credits!")
        return

    credits_data[sender_id] -= amount
    credits_data[receiver_id] = credits_data.get(receiver_id, 0) + amount
    await ctx.send(f"💸 {ctx.author.mention} hat {amount} Credits an {member.mention} gesendet!")

    # ================= CASINO BEFEHLE =====================
    # Kartendeck für Blackjack
CARD_VALUES = {
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 10, "Q": 10, "K": 10, "A": 11  # Ass kann 1 oder 11 sein
}
CARD_EMOJIS = {
    "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣", "10": "🔟",
    "J": "🃏", "Q": "👸", "K": "🤴", "A": "🅰️"
}

credits_data = {}

def draw_card():
    return random.choice(list(CARD_VALUES.keys()))

def hand_value(hand):
    value = sum(CARD_VALUES[card] for card in hand)
    ace_count = hand.count("A")
    while value > 21 and ace_count > 0:
        value -= 10
        ace_count -= 1
    return value

class BlackjackGame(discord.ui.View):
    def __init__(self, ctx, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bet = bet
        self.player_hand = [draw_card(), draw_card()]
        self.dealer_hand = [draw_card(), draw_card()]
        self.finished = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user == self.ctx.author

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.player_hand.append(draw_card())
        if hand_value(self.player_hand) > 21:
            await self.end_game(interaction, "💥 Du hast über 21! **Verloren!** ❌")
        else:
            await self.update_message(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🤵 Der Dealer zieht seine Karten...", ephemeral=True)
        await asyncio.sleep(2)
        while hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(draw_card())
            await self.update_message(interaction)
            await asyncio.sleep(1)

        player_value = hand_value(self.player_hand)
        dealer_value = hand_value(self.dealer_hand)

        if dealer_value > 21 or player_value > dealer_value:
            winnings = self.bet * 2
            credits_data[self.ctx.author.id] += winnings
            await self.end_game(interaction, f"🎉 **Gewonnen!** Du bekommst {winnings} Credits! 🏆")
        elif player_value < dealer_value:
            await self.end_game(interaction, "❌ **Verloren!** Der Dealer hatte eine bessere Hand.")
        else:
            credits_data[self.ctx.author.id] += self.bet
            await self.end_game(interaction, "⚖️ **Unentschieden!** Dein Einsatz wurde zurückgegeben.")

    async def update_message(self, interaction: discord.Interaction):
        embed = self.create_embed()
        await self.message.edit(embed=embed, view=self)

    async def end_game(self, interaction: discord.Interaction, result):
        self.finished = True
        embed = self.create_embed()
        embed.add_field(name="🎲 Ergebnis", value=result, inline=False)
        await self.message.edit(embed=embed, view=None)
        self.stop()

    def create_embed(self):
        embed = discord.Embed(title="♠️ Blackjack ♠️", color=discord.Color.green())
        embed.add_field(
            name="🃏 Deine Karten",
            value=f"{' '.join(CARD_EMOJIS[c] for c in self.player_hand)} (Gesamt: {hand_value(self.player_hand)})",
            inline=False
        )
        embed.add_field(
            name="🤵 Dealer Karten",
            value=f"{' '.join(CARD_EMOJIS[c] for c in self.dealer_hand)} (Gesamt: {hand_value(self.dealer_hand)})",
            inline=False
        )
        return embed

    async def start_game(self):
        credits_data[self.ctx.author.id] -= self.bet
        embed = self.create_embed()
        self.message = await self.ctx.send(embed=embed, view=self)

@bot.command()
async def blackjack(ctx, bet: int):
    if ctx.author.id not in credits_data:
        credits_data[ctx.author.id] = 100  # Startguthaben
    if bet > credits_data[ctx.author.id] or bet <= 0:
        await ctx.send("❌ Ungültiger Einsatz! Stelle sicher, dass du genug Credits hast.")
        return

    game = BlackjackGame(ctx, bet)
    await game.start_game()
@bot.command()
async def coinflip(ctx, bet: int):
    # Falls der Spieler noch keine Credits hat, initialisiere ihn mit 100
    if ctx.author.id not in credits_data:
        credits_data[ctx.author.id] = 100

    # Überprüfe, ob der Einsatz gültig ist
    if bet > credits_data[ctx.author.id] or bet <= 0:
        await ctx.send(":x: Ungültiger Einsatz! Stelle sicher, dass du genug Credits hast.")
        return

    # Generiere das Ergebnis des Coinflips
    result = random.choice(["Kopf", "Zahl"])

    # Erstellt das Embed für das Coinflip-Spiel
    embed = discord.Embed(
        title=":coin: Coinflip",
        description=f"Du hast {bet} Credits gesetzt!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Ergebnis", value="🔵 = Kopf | 🔴 = Zahl", inline=False)
    embed.set_footer(text="Reagiere mit 🔵 oder 🔴, um deine Wahl zu treffen!")

    # Nachricht senden
    message = await ctx.send(embed=embed)

    # Reaktionen hinzufügen
    await message.add_reaction("🔵")  # Kopf
    await message.add_reaction("🔴")  # Zahl

    # Überprüfungsfunktion für die Reaktion
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["🔵", "🔴"]

    # Warte auf die Reaktion des Spielers
    try:
        reaction, user = await bot.wait_for("reaction_add", check=check, timeout=30)
    except TimeoutError:
        await ctx.send("⏳ Du hast zu lange gebraucht! Das Spiel wurde abgebrochen.")
        return

    # Überprüfung, ob die Wahl mit dem Ergebnis übereinstimmt
    player_choice = "Kopf" if str(reaction.emoji) == "🔵" else "Zahl"

    if player_choice == result:
        credits_data[ctx.author.id] += bet
        await ctx.send(f":tada: Glückwunsch! Du hast {bet} Credits gewonnen! Du hast jetzt {credits_data[ctx.author.id]} Credits.")
    else:
        credits_data[ctx.author.id] -= bet
        await ctx.send(f":x: Pech gehabt! Du hast {bet} Credits verloren. Du hast jetzt {credits_data[ctx.author.id]} Credits.")


    
    #======================ERROR HANDLER =====================
    @bot.event
    async def on_message(message):
    # Verhindere, dass der Bot auf eigene Nachrichten reagiert
     if message.author == bot.user:
        return

    # Wenn die Nachricht mit "!" beginnt, aber kein Befehl ist
    if message.content.startswith("!"):
        try:
            # Versuche, die Nachricht als Befehl zu verarbeiten
            await bot.process_commands(message)
        except commands.CommandNotFound:
            # Wenn der Befehl nicht gefunden wird, eine Fehlermeldung senden
            await message.channel.send("Fehler: Das ist kein gültiger Befehl.")

            #====================== KI ==========================
    openai.api_key = os.getenv("OPENAI_API_KEY")  # Holt den API-Key aus den Railway-Env-Variablen

# Speichert den KI-Kanal
ki_kanal = None

@bot.command()
async def setupki(ctx, kanal: discord.TextChannel):
    """Setzt den Kanal, in dem die KI antwortet."""
    global ki_kanal
    ki_kanal = kanal.id
    await ctx.send(f"✅ KI ist nun in {kanal.mention} aktiv!")

@bot.event
async def on_message(message):
    """Reagiert mit KI-Antworten, wenn im richtigen Kanal geschrieben wird."""
    global ki_kanal
    if message.author.bot:
        return  # Ignoriere andere Bots
    
    if ki_kanal and message.channel.id == ki_kanal:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": message.content}]
            )
            answer = response["choices"][0]["message"]["content"]
            await message.channel.send(answer)
        except Exception as e:
            await message.channel.send(f"⚠️ Fehler: {e}")

    await bot.process_commands(message)  # Wichtiger Teil, um Befehle nicht zu blockieren

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")





# ===================== BOT START =====================
    @bot.event
    async def on_ready():
     print(f"✅ Bot ist online als {bot.user}")

bot.run(TOKEN)
