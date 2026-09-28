import logging
from pathlib import Path

import pytest

from src.corporate_agents import AgentLayer, AgentNotFoundError, build_agent_catalog
from tests.corporate_agents.conftest import agent_markdown, commit_all, git, write_agent


def test_list_returns_agents_of_both_layers(tmp_path: Path) -> None:
    corporate, personal = tmp_path / "corporate", tmp_path / "personal"
    write_agent(
        corporate,
        "lawyer.md",
        agent_markdown("юрист", "Проверяет договоры", "Ты юрист."),
    )
    write_agent(
        personal,
        "coach.md",
        agent_markdown("тренер", "Планирует тренировки", "Ты тренер."),
    )

    summaries = build_agent_catalog(corporate, personal).list()

    assert {(summary.name, summary.layer) for summary in summaries} == {
        ("юрист", AgentLayer.CORPORATE),
        ("тренер", AgentLayer.PERSONAL),
    }


@pytest.mark.parametrize("corporate_state", ["absent", "empty", "not_configured"])
def test_without_corporate_layer_only_personal_agents(
    tmp_path: Path, corporate_state: str
) -> None:
    corporate = tmp_path / "corporate"
    if corporate_state == "empty":
        corporate.mkdir()
    personal = tmp_path / "personal"
    write_agent(
        personal,
        "coach.md",
        agent_markdown("тренер", "Планирует тренировки", "Ты тренер."),
    )

    catalog = build_agent_catalog(
        None if corporate_state == "not_configured" else corporate, personal
    )

    assert [(summary.name, summary.layer) for summary in catalog.list()] == [
        ("тренер", AgentLayer.PERSONAL)
    ]


def test_same_name_is_taken_from_corporate_layer_with_conflict_logged(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    corporate, personal = tmp_path / "corporate", tmp_path / "personal"
    write_agent(
        corporate,
        "lawyer.md",
        agent_markdown("юрист", "Корпоративный", "Правила компании."),
    )
    write_agent(
        personal, "my_lawyer.md", agent_markdown("Юрист", "Личный", "Мои правила.")
    )

    with caplog.at_level(logging.WARNING):
        definition = build_agent_catalog(corporate, personal).get("юрист")

    assert definition.layer is AgentLayer.CORPORATE
    assert definition.instruction == "Правила компании."
    assert "Agent name conflict" in caplog.text
    assert "my_lawyer.md" in caplog.text


def test_get_matches_name_case_insensitively(tmp_path: Path) -> None:
    corporate = tmp_path / "corporate"
    write_agent(
        corporate,
        "lawyer.md",
        agent_markdown("юрист", "Проверяет договоры", "Ты юрист компании."),
    )

    definition = build_agent_catalog(corporate, None).get("Юрист")

    assert definition.name == "юрист"
    assert definition.description == "Проверяет договоры"
    assert definition.instruction == "Ты юрист компании."


def test_get_unknown_agent_raises(tmp_path: Path) -> None:
    with pytest.raises(AgentNotFoundError):
        build_agent_catalog(tmp_path / "corporate", tmp_path / "personal").get(
            "бухгалтер"
        )


def test_version_of_plain_directory_changes_after_file_edit(tmp_path: Path) -> None:
    personal = tmp_path / "personal"
    path = write_agent(
        personal, "coach.md", agent_markdown("тренер", "Планирует", "Версия один.")
    )
    catalog = build_agent_catalog(None, personal)
    before = catalog.get("тренер").version

    path.write_text(
        agent_markdown("тренер", "Планирует", "Версия два."), encoding="utf-8"
    )
    after = catalog.get("тренер").version

    assert before.startswith("sha256:")
    assert after.startswith("sha256:")
    assert before != after


def test_version_in_git_clone_is_head_sha(tmp_path: Path) -> None:
    corporate = tmp_path / "corporate"
    corporate.mkdir()
    git(corporate, "init", "--initial-branch=main")
    path = write_agent(
        corporate, "lawyer.md", agent_markdown("юрист", "Проверяет", "Правила v1.")
    )
    first_head = commit_all(corporate, "v1")
    catalog = build_agent_catalog(corporate, None)

    assert catalog.get("юрист").version == first_head

    path.write_text(
        agent_markdown("юрист", "Проверяет", "Правила v2."), encoding="utf-8"
    )
    second_head = commit_all(corporate, "v2")

    assert catalog.get("юрист").version == second_head
    assert second_head != first_head


def test_broken_file_is_skipped_with_log(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    corporate = tmp_path / "corporate"
    write_agent(
        corporate, "lawyer.md", agent_markdown("юрист", "Проверяет", "Ты юрист.")
    )
    write_agent(
        corporate, "broken.md", '---\nname: "незакрытый\ndescription: x\n---\nтело\n'
    )
    write_agent(corporate, "no_fence.md", "name: бухгалтер\n\nтело без frontmatter\n")
    (corporate / "agents" / "latin1.md").write_bytes(
        b"---\nname: caf\xe9\ndescription: x\n---\nbody\n"
    )

    with caplog.at_level(logging.WARNING):
        names = [
            summary.name for summary in build_agent_catalog(corporate, None).list()
        ]

    assert names == ["юрист"]
    assert "broken.md" in caplog.text
    assert "no_fence.md" in caplog.text
    assert "latin1.md" in caplog.text
