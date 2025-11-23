# Copyright (c) 2021 Itz-fork
# Don't kang this else your dad is gae

import os
import re
import shutil
import subprocess
import traceback

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from functools import partial
from asyncio import get_running_loop

from megadl.helpers_nexa.account import m
from megadl.helpers_nexa.mega_help import humanbytes, send_errors, send_logs
from megadl.helpers_nexa.up_helper import guess_and_send
from config import Config

# ---------------------------
# small helper: split large files without fsplit
# ---------------------------
def split_large_file(input_file, output_dir, chunk_size=2040108421):
    """
    Split a file into parts of size chunk_size (bytes).
    Parts are written to output_dir with suffix .part1, .part2, ...
    """
    os.makedirs(output_dir, exist_ok=True)
    part = 1

    with open(input_file, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break

            out_path = os.path.join(output_dir, f"{os.path.basename(input_file)}.part{part}")
            with open(out_path, "wb") as o:
                o.write(chunk)

            part += 1

def split_files(input_file, out_base_path):
    split_large_file(
        input_file=input_file,
        output_dir=out_base_path,
        chunk_size=2040108421
    )

# ---------------------------
# config + constants
# ---------------------------
# path we gonna give the download
basedir = Config.DOWNLOAD_LOCATION
# Telegram's max file size
TG_MAX_FILE_SIZE = Config.TG_MAX_SIZE

# Automatic Url Detect (From stackoverflow. Can't find link lol)
MEGA_REGEX = (r"^((?:https?:)?\/\/)"
              r"?((?:www)\.)"
              r"?((?:mega\.nz))"
              r"(\/)([-a-zA-Z0-9()@:%_\+.~#?&//=]*)([\w\-]+)(\S+)?$")

# Github Repo (Don't remove this)
GITHUB_REPO = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "Source Code 🗂", url="https://github.com/Itz-fork/Mega.nz-Bot"
            )
        ],
        [
            InlineKeyboardButton(
                "Support Group 🆘", url="https://t.me/Nexa_bots"
            )
        ]
    ]
)

# Cancel Button
CANCEL_BUTTN = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                "Cancel ❌", callback_data="cancelvro"
            )
        ]
    ]
)

# ---------------------------
# Helpers for mega folder detection & download
# ---------------------------
def is_mega_folder(url: str) -> bool:
    """Detect common folder link patterns (imperfect but works)."""
    if not url:
        return False
    url = url.strip()
    # Public folder links sometimes include #F! token or /folder/
    return ("/folder/" in url) or ("#F!" in url) or ("/#F!" in url)

def nexa_mega_runner(command):
    run = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    shell_output = run.stdout.read()[:-1].decode("utf-8")
    return shell_output

# Old DownloadMegaLink used to call m.download_url without returning anything.
# We'll wrap it and make it robust.
def DownloadMegaLink(url, dest_dir, download_msg):
    """
    Download using mega.py client 'm'.
    The mega.download_url may save a file or a folder into dest_dir.
    """
    try:
        # Ensure destination exists
        os.makedirs(dest_dir, exist_ok=True)

        # Use the existing mega client method to download URL (file or folder)
        # This function may be blocking, so caller should run it in executor.
        # It generally downloads into the dest_dir and returns a local path, but some forks/versions may return None.
        try:
            ret = m.download_url(url, dest_path=dest_dir, statusdl_msg=download_msg)
        except TypeError:
            # older/newer signature mismatch – try without statusdl_msg
            ret = m.download_url(url, dest_path=dest_dir)

        # If ret is None, we rely on dest_dir contents (downloaded files placed there)
        return ret
    except Exception as e:
        # send errors to your error handling helper
        send_errors(e)
        # re-raise so caller knows
        raise

# ---------------------------
# Pyrogram handler (mega.py based)
# ---------------------------
@Client.on_message(filters.regex(MEGA_REGEX) & filters.private)
async def megadl_megapy(_, message: Message):
    # Auth check: keep existing logic
    try:
        if Config.IS_PUBLIC_BOT == "False":
            if message.from_user.id not in Config.AUTH_USERS:
                return await message.reply_text(
                    "**Sorry this bot isn't a Public Bot 🥺! But You can make your own bot ☺️, Click on Below Button!**",
                    reply_markup=GITHUB_REPO
                )
            elif Config.IS_PUBLIC_BOT == "True":
                pass
    except Exception as e:
        return await send_errors(e=e)

    url = message.text.strip()
    userpath = str(message.from_user.id)
    the_chat_id = str(message.chat.id)
    megadl_path = os.path.join(basedir, userpath)

    # Prevent concurrent downloads per user
    if os.path.isdir(megadl_path):
        return await message.reply_text("`Already One Process is Going On. Please wait until it's finished!`")
    else:
        os.makedirs(megadl_path, exist_ok=True)

    download_msg = None
    try:
        download_msg = await message.reply_text("**Starting to Download The Content! This may take while 😴**", reply_markup=CANCEL_BUTTN)
        await send_logs(user_id=userpath, mchat_id=the_chat_id, mega_url=url, download_logs=True)

        # Run blocking download in threadpool
        loop = get_running_loop()
        # use partial properly: pass function and args, do not call it
        download_task = partial(DownloadMegaLink, url, megadl_path, download_msg)
        ret = await loop.run_in_executor(None, download_task)

        # After download, collect files under user's dir
        # ret may be a file path or folder path or None. We will walk megadl_path to get all files.
        folder_f = []
        for dirpath, _, filenames in os.walk(megadl_path):
            for fname in filenames:
                folder_f.append(os.path.join(dirpath, fname))

        if not folder_f:
            # nothing downloaded
            await download_msg.edit("**Error:** Download finished but no files found.")
            shutil.rmtree(megadl_path, ignore_errors=True)
            return

        await download_msg.edit("**Successfully Downloaded The Content!**")
    except Exception as e:
        # Report error, cleanup
        try:
            if download_msg:
                await download_msg.edit(f"**Error:** `{e}`")
        except Exception:
            pass
        shutil.rmtree(megadl_path, ignore_errors=True)
        await send_errors(e)
        return

    # If user cancelled the process bot will return into telegram again lmao
    if not os.path.isdir(megadl_path):
        # cleanup done elsewhere
        return

    # Now upload each file (and split if large)
    try:
        for mg_file in folder_f:
            # ensure actual file exists
            if not os.path.isfile(mg_file):
                continue

            # get correct file size (per-file), handle any exception
            try:
                file_size = os.path.getsize(mg_file)
            except Exception:
                file_size = None

            # If size is unknown, treat as large to be safe (or you can skip)
            if file_size is None:
                # try to continue, but inform user
                await download_msg.edit(f"⚠️ Could not determine size of `{os.path.basename(mg_file)}`. Uploading anyway.")
                try:
                    await guess_and_send(mg_file, int(the_chat_id), "cache", download_msg)
                except Exception as send_e:
                    await download_msg.edit(f"Failed to upload {os.path.basename(mg_file)}: {send_e}")
                    await send_errors(send_e)
                continue

            # If file is larger than telegram limit, split first
            if file_size > Config.TG_MAX_SIZE:
                base_splt_out_dir = os.path.join(megadl_path, "splitted_files")
                await download_msg.edit("`Large File Detected, Trying to split it!`")
                # run splitter in executor properly
                loop = get_running_loop()
                split_task = partial(split_files, mg_file, base_splt_out_dir)
                await loop.run_in_executor(None, split_task)

                # After splitting, send all parts found under split dir
                split_out_dir = []
                for dirpath, _, filenames in os.walk(base_splt_out_dir):
                    for fname in filenames:
                        split_out_dir.append(os.path.join(dirpath, fname))

                # sort to preserve order
                split_out_dir.sort()
                for spl_f in split_out_dir:
                    try:
                        await guess_and_send(spl_f, int(the_chat_id), "cache", download_msg)
                    except Exception as e:
                        await download_msg.edit(f"Failed to upload split part `{os.path.basename(spl_f)}`: {e}")
                        await send_errors(e)
            else:
                # normal upload
                try:
                    await guess_and_send(mg_file, int(the_chat_id), "cache", download_msg)
                except Exception as e:
                    await download_msg.edit(f"Failed to upload `{os.path.basename(mg_file)}`: {e}")
                    await send_errors(e)
    except Exception as e:
        # catch any unexpected error during upload loop
        await download_msg.edit(f"**Error:** \n`{e}`")
        await send_errors(e)
    finally:
        # Clean up user folder
        try:
            shutil.rmtree(megadl_path, ignore_errors=True)
            print("Successfully Removed Downloaded File and the folder!")
        except Exception as e:
            await send_errors(e)


# ---------------------------
# Uses megatools cli (optional handler left as-is)
# ---------------------------
@Client.on_message(filters.command("megadl") & filters.private)
async def megadl_megatools(_, message: Message):
    # To use bot private or public
    try:
        if Config.IS_PUBLIC_BOT == "False":
            if message.from_user.id not in Config.AUTH_USERS:
                return await message.reply_text("**Sorry this bot isn't a Public Bot 🥺! But You can make your own bot ☺️, Click on Below Button!**", reply_markup=GITHUB_REPO)
            elif Config.IS_PUBLIC_BOT == "True":
                pass
    except Exception as e:
        return await send_errors(e)
    # parse url after command
    parts = message.text.split(None, 1)
    if len(parts) < 2:
        return await message.reply_text("Usage: /megadl <mega_link>")
    url = parts[1].strip()
    if not re.match(MEGA_REGEX, url):
        return await message.reply("`This isn't a mega url!`")
    userpath = str(message.from_user.id)
    the_chat_id = str(message.chat.id)
    megadl_path = os.path.join(basedir, userpath)
    # Temp fix for the https://github.com/Itz-fork/Mega.nz-Bot/issues/11
    if os.path.isdir(megadl_path):
        return await message.reply_text("`Already One Process is Going On. Please wait until it's finished!`")
    else:
        os.makedirs(megadl_path, exist_ok=True)
    try:
        download_msg = await message.reply_text("**Starting to Download The Content! This may take while 😴** \n\n`Note: You can't cancel this!`")
        await send_logs(user_id=userpath, mchat_id=the_chat_id, mega_url=url, download_logs=True)
        megacmd = f"megadl --limit-speed 0 --path {megadl_path} {url}"
        loop = get_running_loop()
        await loop.run_in_executor(None, partial(nexa_mega_runner, megacmd))
        folder_f = []
        for dirpath, _, filenames in os.walk(megadl_path):
            for fname in filenames:
                folder_f.append(os.path.join(dirpath, fname))
        await download_msg.edit("**Successfully Downloaded The Content!**")
    except Exception as e:
        if os.path.isdir(megadl_path):
            await download_msg.edit(f"**Error:** `{e}`")
            shutil.rmtree(megadl_path, ignore_errors=True)
            await send_errors(e)
        return
    try:
        for mg_file in folder_f:
            if not os.path.isfile(mg_file):
                continue
            try:
                file_size = os.path.getsize(mg_file)
            except Exception:
                file_size = None

            if file_size is None:
                await download_msg.edit(f"⚠️ Could not determine size of `{os.path.basename(mg_file)}`. Uploading anyway.")
                await guess_and_send(mg_file, int(the_chat_id), "cache", download_msg)
                continue

            if file_size > Config.TG_MAX_SIZE:
                base_splt_out_dir = os.path.join(megadl_path, "splitted_files")
                await download_msg.edit("`Large File Detected, Trying to split it!`")
                loop = get_running_loop()
                await loop.run_in_executor(None, partial(split_files, mg_file, base_splt_out_dir))
                split_out_dir = []
                for dirpath, _, filenames in os.walk(base_splt_out_dir):
                    for fname in filenames:
                        split_out_dir.append(os.path.join(dirpath, fname))
                split_out_dir.sort()
                for spl_f in split_out_dir:
                    await guess_and_send(spl_f, int(the_chat_id), "cache", download_msg)
            else:
                await guess_and_send(mg_file, int(the_chat_id), "cache", download_msg)
        await download_msg.edit("**Successfully Uploaded The Content!**")
    except Exception as e:
        await download_msg.edit(f"**Error:** \n`{e}`")
        await send_errors(e)
    try:
        shutil.rmtree(megadl_path, ignore_errors=True)
        print("Successfully Removed Downloaded File and the folder!")
    except Exception as e:
        await send_errors(e)


# Replying If There is no mega url in the message
@Client.on_message(~filters.command(["start", "help", "info", "upload", "import", "megadl"]) & ~filters.regex(MEGA_REGEX) & filters.private & ~filters.media)
async def nomegaurl(_, message: Message):
    # Auth users only
    if message.from_user.id not in Config.AUTH_USERS:
        await message.reply_text("**Sorry this bot isn't a Public Bot 🥺! But You can make your own bot ☺️, Click on Below Button!**", reply_markup=GITHUB_REPO)
        return
    else:
        await message.reply_text("Sorry, I can't find a **valid mega.nz url** in your message! Can you check it again? \n\nAlso Make sure your url **doesn't** contain `mega.co.nz`. \n\n**If there is,** \n - Open that url in a web-browser and wait till webpage loads. \n - Then simply copy url of the webpage that you're in \n - Try Again")
