import os
import sys

from dotenv import load_dotenv
from envier import Env

from globals import logger

load_dotenv()
log = logger

class GlobalConfig(Env):
    DB_HOST = Env.var(type=str, name="DB_HOST")
    DB_USER = Env.var(type=str, name="DB_USER")
    DB_PASSWORD = Env.var(type=str, name="DB_PASSWORD")
    DB_NAME = Env.var(type=str, name="DB_NAME")
    DB_PORT = Env.var(type=int, name="DB_PORT", default=3306)
    MAX_POOL_SIZE = Env.var(type=int, name="MAX_POOL_SIZE", default=20)
    DISCORD_TOKEN = Env.var(type=str, name="DISCORD_TOKEN")
    CATEGORY_CHANNEL_NAME = Env.var(type=str, name="CATEGORY_CHANNEL_NAME")
    REPORT_CHANNEL_NAME = Env.var(type=str, name="REPORT_CHANNEL_NAME")
    BOSS1_CHANNEL_NAME = Env.var(type=str, name="BOSS1_CHANNEL_NAME")
    BOSS2_CHANNEL_NAME = Env.var(type=str, name="BOSS2_CHANNEL_NAME")
    BOSS3_CHANNEL_NAME = Env.var(type=str, name="BOSS3_CHANNEL_NAME")
    BOSS4_CHANNEL_NAME = Env.var(type=str, name="BOSS4_CHANNEL_NAME")
    BOSS5_CHANNEL_NAME = Env.var(type=str, name="BOSS5_CHANNEL_NAME")
    TL_SHIFTER_CHANNEL_NAME = Env.var(type=str, name="TL_SHIFTER_CHANNEL_NAME")
    MESSAGE_DEFAULT_DELETE_AFTER_SHORT = Env.var(type=int, name="MESSAGE_DEFAULT_DELETE_AFTER_SHORT", default=3)
    MESSAGE_DEFAULT_DELETE_AFTER_MEDIUM = Env.var(type=int, name="MESSAGE_DEFAULT_DELETE_AFTER_MEDIUM", default=15)
    MESSAGE_DEFAULT_DELETE_AFTER_LONG = Env.var(type=int, name="MESSAGE_DEFAULT_DELETE_AFTER_LONG", default=30)


config = GlobalConfig()

REQUIRED_ENV_VARS = {
    "DISCORD_TOKEN": "Your Discord bot token",
    # Add more variables and descriptions
}


def check_env_vars():
    missing = False
    for var, description in REQUIRED_ENV_VARS.items():
        if not os.getenv(var):
            missing = True
            log.critical(f"❌ Missing Environment Variable: {var}")
    if missing:
        sys.exit(1)