from datetime import datetime

from src.knowledge_intake import IntakeReport

RUN_LINE_PREFIX = "knowledge_intake run"


class IntakeRunLine:
    def render(
        self, started_at: datetime, duration_seconds: float, report: IntakeReport
    ) -> str:
        fetched = (
            len(report.merged)
            + len(report.declined)
            + len(report.rejected)
            + report.unpublished
        )
        push = "error" if report.publish_error else "ok"
        return (
            f"{RUN_LINE_PREFIX} started={started_at:%Y-%m-%dT%H:%M:%SZ} "
            f"duration={duration_seconds:.1f}s fetched={fetched} "
            f"merged={len(report.merged)} declined={len(report.declined)} "
            f"rejected={len(report.rejected)} push={push}"
        )
