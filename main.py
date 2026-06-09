import asyncio
import logging

from app.bot import run_bot


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


if __name__ == "__main__":
    setup_logging()
    asyncio.run(run_bot())
