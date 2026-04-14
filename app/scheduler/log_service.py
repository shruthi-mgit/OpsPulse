from app.scheduler.constants import ALLOWED_TYPES
from app.scheduler.log_repository import LogRepository


class LogService:

    def __init__(self, conn):
        self.repo = LogRepository(conn)


    def validate(self, type):

        if type not in ALLOWED_TYPES:
            raise Exception("Invalid type")


    async def log_error(
        self,
        schema,
        schema_id,
        type,
        msg,
    ):

        self.validate(type)

        await self.repo.insert_error(
            schema,
            schema_id,
            type,
            msg,
        )


    async def log_success(
        self,
        schema,
        schema_id,
        type,
        msg,
    ):

        self.validate(type)

        await self.repo.insert_success(
            schema,
            schema_id,
            type,
            msg,
        )