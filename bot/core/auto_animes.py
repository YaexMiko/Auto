from asyncio import gather, create_task, sleep as asleep, Event
from asyncio.subprocess import PIPE
from os import path as ospath, system
from aiofiles import open as aiopen
from aiofiles.os import remove as aioremove
from traceback import format_exc
from base64 import urlsafe_b64encode
from time import time
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot import bot, bot_loop, Var, ani_cache, ffQueue, ffLock, ff_queued
from .tordownload import TorDownloader
from .database import db
from .func_utils import getfeed, encode, editMessage, sendMessage, convertBytes
from .text_utils import TextEditor
from .ffencoder import FFEncoder
from .tguploader import TgUploader
from .reporter import rep

btn_formatter = {
    '1080':'𝟭𝟬𝟴𝟬𝗽', 
    '720':'𝟳𝟮𝟬𝗽',
    '480':'𝟰𝟴𝟬𝗽',
    }

async def fetch_animes():
    await rep.report("Fetch Animes Started !!", "info")
    while True:
        await asleep(60)
        if ani_cache['fetch_animes']:
            for link in Var.RSS_ITEMS:
                if (info := await getfeed(link, 0)):
                    bot_loop.create_task(get_animes(info.title, info.link))

async def get_animes(name, torrent, force=False):
    try:
        aniInfo = TextEditor(name)
        await aniInfo.load_anilist()
        ani_id, ep_no = aniInfo.adata.get('id'), aniInfo.pdata.get("episode_number")
        if ani_id not in ani_cache['ongoing']:
            ani_cache['ongoing'].add(ani_id)
        elif not force:
            return
        if not force and ani_id in ani_cache['completed']:
            return
        if force or (not (ani_data := await db.getAnime(ani_id)) \
            or (ani_data and not (qual_data := ani_data.get(ep_no))) \
            or (ani_data and qual_data and not all(qual for qual in qual_data.values()))):
            
            if "[Batch]" in name:
                await rep.report(f"𝚃𝚘𝚛𝚛𝚎𝚗𝚝 𝚂𝚔𝚒𝚙𝚙𝚎𝚍!\n\n{name}", "𝚆𝚊𝚛𝚗𝚒𝚗𝚐")
                return
            
            await rep.report(f"𝙽𝚎𝚠 𝙰𝚗𝚒𝚖𝚎 𝚃𝚘𝚛𝚛𝚎𝚗𝚝 𝙵𝚘𝚞𝚗𝚍!\n\n{name}", "𝙸𝚗𝚏𝚘")
            post_msg = await bot.send_photo(
                Var.MAIN_CHANNEL,
                photo=await aniInfo.get_poster(),
                caption=await aniInfo.get_caption()
            )
            #post_msg = await sendMessage(Var.MAIN_CHANNEL, (await aniInfo.get_caption()).format(await aniInfo.get_poster()), invert_media=True)
            
            await asleep(1.5)
            stat_msg = await sendMessage(Var.MAIN_CHANNEL, f"<blockquote>‣ <b>𝙰𝚗𝚒𝚖𝚎 𝙽𝚊𝚖𝚎 :</b> <b>{name}</b></blockquote>\n\n<blockquote><b>𝙳𝚘𝚠𝚗𝚕𝚘𝚊𝚍𝚒𝚗𝚐 𝚈𝚘𝚞𝚛 𝙴𝚙𝚒𝚜𝚘𝚍𝚎...</b></blockquote>")
            dl = await TorDownloader("./downloads").download(torrent, name)
            if not dl or not ospath.exists(dl):
                await rep.report(f"𝙵𝚒𝚕𝚎 𝙳𝚘𝚠𝚗𝚕𝚘𝚊𝚍 𝙸𝚗𝚌𝚘𝚖𝚙𝚕𝚎𝚝𝚎, 𝚃𝚛𝚢 𝙰𝚐𝚊𝚒𝚗", "𝙴𝚛𝚛𝚘𝚛")
                await stat_msg.delete()
                return

            post_id = post_msg.id
            ffEvent = Event()
            ff_queued[post_id] = ffEvent
            if ffLock.locked():
                await editMessage(stat_msg, f"<blockquote>‣ <b>𝙰𝚗𝚒𝚖𝚎 𝙽𝚊𝚖𝚎 :</b> <b>{name}</b></blockquote>\n\n<blockquote><b>𝚀𝚞𝚎𝚞𝚎𝚍 𝚃𝚘 𝙴𝚗𝚌𝚘𝚍𝚎 𝚈𝚘𝚞𝚛 𝙴𝚙𝚒𝚜𝚘𝚍𝚎...</b></blockquote>")
                await rep.report("𝙰𝚍𝚍𝚎𝚍 𝚃𝚊𝚜𝚔 𝚃𝚘 𝚀𝚞𝚎𝚞𝚎...", "𝙸𝚗𝚏𝚘")
            await ffQueue.put(post_id)
            await ffEvent.wait()
            
            await ffLock.acquire()
            btns = []
            for qual in Var.QUALS:
                filename = await aniInfo.get_upname(qual)
                await editMessage(stat_msg, f"<blockquote>‣ <b>𝙰𝚗𝚒𝚖𝚎 𝙽𝚊𝚖𝚎 :</b> <b>{name}</b></blockquote>\n\n<blockquote><b>𝚁𝚎𝚊𝚍𝚢 𝚃𝚘 𝙴𝚗𝚌𝚘𝚍𝚎 𝚈𝚘𝚞𝚛 𝙴𝚙𝚒𝚜𝚘𝚍𝚎...</b></blockquote>")
                
                await asleep(1.5)
                await rep.report("𝚂𝚝𝚊𝚛𝚝𝚒𝚗𝚐 𝙴𝚗𝚌𝚘𝚍𝚎...", "𝙸𝚗𝚏𝚘")
                try:
                    out_path = await FFEncoder(stat_msg, dl, filename, qual).start_encode()
                except Exception as e:
                    await rep.report(f"𝙴𝚛𝚛𝚘𝚛: {e}, 𝙲𝚊𝚗𝚌𝚕𝚕𝚎𝚍,  𝚁𝚎𝚝𝚛𝚢 𝙰𝚐𝚊𝚒𝚗 !", "𝙴𝚛𝚛𝚘𝚛")
                    await stat_msg.delete()
                    ffLock.release()
                    return
                await rep.report("𝚂𝚞𝚌𝚌𝚎𝚜𝚏𝚞𝚕𝚕𝚢 𝙲𝚘𝚖𝚙𝚛𝚎𝚜𝚜𝚎𝚍 𝙽𝚘𝚠 𝙶𝚘𝚒𝚗𝚐 𝚃𝚘 𝚄𝚙𝚕𝚘𝚊𝚍...", "info")
                
                await editMessage(stat_msg, f"<blockquote>‣ <b>𝙰𝚗𝚒𝚖𝚎 𝙽𝚊𝚖𝚎 :</b> <b>{filename}</b></blockquote>\n\n<blockquote><b>𝚁𝚎𝚊𝚍𝚢 𝚃𝚘 𝚄𝚙𝚕𝚘𝚊𝚍 𝚈𝚘𝚞𝚛 𝙴𝚙𝚒𝚜𝚘𝚍𝚎...</b></blockquote>")
                await asleep(1.5)
                try:
                    msg = await TgUploader(stat_msg).upload(out_path, qual)
                except Exception as e:
                    await rep.report(f"𝙴𝚛𝚛𝚘𝚛: {e}, 𝙲𝚊𝚗𝚌𝚕𝚕𝚎𝚍,  𝚁𝚎𝚝𝚛𝚢 𝙰𝚐𝚊𝚒𝚗 !", "𝙴𝚛𝚛𝚘𝚛")
                    await stat_msg.delete()
                    ffLock.release()
                    return
                await rep.report("𝚂𝚞𝚌𝚌𝚎𝚜𝚏𝚞𝚕𝚕𝚢 𝚄𝚙𝚕𝚘𝚊𝚍𝚎𝚍 𝙵𝚒𝚕𝚎 𝙸𝚗𝚝𝚘 𝚃𝚐...", "info")
                
                msg_id = msg.id
                link = f"https://telegram.me/{(await bot.get_me()).username}?start={await encode('get-'+str(msg_id * abs(Var.FILE_STORE)))}"
                
                if post_msg:
                    if len(btns) != 0 and len(btns[-1]) == 1:
                        btns[-1].insert(1, InlineKeyboardButton(f"{btn_formatter[qual]} - {convertBytes(msg.document.file_size)}", url=link))
                    else:
                        btns.append([InlineKeyboardButton(f"{btn_formatter[qual]} - {convertBytes(msg.document.file_size)}", url=link)])
                    await editMessage(post_msg, post_msg.caption.html if post_msg.caption else "", InlineKeyboardMarkup(btns))
                    
                await db.saveAnime(ani_id, ep_no, qual, post_id)
                bot_loop.create_task(extra_utils(msg_id, out_path))
            ffLock.release()
            
            await stat_msg.delete()
            await aioremove(dl)
        ani_cache['completed'].add(ani_id)
    except Exception as error:
        await rep.report(format_exc(), "error")

async def extra_utils(msg_id, out_path):
    msg = await bot.get_messages(Var.FILE_STORE, message_ids=msg_id)

    if Var.BACKUP_CHANNEL != 0:
        for chat_id in Var.BACKUP_CHANNEL.split():
            await msg.copy(int(chat_id))
            
    # MediaInfo, ScreenShots, Sample Video ( Add-ons Features )
