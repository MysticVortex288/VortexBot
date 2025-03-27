import discord
from discord.ext import commands
import asyncio
from typing import Optional

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Slash-Command Integration
@bot.tree.command(name="timeout", description="Timeoute einen User für eine bestimmte Zeit.")
@commands.has_permissions(manage_messages=True)
async def slash_timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: Optional[str] = "Kein Grund angegeben"):
    timeout_role = discord.utils.get(interaction.guild.roles, name="Timeout")
    if not timeout_role:
        await interaction.response.send_message("Die Rolle 'Timeout' existiert nicht!", ephemeral=True)
        return

    await member.add_roles(timeout_role)
    await member.send(f"Du wurdest für {minutes} Minuten getimeoutet. Grund: {reason}")
    await interaction.response.send_message(f"{member.mention} wurde für {minutes} Minuten getimeoutet. Grund: {reason}")

    await asyncio.sleep(minutes * 60)
    await member.remove_roles(timeout_role)
    await member.send("Du wurdest enttimeoutet.")
    await interaction.followup.send(f"{member.mention} wurde enttimeoutet.")

# Prefix-Command (!timeout)
@bot.command()
@commands.has_permissions(manage_messages=True)
async def timeout(ctx, member: discord.Member, minutes: int, *, reason: Optional[str] = "Kein Grund angegeben"):
    timeout_role = discord.utils.get(ctx.guild.roles, name="Timeout")
    if not timeout_role:
        await ctx.send("Die Rolle 'Timeout' existiert nicht!")
        return

    await member.add_roles(timeout_role)
    await member.send(f"Du wurdest für {minutes} Minuten getimeoutet. Grund: {reason}")
    await ctx.send(f"{member.mention} wurde für {minutes} Minuten getimeoutet. Grund: {reason}")

    await asyncio.sleep(minutes * 60)
    await member.remove_roles(timeout_role)
    await member.send("Du wurdest enttimeoutet.")
    await ctx.send(f"{member.mention} wurde enttimeoutet.")

# Bot starten
TOKEN = "DEIN_BOT_TOKEN"
bot.run(TOKEN)
