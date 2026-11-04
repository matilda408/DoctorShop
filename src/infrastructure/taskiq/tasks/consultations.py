from dishka.integrations.taskiq import FromDishka, inject
from loguru import logger

from src.application.use_cases.consultation.commands import ExpireConsultations
from src.infrastructure.taskiq.broker import broker


@broker.task(schedule=[{"cron": "*/5 * * * *"}], retry_on_error=True)
@inject(patch_module=True)
async def expire_consultations(
    expire: FromDishka[ExpireConsultations],
) -> None:
    count = await expire.system()
    if count:
        logger.info("Expired '{}' consultations", count)
