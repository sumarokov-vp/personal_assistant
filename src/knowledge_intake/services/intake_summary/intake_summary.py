from src.knowledge_intake.services.entities.intake_report import IntakeReport

SHORT_SHA = 8


class IntakeSummary:
    def render(self, report: IntakeReport) -> str | None:
        if report.is_empty():
            return None
        sections = ["Приёмщик знаний"]
        if report.merged:
            sections.append(
                f"Влито ({len(report.merged)}):\n"
                + "\n".join(
                    f"- {item.plugin} · {item.topic} · {item.sender} · {item.commit_sha[:SHORT_SHA]}"
                    for item in report.merged
                )
                + _versions_line(report.versions)
            )
        if report.declined:
            sections.append(
                f"Не принято ({len(report.declined)}):\n"
                + "\n".join(
                    f"- {item.sender} · «{item.subject}» · {item.reason}"
                    for item in report.declined
                )
            )
        if report.rejected:
            sections.append(
                f"Отклонено на входе ({len(report.rejected)}):\n"
                + "\n".join(
                    f"- {item.address} · {item.reason}" for item in report.rejected
                )
            )
        if report.publish_error:
            sections.append(
                f"Вливание не прошло, писем осталось в ящике: {report.unpublished}. "
                f"Повтор — следующим прогоном.\n{report.publish_error}"
            )
        return "\n\n".join(sections)


def _versions_line(versions: dict[str, str]) -> str:
    if not versions:
        return ""
    return "\nВерсии: " + ", ".join(
        f"{plugin} {version}" for plugin, version in versions.items()
    )
