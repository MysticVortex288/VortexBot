# Lade den OpenAI API-Schlüssel aus der Umgebungsvariable
openai.api_key = os.getenv("OPENAI_API_KEY")  # API-Schlüssel wird aus der Umgebungsvariable abgerufen

# Stelle sicher, dass der API-Schlüssel korrekt gesetzt ist
if openai.api_key is None:
    print("Fehler: Der OpenAI API-Schlüssel wurde nicht in den Umgebungsvariablen gesetzt.")
    exit()

# Setze Intents, die für den Bot erforderlich sind
intents = discord.Intents.default()
intents.message_content = True  # Damit der Bot Nachrichteninhalte lesen kann

# Erstelle den Bot mit den Intents
bot = commands.Bot(command_prefix="!", intents=intents)

# Der Kanal, in dem der Bot auf Nachrichten ohne Prefix reagiert
ki_kanal = None

@bot.command()
async def setupki(ctx, kanal: discord.TextChannel):
    """
    Setzt den Kanal, in dem die KI aktiv ist und auf Nachrichten ohne Prefix reagiert.
    """
    global ki_kanal
    ki_kanal = kanal
    await ctx.send(f"Der KI-Kanal wurde auf {kanal.mention} gesetzt!")

@bot.event
async def on_message(message):
    """
    Verarbeitet eingehende Nachrichten.
    Der Bot antwortet ohne Prefix im KI-Kanal, andernfalls benötigt er das Prefix.
    """
    global ki_kanal

    # Überprüfen, ob der Bot auf Nachrichten im richtigen Kanal reagieren soll
    if ki_kanal and message.channel == ki_kanal and message.author != bot.user:
        try:
            # OpenAI API, um eine Antwort zu generieren
            response = openai.Completion.create(
                engine="text-davinci-003",  # Verwende das Modell deiner Wahl
                prompt=message.content,
                max_tokens=150,
                temperature=0.7
            )

            # Antwort in den Kanal senden
            await message.channel.send(response.choices[0].text.strip())

        except Exception as e:
            await message.channel.send(f"Ein Fehler ist aufgetreten: {e}")

    # Stelle sicher, dass der Bot auch Befehle verarbeiten kann, auch wenn er auf Nachrichten reagiert
    await bot.process_commands(message)

@bot.command()
async def custom_help(ctx):
    """
    Gibt eine Übersicht über alle verfügbaren Befehle.
    """
    help_text = (
        "**Verfügbare Befehle:**\n"
        "!setupki <Kanal> - Setzt den Kanal, in dem die KI aktiv ist.\n"
        "Der Bot antwortet nur im festgelegten Kanal ohne Prefix.\n"
    )
    await ctx.send(help_text)

# Weitere benutzerdefinierte Befehle hinzufügen
@bot.command()
async def echo(ctx, *, message: str):
    """
    Gibt eine Nachricht zurück.
    """
    await ctx.send(message)
