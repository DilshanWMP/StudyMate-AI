from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from activities import check_and_trigger_reminders


@workflow.defn
class ReminderCheckWorkflow:
    @workflow.run
    async def run(self) -> None:
        while True:
            await workflow.execute_activity(
                check_and_trigger_reminders,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(
                    maximum_attempts=3,
                    initial_interval=timedelta(seconds=2),
                ),
            )
            await workflow.sleep(timedelta(seconds=10))