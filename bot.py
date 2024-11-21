import discord
from loguru import logger

bot = discord.Bot(command_prefix="!", intents=discord.Intents.all())


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}, bot is ready.")


@bot.slash_command(name="echo", description="Respond with the given text")
async def echo(ctx: discord.ApplicationContext, message: str = "Hello"):
    await ctx.respond(message)


if __name__ == "__main__":
    from dotenv import dotenv_values

    bot.run(dotenv_values()["DISCORD_BOT_TOKEN"])
