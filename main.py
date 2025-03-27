from threading import Thread
from flask import Flask
import os
import random
import discord
from discord.ext import commands
import sqlite3
import asyncio
import aiohttp
from discord import app_commands
from discord.ui import View, Button
import requests
import datetime
from typing import Optional
import discord_slash
import discord_prefix
# andere leute timeouten mit /timeout @user minuten grund und !timeout @user minutes grund
@bot.command()
@commands.has_permissions(manage_messages=true)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason: Optional(str)):
    if reason is None:
        reason = "kein Grund angegeben"
        await member.send(f"Du wurdest für {minutes} Minuten getimeoutet, Grund: {reason}")
        await ctx.send(f"{member} wurde für {minutes} Minuten getimeoutet, Grund: {reason}")
        await member.add_roles(discord.utils.get(ctx.guild.roles, name = "Timeout"))
    #Der jenige der jemanden getimeoutet hat bekommt eine dm und denjenigen den es betrifft kriegt auch eine dm
    else:
        await member.send(f"Du wurdest für {minutes} Minuten getimeoutet, Grund: {reason}")
        await ctx.send(f"{member} wurde für {minutes} Minuten getimeoutet, Grund: {reason}")
        await member.add_roles(discord.utils.get(ctx.guild.roles, name = "Timeout"))
        await asyncio.sleep(minutes*60)
        await member.remove_roles(discord.utils.get(ctx.guild.roles, name = "Timeout"))
        await member.send(f"Du wurdest enttimeoutet")
        await ctx.send(f"{member} wurde enttimeoutet")
        #diese befehle sollen mit slash und prefix funktionieren
        @bot.discord_slash
        @bot.discord_prefix
