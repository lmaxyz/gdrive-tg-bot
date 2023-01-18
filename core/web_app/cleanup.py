from aiohttp.web import Application


async def _db_disconnect(application: Application):
    await application['db_client'].disconnect()


async def _stop_tg_bot(application: Application):
    await application['bot_manager'].stop_tg_bot()


cleanup_actions = (
    _db_disconnect,
    _stop_tg_bot,
)