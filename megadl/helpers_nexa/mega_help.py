import math
import time
import traceback

from megadl import meganzbot as client
from config import Config, ERROR_TEXT

# Progress helper (unchanged except safety around numbers)
async def progress_for_pyrogram(
    current,
    total,
    ud_type,
    message,
    start
):
    try:
        now = time.time()
        diff = now - start
        # throttle updates to reduce API calls
        if diff <= 0:
            diff = 1e-6
        if round(diff % 10.00) == 0 or current == total:
            percentage = (current * 100 / total) if total and total > 0 else 0
            speed = (current / diff) if diff > 0 else 0
            elapsed_ms = int(round(diff) * 1000)
            remaining_ms = int((total - current) / speed * 1000) if speed > 0 else 0
            estimated_total_time = elapsed_ms + remaining_ms

            elapsed_time = TimeFormatter(milliseconds=elapsed_ms)
            estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)

            progress = "[{0}{1}] \n**Process**: {2}%\n".format(
                ''.join(["█" for i in range(math.floor(percentage / 5))]) if percentage > 0 else "",
                ''.join(["░" for i in range(20 - math.floor(percentage / 5))]) if percentage > 0 else "░"*20,
                round(percentage, 2)
            )

            tmp = progress + "{0} of {1}\n**Speed:** {2}/s\n**ETA:** {3}\n".format(
                humanbytes(current),
                humanbytes(total),
                humanbytes(speed),
                estimated_total_time if estimated_total_time != '' else "0 s"
            )
            try:
                await message.edit(
                    text="{}\n {} \n\n**Powered by @NexaBotsUpdates**".format(
                        ud_type,
                        tmp
                    )
                )
            except Exception:
                # ignore edit failures (message deleted, too frequent, etc.)
                pass
    except Exception:
        pass


def humanbytes(size):
    if not size and size != 0:
        return ""
    try:
        size = float(size)
    except Exception:
        return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power and n < 4:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'


def TimeFormatter(milliseconds: int) -> str:
    try:
        seconds, milliseconds = divmod(int(milliseconds), 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        tmp = ((str(days) + "d, ") if days else "") + \
            ((str(hours) + "h, ") if hours else "") + \
            ((str(minutes) + "m, ") if minutes else "") + \
            ((str(seconds) + "s, ") if seconds else "") + \
            ((str(milliseconds) + "ms, ") if milliseconds else "")
        return tmp[:-2]
    except Exception:
        return ""


# Checking log channel (synchronous call to check setup)
def check_logs():
    try:
        if Config.LOGS_CHANNEL and Config.LOGS_CHANNEL > 0:
            try:
                c_info = client.get_chat(chat_id=Config.LOGS_CHANNEL)
                # best-effort validation
                if getattr(c_info, "type", None) != "channel":
                    print(ERROR_TEXT.format("Chat is not a channel"))
                    return False
                if getattr(c_info, "username", None) is not None:
                    # prefer private channel id (no username)
                    print(ERROR_TEXT.format("Chat appears to be public (has username)"))
                    # not fatal, just warn
                # notify start
                try:
                    client.send_message(chat_id=Config.LOGS_CHANNEL, text="`Mega.nz-Bot has Successfully Started!` \n\n**Powered by @NexaBotsUpdates**")
                except Exception:
                    pass
                return True
            except Exception as e:
                print(ERROR_TEXT.format(f"Failed to access provided LOGS_CHANNEL: {e}"))
                return False
        else:
            print("No Log Channel ID is Given. Logs disabled.")
            return False
    except Exception as e:
        print(ERROR_TEXT.format(f"Unknown error in check_logs: {e}"))
        return False


# Send Download / Upload / Import logs in log channel (async)
async def send_logs(user_id=None, mchat_id=None, up_file=None, mega_url=None,
                    download_logs=False, upload_logs=False, import_logs=False):
    try:
        # early exit if logs disabled
        if not (Config.LOGS_CHANNEL and Config.LOGS_CHANNEL > 0):
            return

        if download_logs:
            # build a safe message
            ui = user_id or "Unknown"
            ci = mchat_id or "Unknown"
            mu = mega_url or "N/A"
            try:
                await client.send_message(chat_id=Config.LOGS_CHANNEL,
                                          text=f"**#DOWNLOAD_LOG** \n\n**User ID:** `{ui}` \n**Chat ID:** `{ci}` \n**Url:** {mu}")
            except Exception as e:
                # log but do not crash
                await send_errors(e=e)
        elif upload_logs:
            ui = user_id or "Unknown"
            ci = mchat_id or "Unknown"
            if up_file is not None:
                try:
                    # up_file is a Message object — forward or handle gracefully
                    forwarded = await up_file.forward(Config.LOGS_CHANNEL)
                    await forwarded.reply_text(f"**#UPLOAD_LOG** \n\n**User ID:** `{ui}` \n**Chat ID:** `{ci}`")
                except Exception as e:
                    await send_errors(e=e)
            elif mega_url is not None:
                try:
                    await client.send_message(chat_id=Config.LOGS_CHANNEL,
                                              text=f"**#UPLOAD_LOG** \n\n**User ID:** `{ui}` \n**Chat ID:** `{ci}` \n**Url:** {mega_url}")
                except Exception as e:
                    await send_errors(e=e)
        elif import_logs:
            ui = user_id or "Unknown"
            ci = mchat_id or "Unknown"
            mu = mega_url or "N/A"
            try:
                await client.send_message(chat_id=Config.LOGS_CHANNEL,
                                          text=f"**#IMPORT_LOG** \n\n**User ID:** `{ui}` \n**Chat ID:** `{ci}` \n**Origin Url:** {mu}")
            except Exception as e:
                await send_errors(e=e)
    except Exception as e:
        # catch-all: don't allow logging to break main flow
        try:
            await send_errors(e=e)
        except Exception:
            print("send_logs failed and send_errors also failed:", e)


# Send or print errors (async)
async def send_errors(e):
    try:
        if Config.LOGS_CHANNEL and Config.LOGS_CHANNEL > 0:
            try:
                await client.send_message(Config.LOGS_CHANNEL, f"**#Error** \n`{e}`")
            except Exception:
                # fallback to printing and saving stacktrace
                print("Failed to send error to LOGS_CHANNEL:", e)
                traceback.print_exc()
        else:
            # logs disabled: print to stdout
            print(ERROR_TEXT.format(e))
    except Exception:
        # last resort
        print("Critical failure in send_errors:", e)
        traceback.print_exc()
