# Discord Moderations-Bot

Ein Discord Bot mit Moderationsbefehlen (Kick, Ban, Timeout).

## Features
- Kick Command (`!kick` oder `/kick`)
- Ban Command (`!ban` oder `/ban`)
- Timeout Command (`!timeout` oder `/timeout`)
- Untimeout Command (`!untimeout` oder `/untimeout`)
- DM Benachrichtigungen
- Schöne Embed-Nachrichten

## Installation
1. Repository klonen
2. `pip install -r requirements.txt` ausführen
3. `.env` Datei mit Bot-Token erstellen
4. `python main.py` ausführen

## Befehle
- `!kick @user [grund]` - Kickt einen User
- `!ban @user [grund]` - Bannt einen User
- `!timeout @user [minuten] [grund]` - Timeout für User
- `!untimeout @user [grund]` - Hebt Timeout auf

## Setup
1. Bot im [Discord Developer Portal](https://discord.com/developers/applications) erstellen
2. Token in `.env` Datei einfügen
3. Bot mit benötigten Berechtigungen einladen
