from telebot import TeleBot
from telebot.types import Update

from .protocols import IUpdateGate

PROCESS_NEW_UPDATES = "process_new_updates"


class UpdateGateInstaller:
    def __init__(self, gate: IUpdateGate) -> None:
        self._gate = gate

    def install(self, bot: TeleBot) -> None:
        process_new_updates = bot.process_new_updates

        def process_admitted_updates(updates: list[Update]) -> None:
            self._confirm_received(bot, updates)
            process_new_updates(self._gate.admitted(updates))

        setattr(bot, PROCESS_NEW_UPDATES, process_admitted_updates)

    # TeleBot сдвигает offset только по тем апдейтам, что дошли до process_new_updates:
    # без этого отброшенные апдейты приходили бы из getUpdates снова и снова
    @staticmethod
    def _confirm_received(bot: TeleBot, updates: list[Update]) -> None:
        for update in updates:
            if bot.last_update_id is None or update.update_id > bot.last_update_id:
                bot.last_update_id = update.update_id
