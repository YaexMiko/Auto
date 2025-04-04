from os import path as ospath
from aiofiles import open as aiopen
from aiofiles.os import path as aiopath, remove as aioremove, mkdir
from aiohttp import ClientSession, TCPConnector
from torrentp import TorrentDownloader
from time import time
from traceback import format_exc

from bot import LOGS
from bot.core.func_utils import handle_logs, rep

class TorDownloader:
    def __init__(self, path="."):
        self.__downdir = path
        self.__torpath = "torrents/"
    
    @handle_logs
    async def download(self, torrent, name=None):
        try:
            start_time = time()
            if torrent.startswith("magnet:"):
                torp = TorrentDownloader(torrent, self.__downdir)
                await torp.start_download()
                LOGS.info(f"Download completed in {time() - start_time:.2f} seconds")
                return ospath.join(self.__downdir, name) if name else ospath.join(self.__downdir, torp._torrent_info._info.name())
            elif torfile := await self.get_torfile(torrent):
                torp = TorrentDownloader(torfile, self.__downdir)
                await torp.start_download()
                await aioremove(torfile)
                LOGS.info(f"Download completed in {time() - start_time:.2f} seconds")
                return ospath.join(self.__downdir, torp._torrent_info._info.name())
            return None
        except Exception as e:
            await rep.report(f"Torrent download failed: {format_exc()}", "error")
            return None

    @handle_logs
    async def get_torfile(self, url):
        try:
            if not await aiopath.isdir(self.__torpath):
                await mkdir(self.__torpath)
            
            tor_name = url.split('/')[-1].split('?')[0]
            des_dir = ospath.join(self.__torpath, tor_name)
            
            connector = TCPConnector(limit=0, force_close=True, enable_cleanup_closed=True)
            async with ClientSession(connector=connector) as session:
                try:
                    async with session.get(url, timeout=60) as response:
                        if response.status != 200:
                            raise Exception(f"HTTP Error {response.status}")
                        async with aiopen(des_dir, 'wb') as file:
                            async for chunk in response.content.iter_any():
                                await file.write(chunk)
                        return des_dir
                except Exception as e:
                    await rep.report(f"Failed to download torrent file from {url}: {str(e)}", "error")
                    return None
        except Exception as e:
            await rep.report(f"Failed to get torrent file: {format_exc()}", "error")
            return None
