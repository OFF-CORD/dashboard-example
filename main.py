import asyncio
from bot import bot, logger
from dotenv import dotenv_values
from flask import Flask, redirect, url_for, render_template
from flask_discord import DiscordOAuth2Session, models as FlaskDiscordModels

TOP_SECRETS = dotenv_values()

app = Flask(__name__)
app.config.update(TOP_SECRETS)

oauth_session = DiscordOAuth2Session(app)


async def get_guild_ids() -> list[int]:
    "return a list of guild ids the bot is in"
    final = []
    for guild in bot.guilds:
        final.append(guild.id)
    return final


@app.route("/")
async def home():
    return render_template(
        "index.html",
        authorized=oauth_session.authorized,
        bot_name=bot.user.display_name if bot.user else "(UnInitialzied)",
    )


@app.route("/login")
async def login():
    return oauth_session.create_session()


@app.route("/callback")
async def callback():
    logger.debug("Callback begin called")
    try:
        oauth_session.callback()
    except Exception:
        pass

    return redirect(url_for("dashboard"))


def log_unauth_user():
    return logger.info("Redirecting unauthticated user back to login page")


@app.route("/dashboard")
async def dashboard():
    if not oauth_session.authorized:
        log_unauth_user()
        return redirect(url_for("login"))

    logger.info(
        f'User "{oauth_session.fetch_user().username}" ({oauth_session.user_id}) has logged in'
    )

    bot_guilds_ids = await get_guild_ids()
    user_guilds: list[FlaskDiscordModels.Guild] = oauth_session.fetch_guilds()

    guilds = []
    for guild in user_guilds:
        if not guild.permissions.administrator:
            # means the user won't be able to add the bot if not there already
            continue

        guild.class_color = (
            "green-border" if guild.id in bot_guilds_ids else "red-border"
        )
        guilds.append(guild)

    # arrange guilds the bot isn't in to the end of the list
    guilds.sort(key=lambda x: x.class_color == "red-border")

    return render_template(
        "dashboard.html",
        guild_count=len(bot_guilds_ids),
        guilds=guilds,
        username=oauth_session.fetch_user().name,
    )


@app.route("/dashboard/<int:guild_id>")
async def dashboard_server(guild_id: int):
    if not oauth_session.authorized:
        log_unauth_user()
        return redirect(url_for("login"))

    guild = bot.get_guild(guild_id)
    if guild is None:
        return redirect(
            f'https://discord.com/oauth2/authorize?&client_id={app.config["DISCORD_CLIENT_ID"]}&scope=bot&permissions=8&guild_id={guild_id}&response_type=code&redirect_uri={app.config["DISCORD_REDIRECT_URI"]}'
        )
    return render_template(
        "guild-info.html",
        guild=guild,
        guild_roles=guild.roles,
    )


async def run_prod():
    # a hack to use both event loops
    async def async_flask_app():
        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        config = Config()
        config.bind = ["127.0.0.1:5000"]

        await serve(app, config, shutdown_trigger=lambda *_: asyncio.Future())

    return await asyncio.gather(
        async_flask_app(), bot.start(TOP_SECRETS["DISCORD_BOT_TOKEN"])
    )


def run_devel():
    import threading

    bot_thread = threading.Thread(
        target=bot.run, args=(TOP_SECRETS["DISCORD_BOT_TOKEN"],), daemon=True
    )
    bot_thread.start()

    app.run(debug=True)


if __name__ == "__main__":
    run_devel()

    # ATTENTION: use this instead of `run_devel` for production builds
    # asyncio.run(run_prod())
