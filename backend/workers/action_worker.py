"""
Action completion worker.
Uses a simple polling mechanism instead of BullMQ for Python compatibility.
In production, consider using Celery with Redis broker.
"""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config import get_settings, refresh_settings_if_changed
from app.models import Action, ActionStatus
from app.services.action_service import ActionService

settings = get_settings()
# Apply admin overrides on worker startup
refresh_settings_if_changed()
logger = logging.getLogger(__name__)

engine = create_async_engine(settings.DATABASE_URL)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def check_pending_actions():
    """Check for actions that should be completed."""
    async with async_session() as db:
        result = await db.execute(
            select(Action).where(
                Action.status == ActionStatus.PENDING,
                Action.finish_at <= datetime.now(timezone.utc),
            )
        )
        actions = list(result.scalars().all())

        action_service = ActionService(db)

        for action in actions:
            try:
                if action.is_cooperation and action.cooperation_target_id:
                    await action_service.complete_cooperation(action.id)
                    logger.info(f"Completed cooperation {action.id}")
                else:
                    await action_service.complete_action(action.id)
                    logger.info(f"Completed action {action.id}")
            except Exception as e:
                logger.error(f"Failed to complete action {action.id}: {e}")


async def worker_loop(interval: int = 5):
    """Main worker loop, checking every N seconds."""
    logger.info("Action worker started")
    while True:
        try:
            refresh_settings_if_changed()
            await check_pending_actions()
        except Exception as e:
            logger.error(f"Worker error: {e}")
        await asyncio.sleep(interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(worker_loop())
