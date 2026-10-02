from collections.abc import Set

from workers.mcp.project.project_resolution import ProjectResolution


class ProjectResolver:
    def __init__(self, allowed_projects: Set[str]) -> None:
        self._allowed_projects = frozenset(allowed_projects)

    def resolve(self, header: str | None, argument: object) -> ProjectResolution:
        header_project = (header or "").strip()
        if header_project:
            return ProjectResolution(
                project=header_project, source="header", allowed=True
            )
        argument_project = "" if argument is None else str(argument).strip()
        if argument_project:
            return ProjectResolution(
                project=argument_project,
                source="param",
                allowed=argument_project in self._allowed_projects,
            )
        return ProjectResolution(project=None, source="none", allowed=True)
