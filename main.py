from threading import Thread
from flask import Flask
import os
import random
import discord
from discord.ext import commands
import sqlite3
import asyncio
from discord import app_commands
from discord.ui import View, Button
import requests
import datetime
from typing import Optional

# Flask Setup für den Webserver
app = Flask('')

@app.route('/')
def home():
    return "Bot ist online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    server = Thread(target=run)
    server.start()

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

# Datenbank Setup
conn = sqlite3.connect('casino.db')
cursor = conn.cursor()

# Erstelle die Tabelle für KI-Kanäle
cursor.execute('''
    CREATE TABLE IF NOT EXISTS funki_channels (
        guild_id INTEGER,
        channel_id INTEGER,
        PRIMARY KEY (guild_id, channel_id)
    )
''')
conn.commit()

async def generate_response(prompt: str) -> str:
    try:
        # Nutze die API Ninjas Chat API
        api_url = 'https://api.api-ninjas.com/v1/chat'
        headers = {'X-Api-Key': os.getenv('NINJA_API_KEY')}
        payload = {'message': prompt}
        
        # Sende Anfrage
        response = requests.post(api_url, headers=headers, json=payload)
        
        # Prüfe ob die Anfrage erfolgreich war
        if response.status_code == 200:
            return response.json()['message']
        else:
            return "Entschuldigung, ich konnte gerade keine Antwort generieren."
            
    except Exception as e:
        return "Tut mir leid, ich verstehe dich gerade nicht. Versuche es bitte nochmal!"

@bot.event
async def on_message(message):
    # Ignoriere Bot-Nachrichten
    if message.author.bot:
        return

    # Überprüfe ob der Kanal ein KI-Kanal ist
    cursor.execute("SELECT 1 FROM funki_channels WHERE guild_id = ? AND channel_id = ?",
                 (message.guild.id, message.channel.id))
    is_funki_channel = cursor.fetchone() is not None

    if is_funki_channel and not message.content.startswith('!'):
        # Zeige "schreibt..." Indikator
        async with message.channel.typing():
            # Generiere eine KI-Antwort
            response = await generate_response(message.content)
        
        # Sende die Antwort
        await message.channel.send(response)
        return
    
    # Verarbeite normale Befehle
    await bot.process_commands(message)

@bot.command(name="setupki")
@commands.has_permissions(administrator=True)
async def setupki(ctx, channel: discord.TextChannel):
    # Füge den Kanal zur Datenbank hinzu
    cursor.execute('''
        INSERT OR REPLACE INTO funki_channels (guild_id, channel_id)
        VALUES (?, ?)
    ''', (ctx.guild.id, channel.id))
    conn.commit()
    
    await ctx.send(f"KI-System wurde in {channel.mention} eingerichtet!")

# Hilfsfunktionen
def get_coins(user_id: int) -> int:
    cursor.execute("SELECT balance FROM economy WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("INSERT INTO economy (user_id, balance) VALUES (?, 0)", (user_id,))
        conn.commit()
        return 0
    return result[0]

def update_coins(user_id: int, amount: int):
    current_coins = get_coins(user_id)
    new_coins = max(0, current_coins + amount)  # Verhindere negative Coins
    cursor.execute("INSERT OR REPLACE INTO economy (user_id, balance) VALUES (?, ?)", (user_id, new_coins))
    conn.commit()

def get_last_used(user_id: int, command: str) -> Optional[datetime.datetime]:
    cursor.execute("SELECT last_used FROM cooldowns WHERE user_id = ? AND command = ?", (user_id, command))
    result = cursor.fetchone()
    if result:
        return datetime.datetime.fromisoformat(result[0])
    return None

def update_last_used(user_id: int, command: str):
    now = datetime.datetime.now().isoformat()
    cursor.execute("""
        INSERT OR REPLACE INTO cooldowns (user_id, command, last_used)
        VALUES (?, ?, ?)
    """, (user_id, command, now))
    conn.commit()

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
async def on_ready():
    print(f'🤖 Bot ist online als {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="!help | Dein Allrounder"))

@bot.command(name="help", aliases=["commands", "befehle", "hilfe"])
async def help_command(ctx, category: str = None):
    if category:
        # Hilfe für spezifische Kategorie
        category = category.lower()
        if category == "economy":
            embed = discord.Embed(
                title="💰 Economy - Hilfe",
                description="**Economy-Befehle:**\n\n"
                          "• `!daily` - Tägliche Coins abholen\n"
                          "• `!work` - Arbeiten für Coins\n"
                          "• `!beg` - Betteln für Coins\n"
                          "• `!rob <user>` - Andere Spieler ausrauben\n"
                          "• `!balance` - Zeigt dein Guthaben\n"
                          "• `!top` - Zeigt die reichsten Spieler",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1037834042793287680.webp?size=96&quality=lossless")
        elif category == "casino":
            embed = discord.Embed(
                title="🎲 Casino - Hilfe",
                description="**Casino-Befehle:**\n\n"
                          "• `!slots <einsatz>` - Spielautomat\n"
                          "• `!roulette <einsatz> <wette>` - Roulette\n"
                          "• `!coinflip <einsatz> <kopf/zahl>` - Münzwurf\n"
                          "• `!dice <einsatz>` - Würfelspiel\n"
                          "• `!scratch <einsatz>` - Rubbellos\n"
                          "• `!race <einsatz> <pferd>` - Pferderennen\n"
                          "• `!yahtzee <einsatz>` - Würfelpoker",
                color=discord.Color.purple()
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1037834098187153408.webp?size=96&quality=lossless")
        elif category == "moderation":
            embed = discord.Embed(
                title="🛡️ Moderation - Hilfe",
                description="**Server-Moderation:**\n"
                          "• `!kick <user> [grund]` - Kickt einen User\n"
                          "• `!ban <user> [grund]` - Bannt einen User\n"
                          "• `!timeout <user> <minuten> [grund]` - Timeout für User\n"
                          "• `!untimeout <user> [grund]` - Hebt Timeout auf\n\n"
                          "**Rollen & Events:**\n"
                          "• `!creatorroles` - Erstellt die Creator-Rollen\n"
                          "• `!setupwelcome` - Richtet Welcome/Goodbye System ein:\n"
                          "  ↳ Erstellt #willkommen für Join-Nachrichten\n"
                          "  ↳ Erstellt #aufwiedersehen für Leave-Nachrichten\n"
                          "  ↳ Vergibt automatisch Member-Rolle\n"
                          "  ↳ Zeigt schöne Nachrichten wenn User joinen/leaven\n"
                          "  ↳ Zeigt bei Leaves wie lange der User da war\n\n"
                          "**Hinweis:** Diese Befehle benötigen Admin-Rechte!",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1037834181517074443.webp?size=96&quality=lossless")
        elif category == "counting":
            embed = discord.Embed(
                title="🔢 Counting - Hilfe",
                description="**Counting-Befehle:**\n\n"
                          "• `!countingsetup #kanal` - Richtet einen Counting-Kanal ein\n"
                          "• `!stopcounting` - Deaktiviert das Counting-System\n\n"
                          "**Hinweis:** Diese Befehle sind nur für Administratoren!",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1037834223187759154.webp?size=96&quality=lossless")
        elif category == "ki":
            embed = discord.Embed(
                title="🤖 KI-System Befehle",
                description="Hier sind alle Befehle für das KI-System:\n\n"
                           "• `!setupki #kanal` - Richtet einen KI-Kanal ein\n\n"
                           "**So funktioniert's:**\n"
                           "1. Richte zuerst mit `!setupki #kanal` einen Kanal ein\n"
                           "2. Schreibe dann einfach in diesem Kanal und die KI wird antworten!",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1037834270235238410.webp?size=96&quality=lossless")
        else:
            embed = discord.Embed(
                title="❓ Unbekannte Kategorie",
                description="**Verfügbare Kategorien:**\n\n"
                          "• `!help economy` - Economy-System\n"
                          "• `!help casino` - Casino-Spiele\n"
                          "• `!help moderation` - Server-Moderation\n"
                          "• `!help counting` - Counting-System\n"
                          "• `!help ki` - KI-System",
                color=discord.Color.red()
            )
            embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1037834270235238410.webp?size=96&quality=lossless")
    else:
        # Hauptmenü
        embed = discord.Embed(
            title="🤖 Dein Allrounder Bot",
            description="**Ein Bot für alles!**\n\n"
                      "Wähle eine Kategorie für mehr Infos:\n\n"
                      "🎮 **Fun & Games**\n"
                      "• `!help casino` - Spannende Casino-Spiele\n"
                      "• `!help counting` - Gemeinsam zählen\n"
                      "• `!help ki` - Lustige KI-Witze\n\n"
                      "💰 **Economy**\n"
                      "• `!help economy` - Coins verdienen & ausgeben\n\n"
                      "🛡️ **Administration**\n"
                      "• `!help moderation` - Server verwalten\n",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1037834270235238410.webp?size=96&quality=lossless")
        embed.set_footer(text="Tipp: Nutze !commands als Alternative zu !help")
    
    # Füge Autor und Zeitstempel zu allen Embeds hinzu
    embed.set_author(
        name=ctx.guild.name,
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )
    embed.timestamp = datetime.datetime.now()
    
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
    
    def get_hand_value(self, hand: list) -> int:
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
    
    def dealer_play(self) -> list:
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
            embed = discord.Embed(
                title="❌ Fehler",
                description="Das ist nicht dein Spiel!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        self.game.player_hit()
        await interaction.response.defer()
        await self.update_message()

    @discord.ui.button(label="Stand 🛑", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.game.player_id:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Das ist nicht dein Spiel!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
        embed = discord.Embed(
            title="❌ Fehler",
            description="Der Mindesteinsatz ist 50 Coins!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    user_coins = get_coins(ctx.author.id)
    if user_coins < bet:
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Du hast nicht genug Coins! Dir fehlen noch **{bet - user_coins:,}** Coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Ziehe Einsatz ab
    update_coins(ctx.author.id, -bet)

    # Starte Spiel
    game = BlackjackGame(ctx.author.id, bet)
    view = BlackjackView(game, ctx)
    await view.update_message()

class WheelGame:
    def __init__(self):
        # Roulette Zahlen und ihre Eigenschaften
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
            embed = discord.Embed(
                title="❌ Fehler",
                description="Das ist nicht dein Spiel!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if self.spinning:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Das Rad dreht sich bereits!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
                      "`!wheel <einsatz>`\n"
                      "Beispiel: `!wheel 100`",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)
        return

    if bet < 50:
        embed = discord.Embed(
            title="❌ Fehler",
            description="Der Minimaleinsatz ist 50 Coins!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    user_coins = get_coins(ctx.author.id)
    if user_coins < bet:
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Du hast nicht genug Coins! Dir fehlen noch **{bet - user_coins:,}** Coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
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
        if len(set(result)) == 1:  # Alle Symbole gleich
            symbol = result[0]
            return self.symbols[symbol]["multiplier"], f"3x {symbol}"
        
        # Zwei gleich
        if len(set(result)) == 2:  # Zwei gleiche Symbole
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
            embed = discord.Embed(
                title="❌ Fehler",
                description="Das ist nicht dein Spiel!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
            embed = discord.Embed(
                title="❌ Fehler",
                description="Die Walzen drehen sich bereits!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
        embed = discord.Embed(
            title="❌ Fehler",
            description="Der Mindesteinsatz ist 1 Coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Du hast nicht genug Coins! Dir fehlen noch **{bet_amount - balance:,}** Coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    update_coins(ctx.author.id, -bet_amount)
    view = SlotsView(bet_amount, ctx.author.id, ctx)
    await view.start()

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
            embed = discord.Embed(
                title="❌ Fehler",
                description="Das ist nicht dein Spiel!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
            embed = discord.Embed(
                title="❌ Fehler",
                description="Das Rad dreht sich bereits!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
        
        # Prüfe auf Gewinn
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
        embed = discord.Embed(
            title="❌ Fehler",
            description="Der Mindesteinsatz ist 1 Coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Du hast nicht genug Coins! Dir fehlen noch **{bet_amount - balance:,}** Coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
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
            description="Wähle Kopf oder Zahl!\nEinsatz: {self.bet_amount} Coins",
            color=discord.Color.gold()
        )
        self.message = await self.ctx.send(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Das ist nicht dein Spiel!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
        result = random.choice(['kopf', 'zahl'])
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
            embed.description = f"🎯 **{result.upper()}**!\n\n**Gewonnen!** Du bekommst {winnings} Coins!"
            embed.color = discord.Color.green()
        else:
            embed.description = f"🎯 **{result.upper()}**!\n\n**Verloren!**"
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
            description="Rubble 3 Felder frei!\nEinsatz: {self.bet_amount} Coins\n\n"
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
            embed = discord.Embed(
                title="❌ Fehler",
                description="Das ist nicht dein Spiel!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
    async def button_1(self, interaction: discord.Interaction, button: Button):
        await self.reveal(interaction, 0, button)

    @discord.ui.button(label="2", style=discord.ButtonStyle.secondary, row=0)
    async def button_2(self, interaction: discord.Interaction, button: Button):
        await self.reveal(interaction, 1, button)

    @discord.ui.button(label="3", style=discord.ButtonStyle.secondary, row=0)
    async def button_3(self, interaction: discord.Interaction, button: Button):
        await self.reveal(interaction, 2, button)

    @discord.ui.button(label="4", style=discord.ButtonStyle.secondary, row=1)
    async def button_4(self, interaction: discord.Interaction, button: Button):
        await self.reveal(interaction, 3, button)

    @discord.ui.button(label="5", style=discord.ButtonStyle.secondary, row=1)
    async def button_5(self, interaction: discord.Interaction, button: Button):
        await self.reveal(interaction, 4, button)

    @discord.ui.button(label="6", style=discord.ButtonStyle.secondary, row=1)
    async def button_6(self, interaction: discord.Interaction, button: Button):
        await self.reveal(interaction, 5, button)

    @discord.ui.button(label="7", style=discord.ButtonStyle.secondary, row=2)
    async def button_7(self, interaction: discord.Interaction, button: Button):
        await self.reveal(interaction, 6, button)

    @discord.ui.button(label="8", style=discord.ButtonStyle.secondary, row=2)
    async def button_8(self, interaction: discord.Interaction, button: Button):
        await self.reveal(interaction, 7, button)

    @discord.ui.button(label="9", style=discord.ButtonStyle.secondary, row=2)
    async def button_9(self, interaction: discord.Interaction, button: Button):
        await self.reveal(interaction, 8, button)

    async def reveal(self, interaction: discord.Interaction, position: int, button: discord.ui.Button):
        if self.revealed >= 3:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Du hast bereits 3 Felder aufgedeckt!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
        embed = discord.Embed(
            title="❌ Fehler",
            description="Der Mindesteinsatz ist 1 Coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Du hast nicht genug Coins! Dir fehlen noch **{bet_amount - balance:,}** Coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
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
        embed = discord.Embed(
            title="❌ Fehler",
            description="Der Mindesteinsatz ist 1 Coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Du hast nicht genug Coins! Dir fehlen noch **{bet_amount - balance:,}** Coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
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
        
        # Vier gleiche
        if 4 in counts.values():  
            return 30, "🎲 Vier gleiche!"
        
        # Full House
        if 3 in counts.values() and 2 in counts.values():  
            return 25, "🎲 Full House!"
        
        # Große Straße
        if (sorted_dice == [1,2,3,4,5] or 
              sorted_dice == [2,3,4,5,6]):  
            return 30, "🎲 Große Straße!"
        
        # Kleine Straße
        for i in range(1, 4):
            if all(x in sorted_dice for x in range(i, i+4)):  
                return 20, "🎲 Kleine Straße!"
        
        # Drilling
        if 3 in counts.values():  
            return 15, "🎲 Drei gleiche!"
        
        # Zwei Paare
        if list(counts.values()).count(2) == 2:  
            return 10, "🎲 Zwei Paare!"
        
        # Ein Paar
        if 2 in counts.values():  
            return 5, "🎲 Ein Paar!"
        
        return 0, "Keine Gewinnkombination"

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Das ist nicht dein Spiel!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            await self.message.edit(view=self)

    @discord.ui.button(label="Würfeln", style=discord.ButtonStyle.success, emoji="🎲", row=0)
    async def roll(self, interaction: discord.Interaction, button: Button):
        if self.rolling:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Die Würfel rollen bereits!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if self.rolls_left <= 0:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Keine Würfe mehr übrig!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
            embed = discord.Embed(
                title="❌ Fehler",
                description="Warte bis die Würfel aufhören zu rollen!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.kept_dice[0] = not self.kept_dice[0]
        button.style = discord.ButtonStyle.primary if self.kept_dice[0] else discord.ButtonStyle.secondary
        await self.update_message()
        await interaction.response.defer()

    @discord.ui.button(label="Würfel 2", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_die_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.rolling:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Warte bis die Würfel aufhören zu rollen!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.kept_dice[1] = not self.kept_dice[1]
        button.style = discord.ButtonStyle.primary if self.kept_dice[1] else discord.ButtonStyle.secondary
        await self.update_message()
        await interaction.response.defer()

    @discord.ui.button(label="Würfel 3", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_die_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.rolling:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Warte bis die Würfel aufhören zu rollen!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.kept_dice[2] = not self.kept_dice[2]
        button.style = discord.ButtonStyle.primary if self.kept_dice[2] else discord.ButtonStyle.secondary
        await self.update_message()
        await interaction.response.defer()

    @discord.ui.button(label="Würfel 4", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_die_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.rolling:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Warte bis die Würfel aufhören zu rollen!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.kept_dice[3] = not self.kept_dice[3]
        button.style = discord.ButtonStyle.primary if self.kept_dice[3] else discord.ButtonStyle.secondary
        await self.update_message()
        await interaction.response.defer()

    @discord.ui.button(label="Würfel 5", style=discord.ButtonStyle.secondary, row=2)
    async def toggle_die_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.rolling:
            embed = discord.Embed(
                title="❌ Fehler",
                description="Warte bis die Würfel aufhören zu rollen!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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
        embed = discord.Embed(
            title="❌ Fehler",
            description="Der Mindesteinsatz ist 1 Coin!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    balance = get_coins(ctx.author.id)
    if balance < bet_amount:
        embed = discord.Embed(
            title="❌ Fehler",
            description=f"Du hast nicht genug Coins! Dir fehlen noch **{bet_amount - balance:,}** Coins.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    update_coins(ctx.author.id, -bet_amount)
    view = YahtzeeView(bet_amount, ctx.author.id, ctx)
    await view.start()

@bot.event
async def on_command_error(ctx, error):
    # Verhindere doppelte Error-Nachrichten
    if hasattr(ctx.command, 'on_error'):
        return

    # Ignoriere CommandNotFound Errors
    if isinstance(error, commands.CommandNotFound):
        return

    # Erstelle das Error Embed
    embed = discord.Embed(color=discord.Color.red())
    
    if isinstance(error, commands.CommandOnCooldown):
        hours = int(error.retry_after // 3600)
        minutes = int((error.retry_after % 3600) // 60)
        seconds = int(error.retry_after % 60)
        
        embed.title = "⏰ Cooldown"
        embed.description = f"Du musst noch **{hours}h {minutes}m {seconds}s** warten!"
        embed.color = discord.Color.orange()
    
    elif isinstance(error, commands.MissingPermissions):
        embed.title = "❌ Keine Berechtigung"
        embed.description = "Du hast keine Berechtigung für diesen Befehl!"
    
    elif isinstance(error, commands.MemberNotFound):
        embed.title = "❌ Mitglied nicht gefunden"
        embed.description = "Dieser User wurde nicht gefunden!"
    
    else:
        embed.title = "❌ Fehler"
        embed.description = str(error)
    
    # Setze ein Flag, dass der Error behandelt wurde
    ctx.error_handled = True
    
    # Sende die Nachricht
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
    cursor.execute("SELECT user_id, balance FROM economy ORDER BY balance DESC LIMIT 10")
    top_users = cursor.fetchall()
    
    description = ""
    for i, (user_id, balance) in enumerate(top_users, 1):
        user = bot.get_user(user_id)
        if user:
            medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
            description += f"{medal} **{i}.** {user.mention}: **{balance:,}** Coins\n"
    
    embed = discord.Embed(
        title="🏆 Reichste Spieler",
        description=description,
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

class RoleButton(discord.ui.Button):
    def __init__(self, role_name: str, emoji: str, style: discord.ButtonStyle):
        # Entferne Emoji aus dem Label wenn es schon im Namen ist
        label = role_name
        if emoji in label:
            label = label.replace(emoji, '').strip()
        super().__init__(label=label, emoji=emoji, style=style, custom_id=f"role_{role_name}")
        self.role_name = role_name

    async def callback(self, interaction: discord.Interaction):
        # Finde die Rolle
        role = discord.utils.get(interaction.guild.roles, name=self.role_name)
        if not role:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Fehler",
                    description=f"Die Rolle {self.role_name} wurde nicht gefunden!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return

        # Toggle die Rolle
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🗑️ Rolle entfernt",
                    description=f"Dir wurde die Rolle {role.mention} entfernt!",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Rolle hinzugefügt",
                    description=f"Dir wurde die Rolle {role.mention} hinzugefügt!",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )

class RoleView(discord.ui.View):
    def __init__(self, roles: list):
        super().__init__(timeout=None)  # Kein Timeout
        
        # Füge Buttons für jede Rolle hinzu
        for role_name, emoji, style in roles:
            self.add_item(RoleButton(role_name, emoji, style))

@bot.command()
@commands.has_permissions(administrator=True)
async def setupwelcome(ctx):
    """Erstellt den Willkommens-Kanal und die Member-Rolle"""
    
    # Erstelle/Prüfe Member-Rolle
    member_role = discord.utils.get(ctx.guild.roles, name="Member")
    if not member_role:
        member_role = await ctx.guild.create_role(
            name="Member",
            color=discord.Color.blue(),
            mentionable=True,
            reason="Rolle für Mitglieder"
        )
        role_created = "✅ Member-Rolle erstellt"
    else:
        role_created = "ℹ️ Member-Rolle existiert bereits"
    
    # Standard Channel-Berechtigungen
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(
            send_messages=False,
            add_reactions=True
        ),
        ctx.guild.me: discord.PermissionOverwrite(
            send_messages=True,
            add_reactions=True
        )
    }
    
    # Erstelle/Prüfe Willkommens-Kanal
    welcome_channel = discord.utils.get(ctx.guild.channels, name="willkommen")
    if not welcome_channel:
        welcome_channel = await ctx.guild.create_text_channel(
            'willkommen',
            overwrites=overwrites,
            reason="Kanal für Willkommensnachrichten"
        )
        channel_created = "✅ Willkommens-Kanal erstellt"
    else:
        channel_created = "ℹ️ Willkommens-Kanal existiert bereits"
    
    # Erstelle/Prüfe Goodbye-Kanal
    goodbye_channel = discord.utils.get(ctx.guild.channels, name="aufwiedersehen")
    if not goodbye_channel:
        goodbye_channel = await ctx.guild.create_text_channel(
            'aufwiedersehen',
            overwrites=overwrites,
            reason="Kanal für Abschiedsnachrichten"
        )
        goodbye_created = "✅ Aufwiedersehen-Kanal erstellt"
    else:
        goodbye_created = "ℹ️ Aufwiedersehen-Kanal existiert bereits"
    
    # Sende Bestätigung
    embed = discord.Embed(
        title="🛠️ Willkommens-System Setup",
        description=f"{role_created}\n{channel_created}\n{goodbye_created}\n\n"
                   "**Das System ist jetzt aktiv:**\n"
                   "• Neue Mitglieder bekommen automatisch die Member-Rolle\n"
                   f"• Willkommensnachrichten erscheinen in {welcome_channel.mention}\n"
                   f"• Abschiedsnachrichten erscheinen in {goodbye_channel.mention}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def creatorroles(ctx):
    """Erstellt alle Rollen für das Server-Setup und zeigt Auswahlmenüs"""
    
    # Definiere die Rollen mit ihren Farben und Emojis
    role_categories = {
        "Altersgruppen": [
            ("12+", "👶", discord.ButtonStyle.gray),
            ("16+", "🧑", discord.ButtonStyle.gray),
            ("18+", "🧓", discord.ButtonStyle.gray)
        ],
        "Geschlecht": [
            ("♂️ Männlich", "♂️", discord.ButtonStyle.blurple),
            ("♀️ Weiblich", "♀️", discord.ButtonStyle.danger)
        ],
        "Plattformen": [
            ("🤖 Android", "📱", discord.ButtonStyle.success),
            ("🍎 iOS", "📱", discord.ButtonStyle.danger),
            ("💻 PC", "🖥️", discord.ButtonStyle.blurple),
            ("🍏 MacOS", "💻", discord.ButtonStyle.gray)
        ],
        "Spiele": [
            ("⛏️ Minecraft", "⛏️", discord.ButtonStyle.success),
            ("🔫 Fortnite", "🎮", discord.ButtonStyle.danger),
            ("🎮 Roblox", "🎮", discord.ButtonStyle.primary),
            ("🎯 Valorant", "🎯", discord.ButtonStyle.danger)
        ]
    }

    # Erstelle die Rollen
    for category, roles in role_categories.items():
        for role_name, _, _ in roles:
            if not discord.utils.get(ctx.guild.roles, name=role_name):
                # Erstelle die Rolle wenn sie nicht existiert
                member_role = await ctx.guild.create_role(
                    name=role_name,
                    mentionable=True,
                    reason="Automatisch erstellte Rolle für neue Mitglieder"
                )
    
    # Sende Auswahlmenüs für jede Kategorie
    for category, roles in role_categories.items():
        embed = discord.Embed(
            title=f"🎭 {category}",
            description="Klicke auf einen Button um die entsprechende Rolle zu erhalten oder zu entfernen!",
            color=discord.Color.blue()
        )
        
        # Füge Rollen zur Embed-Beschreibung hinzu
        roles_text = "\n".join(f"{emoji} {name}" for name, emoji, _ in roles)
        embed.add_field(name="Verfügbare Rollen:", value=roles_text)
        
        # Sende Embed mit Buttons
        await ctx.send(embed=embed, view=RoleView(roles))

@bot.command()
@commands.has_permissions(administrator=True)
async def countingsetup(ctx, channel: discord.TextChannel):
    """Richtet einen Counting-Kanal ein"""
    
    # Speichere den Kanal in der Datenbank
    cursor.execute('''
        INSERT OR REPLACE INTO counting (guild_id, channel_id, last_number, last_user_id)
        VALUES (?, ?, 0, 0)
    ''', (ctx.guild.id, channel.id))
    conn.commit()
    
    # Sende Bestätigung
    embed = discord.Embed(
        title="✅ Counting eingerichtet",
        description=f"Der Kanal {channel.mention} wurde als Counting-Kanal eingerichtet!\n\n"
                   "**Regeln:**\n"
                   "• Zähle von 1 an aufwärts\n"
                   "• Jeder darf nur eine Zahl nacheinander schreiben\n"
                   "• Bei einem Fehler wird auf 1 zurückgesetzt",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    
    # Sende Startmessage im Counting-Kanal
    embed = discord.Embed(
        title="🔢 Counting",
        description="Das Zählen beginnt!\nSchreibe '1' um zu starten.",
        color=discord.Color.blue()
    )
    await channel.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def stopcounting(ctx):
    """Deaktiviert das Counting-System"""
    
    # Lösche den Counting-Kanal aus der Datenbank
    cursor.execute('DELETE FROM counting WHERE guild_id = ?', (ctx.guild.id,))
    conn.commit()
    
    # Sende Bestätigung
    embed = discord.Embed(
        title="✅ Counting deaktiviert",
        description="Das Counting-System wurde deaktiviert.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.event
async def on_member_join(member):
    # Prüfe/Erstelle Member-Rolle
    member_role = discord.utils.get(member.guild.roles, name="Member")
    if not member_role:
        # Erstelle die Rolle wenn sie nicht existiert
        member_role = await member.guild.create_role(
            name="Member",
            color=discord.Color.blue(),
            mentionable=True,
            reason="Automatisch erstellte Rolle für neue Mitglieder"
        )
    
    # Gebe dem neuen Mitglied die Rolle
    await member.add_roles(member_role)
    
    # Sende Willkommensnachricht
    welcome_channel = discord.utils.get(member.guild.channels, name="willkommen")
    if welcome_channel:
        embed = discord.Embed(
            title="👋 Neues Mitglied",
            description=f"{member.mention} ist dem Server beigetreten!\n"
                      f"Du bist unser {len(member.guild.members)}. Mitglied!\n\n"
                      "• Dir wurde automatisch die Member-Rolle gegeben\n"
                      "• Nutze `!help` um alle Befehle zu sehen\n"
                      "• Viel Spaß auf unserem Server! 🎉",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        await welcome_channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    # Berechne wie lange der User auf dem Server war
    joined_at = member.joined_at
    now = datetime.datetime.now(datetime.timezone.utc)
    time_on_server = now - joined_at
    
    # Formatiere die Zeit schön
    days = time_on_server.days
    hours, remainder = divmod(time_on_server.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    time_str = ""
    if days > 0:
        time_str += f"{days} {'Tag' if days == 1 else 'Tage'} "
    if hours > 0:
        time_str += f"{hours} {'Stunde' if hours == 1 else 'Stunden'} "
    if minutes > 0:
        time_str += f"{minutes} {'Minute' if minutes == 1 else 'Minuten'}"
    
    # Sende Goodbye-Nachricht
    goodbye_channel = discord.utils.get(member.guild.channels, name="aufwiedersehen")
    if goodbye_channel:
        embed = discord.Embed(
            title="👋 Auf Wiedersehen!",
            description=f"**{member}** hat den Server verlassen.\n\n"
                      f"War {time_str} auf dem Server\n"
                      f"Beigetreten: {joined_at.strftime('%d.%m.%Y um %H:%M')} Uhr",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.timestamp = datetime.datetime.now()
        await goodbye_channel.send(embed=embed)

@bot.event
async def on_message(message):
    # Ignoriere Bot-Nachrichten
    if message.author.bot:
        return

    # Überprüfe ob der Kanal ein KI-Witz-Kanal ist
    cursor.execute("SELECT 1 FROM funki_channels WHERE guild_id = ? AND channel_id = ?",
                 (message.guild.id, message.channel.id))
    is_funki_channel = cursor.fetchone() is not None

    if is_funki_channel and not message.content.startswith('!'):
        # Zeige "schreibt..." Indikator
        async with message.channel.typing():
            # Generiere eine KI-Antwort
            response = await generate_response(message.content)
        
        # Sende die Antwort
        await message.channel.send(response)
        return
    
    # Verarbeite normale Befehle
    await bot.process_commands(message)

if __name__ == "__main__":
    keep_alive()
    bot.run(os.getenv('DISCORD_TOKEN'))
