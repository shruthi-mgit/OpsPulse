import asyncpg
import logging

logger = logging.getLogger("sequence-generator")


async def generate_prefixed_id(
    db_pool: asyncpg.Pool,
    prefix: str,
    number_format: str = "%d",
    sequence_name: str = None,
    schema: str = "ik_opspulse_b1",
) -> str:

    # ✅ use separate sequence per prefix
    if sequence_name is None:
        sequence_name = f"seq_{prefix.lower()}"

    try:
        async with db_pool.acquire() as conn:

            # set schema
            await conn.execute(f'SET search_path TO "{schema}"')

            # create sequence per prefix
            await conn.execute(f"""
                CREATE SEQUENCE IF NOT EXISTS "{schema}".{sequence_name}
                START 1;
            """)

            # get next value
            seq_val = await conn.fetchval(
                f'SELECT nextval(\'"{schema}".{sequence_name}\')'
            )

            formatted_id = prefix + (number_format % seq_val)

            return formatted_id

    except Exception as e:
        logger.error(f"Error generating ID: {e}")
        raise