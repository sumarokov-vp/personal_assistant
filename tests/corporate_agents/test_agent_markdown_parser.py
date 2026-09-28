from src.corporate_agents.repos import AgentMarkdownParser


def test_claude_agent_file_with_quoted_multiline_description() -> None:
    text = (
        "---\n"
        "name: accountant\n"
        'description: "Бухгалтер.\\n\\nПримеры: \\"прими\\""\n'
        "tools: Read, Grep\n"
        "model: sonnet\n"
        "---\n"
        "\n"
        "# Роль\n"
        "Ты бухгалтер.\n"
    )

    parsed = AgentMarkdownParser().parse(text)

    assert parsed is not None
    assert parsed.fields["name"] == "accountant"
    assert parsed.fields["description"] == 'Бухгалтер.\n\nПримеры: "прими"'
    assert parsed.body == "# Роль\nТы бухгалтер."


def test_block_scalars_and_lists_do_not_break_frontmatter() -> None:
    text = (
        "---\n"
        "name: 'юрист ''старший'''\n"
        "description: >\n"
        "  Проверяет договоры\n"
        "  поставки.\n"
        "\n"
        "  Готовит заключение.\n"
        "tools:\n"
        "  - Read\n"
        "  - Grep\n"
        "notes: |\n"
        "  строка один\n"
        "  строка два\n"
        "---\n"
        "Инструкция\n"
    )

    parsed = AgentMarkdownParser().parse(text)

    assert parsed is not None
    assert parsed.fields["name"] == "юрист 'старший'"
    assert (
        parsed.fields["description"]
        == "Проверяет договоры поставки.\nГотовит заключение."
    )
    assert parsed.fields["notes"] == "строка один\nстрока два"


def test_unclosed_frontmatter_or_quote_is_rejected() -> None:
    parser = AgentMarkdownParser()

    assert parser.parse("---\nname: юрист\nтело без закрывающей черты\n") is None
    assert parser.parse('---\nname: "юрист\n---\nтело\n') is None
    assert parser.parse("---\n  отступ до ключа\n---\nтело\n") is None
