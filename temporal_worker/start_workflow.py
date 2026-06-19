import asyncio
from temporalio.client import Client

from workflow import ReminderCheckWorkflow

TASK_QUEUE = "reminder-task-queue"


async def main():
    client = await Client.connect("localhost:7233")

    handle = await client.start_workflow(
        ReminderCheckWorkflow.run,
        id="reminder-check-workflow",
        task_queue=TASK_QUEUE,
    )

    print(f"Started workflow. Workflow ID: {handle.id}")


if __name__ == "__main__":
    asyncio.run(main())