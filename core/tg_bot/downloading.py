

class DownloadManager:
    def __init__(self, tg_client, process_message):
        self._tg_client = tg_client
        self._process_message = process_message

    async def download_file(self, file_id, total_file_size):
        file = await self._tg_client.download_media(file_id, in_memory=True, progress=self.update_progress,
                                                    progress_args=(total_file_size,))
        return _CustomFileBuffer(file.getbuffer())

    async def update_progress(self, current, _total, total_file_size):
        await self._process_message.edit_text(f"File downloading...\n**{current * 100 / total_file_size:.1f}%**")


class _CustomFileBuffer:
    _mem_link = None

    def __init__(self, mem_link):
        self._mem_link = mem_link

    def read(self):
        return bytes(self._mem_link)
