from .types import HandlerType
from core.google import GoogleSession

_AUTHENTICATION_FAILURE_MESSAGE = "❌ Authentication failed.\nTry again later."


def with_google_session(handler_type: HandlerType):
    auth_fail_reply = _auth_fail_replies_map[handler_type]

    def inner(handler):
        async def with_auth(tg_app, message_or_callback):
            user_id = message_or_callback.from_user.id
            if not (google_session := await GoogleSession(tg_app.google, tg_app.db_client, user_id)).is_authorized():
                auth_url = await google_session.get_authorization_url()
                await tg_app.send_authorization_request(user_id, auth_url)
                await google_session.wait_for_authorization()

            if google_session.is_authorized():
                message_or_callback.from_user.google_session = google_session
                await handler(tg_app, message_or_callback)
            else:
                await auth_fail_reply(message_or_callback)

        return with_auth

    return inner


async def _message_reply(message):
    await message.reply(_AUTHENTICATION_FAILURE_MESSAGE)


async def _callback_reply(callback):
    await callback.message.reply(_AUTHENTICATION_FAILURE_MESSAGE)


_auth_fail_replies_map = {
    HandlerType.Message: _message_reply,
    HandlerType.Callback: _callback_reply
}
