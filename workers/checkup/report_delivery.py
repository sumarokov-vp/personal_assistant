from workers.checkup.checkup_report import CheckupReport
from workers.checkup.protocols.i_owner_notifier import IOwnerNotifier


class ReportDelivery:
    def __init__(self, notifier: IOwnerNotifier) -> None:
        self._notifier = notifier

    def deliver(self, report: CheckupReport) -> None:
        message = report.owner_message()
        if message is not None:
            self._notifier.notify(message)
