import asyncio
import sys
import os
sys.path.append(os.path.dirname(__file__))

from temporalio.client import Client
from temporalio.worker import Worker

from workflow import ReminderCheckWorkflow
from activities import check_and_trigger_reminders

TASK_QUEUE = "reminder-task-queue"


async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[ReminderCheckWorkflow],
        activities=[check_and_trigger_reminders],
    )

    print(f"Worker started. Listening on task queue: {TASK_QUEUE}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())