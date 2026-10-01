from workers.scheduled_run.protocols.i_prompt_builder import IPromptBuilder


class ScheduledRunPrompt:
    def __init__(self, bot_prompt: IPromptBuilder, run_prompt: IPromptBuilder) -> None:
        self._bot_prompt = bot_prompt
        self._run_prompt = run_prompt

    def build(self) -> str:
        return f"{self._bot_prompt.build()}\n\n{self._run_prompt.build()}"
