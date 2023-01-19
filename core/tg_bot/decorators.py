from .types import HandlerType

_AUTHENTICATION_FAILURE_MESSAGE = "❌ Authentication failed.\nTry again later."


def with_user_authentication(handler_type: HandlerType):
    auth_fail_reply = _auth_fail_replies_map[handler_type]

    def inner(handler):
        async def with_auth(bot_manager, tg_app, message_or_callback):
            user_id = message_or_callback.from_user.id
            if (user_creds := await bot_manager.authenticator.authenticate_user(user_id)) is None:
                user_creds = await bot_manager.authenticator.start_authorization(message_or_callback.from_user.id)

            if user_creds is not None:
                await handler(bot_manager, tg_app, message_or_callback, user_creds)
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
