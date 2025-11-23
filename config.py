# Copyright (c) 2021 Itz-fork

import os

def to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# --- LOG CHANNEL ---
log_channel_env = os.environ.get("LOGS_CHANNEL")
log_channel = to_int(log_channel_env, None)


class Config(object):
    APP_ID = int(os.environ.get("APP_ID", 37423470))
    API_HASH = os.environ.get("API_HASH", "eeef73ca03d2707c0e4d0fa1d19472b0")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "8206336257:AAFgOOiUMDx_6KsYf5pILaNDqScwjWwF1GU")
    AUTH_USERS = set(int(x) for x in os.environ.get("AUTH_USERS", "").split())
    DOWNLOAD_LOCATION = "./NexaBots"
    IS_PUBLIC_BOT = os.environ.get("IS_PUBLIC_BOT", "True")
    LOGS_CHANNEL = log_channel
    TG_MAX_SIZE = 2040108421
    # Mega User Account
    MEGA_EMAIL = os.environ.get("MEGA_EMAIL", "")
    MEGA_PASSWORD = os.environ.get("MEGA_PASSWORD", "")

# Text Prints
B_START_TEXT = """
   __  ___                                     ___       __ 
  /  |/  /__ ___ ____ _      ___  ___   ____  / _ )___  / /_
 / /|_/ / -_) _ `/ _ `/ _   / _ \/_ /  /___/ / _  / _ \/ __/
/_/  /_/\__/\_, /\_,_/ (_) /_//_//__/       /____/\___/\__/ 
           /___/

Process: {}
"""

PROCESS_TEXT = """
Process: {}
"""

LOGGED_AS_USER = """
Successfully Logged Into Mega.nz User Account
"""

LOGIN_ERROR_TEXT = """
Can't Get Mega Email and Password Login as an Anonymouse User
"""

ERROR_TEXT = """
 _____                     
| ____|_ __ _ __ ___  _ __ 
|  _| | '__| '__/ _ \| '__|
| |___| |  | | | (_) | |   
|_____|_|  |_|  \___/|_|  

Log: {}

Save the Log file and Send it to @Nexa_bots for Help :)
"""

START_TEXT="""
    _   __                   ____        __      
   / | / /__  _  ______ _   / __ )____  / /______
  /  |/ / _ \| |/_/ __ `/  / __  / __ \/ __/ ___/
 / /|  /  __/>  </ /_/ /  / /_/ / /_/ / /_(__  ) 
/_/ |_/\___/_/|_|\__,_/  /_____/\____/\__/____/ 


Bot is Running Now! Join @NexaBotsUpdates
"""
