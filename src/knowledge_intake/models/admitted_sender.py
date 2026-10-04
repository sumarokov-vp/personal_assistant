from dataclasses import dataclass


@dataclass(frozen=True)
class AdmittedSender:
    name: str
    email: str

    def signature(self) -> str:
        return f"{self.name} <{self.email}>"
