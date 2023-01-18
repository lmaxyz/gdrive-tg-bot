import json
import sqlite3

from aiosqlite import connect, Connection


class DBClient:
    def __init__(self, connection: Connection):
        self._connection = connection

    async def disconnect(self):
        try:
            await self._connection.close()
        except ValueError:
            pass

    @classmethod
    async def connect(cls, file_path: str):
        connection = await connect(file_path)
        db = cls(connection)
        await db.__create_working_table()
        return db

    async def __create_working_table(self):
        await self._connection.execute(
            "CREATE TABLE IF NOT EXISTS user_settings ("
            "user_id int primary key,"
            "secret text NOT NULL,"
            "creds text,"
            "saving_dir text);"
        )
        await self._connection.commit()

    async def init_auth(self, user_id: int, secret: str):
        try:
            await self._connection.execute("INSERT INTO user_settings VALUES (?,?, NULL);", (user_id, secret))
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                await self._connection.execute("UPDATE user_settings SET secret=? WHERE user_id=?", (secret, user_id))

        await self._connection.commit()

    async def delete_auth(self, user_id: int):
        await self._connection.execute("DELETE FROM user_settings WHERE user_id=?", (user_id,))
        await self._connection.commit()

    async def save_user_creds(self, data: str, secret: str = None, user_id: int = None):
        if secret:
            await self._connection.execute("UPDATE user_settings SET creds=? WHERE secret=?;", (data, secret))
        elif user_id is not None:
            await self._connection.execute("UPDATE user_settings SET creds=? WHERE user_id=?;", (data, user_id))
        else:
            raise ValueError("`secret` or `user_id` must be given to save credentials.")

        await self._connection.commit()

    async def set_saving_dir(self, user_id: int, saving_dir: str):
        await self._connection.execute("UPDATE user_settings SET saving_dir=? WHERE user_id=?", (saving_dir, user_id))
        await self._connection.commit()

    async def get_saving_dir(self, user_id: int) -> str:
        await self._connection.execute("SELECT saving_dir FROM user_settings WHERE user_id=?", (user_id,))

    async def is_secret_exists(self, secret: str) -> bool:
        cursor = await self._connection.execute("SELECT 1 FROM user_settings WHERE secret=?;", (secret,))
        return await cursor.fetchone() is not None

    async def get_user_creds(self, user_id: int) -> dict:
        cursor = await self._connection.execute("SELECT creds FROM user_settings WHERE user_id=?;", (user_id,))

        if (result := await cursor.fetchone()) is not None and result[0] is not None:
            return json.loads(result[0])

        return None
