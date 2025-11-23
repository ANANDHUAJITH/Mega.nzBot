import math
import time
import traceback

from megadl import meganzbot as client
from config import Config, ERROR_TEXT

# Progress reporting for Pyrogram uploads/downloads
async def progress_for_pyrogram(
    current,
    total,
    ud_type,
    message,
    start
):
    now = time.time()
    diff = now - start
    # Update roughly every 10 seconds or on completion
    if diff <= 0:
        diff = 0.0001
    if round(diff % 10.0) == 0 or current == total:
        try:
            percentage = (current * 100) / total if total else 0
            speed = current / diff if diff else 0
            elapsed_time_ms = round(diff) * 1000
            time_to_completion_ms = round((total - current) / speed) * 1000 if speed else 0
            estimated_total_time_ms = elapsed_time_ms + time_to_completion_ms

            elapsed_time = TimeFormatter(milliseconds=elapsed_time_ms)
            estimated_total_time = TimeFormatter(milliseconds=estimated_total_time_ms)

            progress = "[{0}{1}] \n**Process**: {2}%\n".format(
                ''.join(["█" for _ in range(math.floor(percentage / 5))]),
                ''.join(["░" for _ in range(20 - math.floor(percentage / 5))]),
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
                # ignore edit failures (rate limits, message deleted, etc.)
                pass
        except Exception:
            # Make sure progress errors do not crash the bot
            pass


def humanbytes(size):
    # Safe guard
    if not size:
        return "0 B"
    try:
        power = 2**10
        n = 0
        Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
        while size > power:
            size /= power
            n += 1
        return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'
    except Exception:
        return "0 B"


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


# Checking log channel (keeps synchronous behavior like original)
def check_logs():
    """
    Called at startup to validate LOGS_CHANNEL. This function will not crash
    if LOGS_CHANNEL is 0/None/invalid — it will print helpful messages instead.
    """
    try:
        if not Config.LOGS_CHANNEL:
            print("No Log Channel ID is Given. Anyway I'm Trying to Start!")
            return

        # ensure it's an int and positive (channel ids are negative for supergroups/channels with -100 prefix,
        # but Pyrogram expects the id as int; here we only check existence)
        try:
            chat_id = int(Config.LOGS_CHANNEL)
        except Exception:
            print(ERROR_TEXT.format("Invalid LOGS_CHANNEL value"))
            return

        try:
            c_info = client.get_chat(chat_id=chat_id)
        except Exception as e:
            print(ERROR_TEXT.format(f"Failed to get chat info: {e}"))
            return

        # c_info could be None or an object
        if not c_info:
            print(ERROR_TEXT.format("Failed to resolve chat info"))
            return

        # If the chat is not a channel or is public (username set), warn
        try:
            c_type = getattr(c_info, "type", None)
            c_username = getattr(c_info, "username", None)
            if c_type != "channel":
                print(ERROR_TEXT.format("Chat is not a channel"))
                return
            if c_username is not None:
                print(ERROR_TEXT.format("Chat is not private"))
                return

            # send startup message (best effort)
            try:
                client.send_message(chat_id=chat_id, text="`Mega.nz-Bot has Successfully Started!` \n\n**Powered by @NexaBotsUpdates**")
            except Exception as e:
                print(f"Could not send startup message to LOGS_CHANNEL: {e}")
        except Exception as e:
            print(ERROR_TEXT.format(f"Unexpected chat info structure: {e}"))
            return
    except Exception as e:
        # nothing fatal — print and continue
        print(f"check_logs() error: {e}")


# Send Download or Upload logs in log channel (async)
async def send_logs(user_id, mchat_id, up_file=None, mega_url=None, download_logs=False, upload_logs=False, import_logs=False):
    """
    Sends logs to Config.LOGS_CHANNEL only when it is a valid non-zero integer.
    If sending fails, it will print the error instead of recursively calling send_errors.
    """
    # normalize ids
    try:
        c_id = int(Config.LOGS_CHANNEL) if Config.LOGS_CHANNEL else 0
    except Exception:
        c_id = 0

    # helper to safely send a message
    async def _safe_send_text(text):
        if c_id:
            try:
                await client.send_message(chat_id=c_id, text=text)
            except Exception as e:
                print(f"[LOG SEND FAILED] {e}\nText was:\n{text}")
        else:
            print(text)

    # guard and prepare values
    uid = user_id if user_id is not None else "Unknown"
    mid = mchat_id if mchat_id is not None else "Unknown"

    if download_logs:
        text = f"**#DOWNLOAD_LOG** \n\n**User ID:** `{uid}` \n**Chat ID:** `{mid}` \n**Url:** {mega_url}"
        await _safe_send_text(text)
        return

    if upload_logs:
        if up_file is not None:
            # up_file assumed to be a Message object or file-like; forward if possible
            if c_id:
                try:
                    gib_details = await up_file.forward(c_id)
                    try:
                        await gib_details.reply_text(f"**#UPLOAD_LOG** \n\n**User ID:** `{uid}` \n**Chat ID:** `{mid}`")
                    except Exception:
                        # best effort
                        pass
                except Exception as e:
                    # can't forward — fallback to text log
                    await _safe_send_text(f"**#UPLOAD_LOG** \n\n**User ID:** `{uid}` \n**Chat ID:** `{mid}`\n(Forward failed: {e})")
            else:
                print(f"UPLOAD_LOG \nUser ID: {uid} \n\nChat ID: {mid}")
        elif mega_url is not None:
            text = f"**#UPLOAD_LOG** \n\n**User ID:** `{uid}` \n**Chat ID:** `{mid}` \n**Url:** {mega_url}"
            await _safe_send_text(text)
        return

    if import_logs:
        text = f"**#IMPORT_LOG** \n\n**User ID:** `{uid}` \n**Chat ID:** `{mid}` \n**Origin Url:** {mega_url}"
        await _safe_send_text(text)
        return


# Send or print errors (async)
async def send_errors(e):
    """
    Send errors to the log channel if configured, otherwise print them.
    This function is defensive and will not call itself on failure.
    """
    # normalize channel id
    try:
        c_id = int(Config.LOGS_CHANNEL) if Config.LOGS_CHANNEL else 0
    except Exception:
        c_id = 0

    text = f"**#Error** \n`{e}`\n\nTraceback:\n{traceback.format_exc()}"

    if c_id:
        try:
            await client.send_message(chat_id=c_id, text=text)
        except Exception as ex:
            # avoid recursion — just print
            print(f"[send_errors] Failed to send error to LOGS_CHANNEL: {ex}\nOriginal error: {e}")
    else:
        # no channel configured — print to stdout
        print(ERROR_TEXT.format(e))
