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
            "CREATE TABLE IF NOT EXISTS creds (user_id int primary key, secret text NOT NULL, data text);"
        )
        await self._connection.commit()

    async def init_auth(self, user_id: int, secret: str):
        try:
            await self._connection.execute("INSERT INTO creds VALUES (?,?, NULL);", (user_id, secret))
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                await self._connection.execute("UPDATE creds SET secret=? WHERE user_id=?", (secret, user_id))

        await self._connection.commit()

    async def delete_auth(self, user_id: int):
        await self._connection.execute("DELETE FROM creds WHERE user_id=?", (user_id,))
        await self._connection.commit()

    async def save_user_creds(self, secret: str, data: str):
        await self._connection.execute("UPDATE creds SET data=? WHERE secret=?;", (data, secret))
        await self._connection.commit()

    async def get_secret(self, secret: str) -> str | None:
        cursor = await self._connection.execute("SELECT secret FROM creds WHERE secret=?;", (secret,))

        if (result := await cursor.fetchone()) is not None:
            return result[0]
        print(result)
        return None

    async def get_user_creds(self, user_id: int) -> dict | None:
        cursor = await self._connection.execute("SELECT data FROM creds WHERE user_id=?;", (user_id,))

        if (result := await cursor.fetchone()) is not None and result[0] is not None:
            return json.loads(result[0])

        return None
