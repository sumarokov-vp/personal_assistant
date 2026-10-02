from typing import Any

PROJECT_ARGUMENT = "project"
PROJECT_PARAMETER_SCHEMA = {
    "type": "string",
    "description": "Имя проекта из инструкции проекта приложения",
}


def with_project_parameter(input_schema: dict[str, Any]) -> dict[str, Any]:
    properties = input_schema.get("properties", {})
    if PROJECT_ARGUMENT in properties:
        raise ValueError(f"Tool input schema already has '{PROJECT_ARGUMENT}' property")
    return {
        **input_schema,
        "properties": {**properties, PROJECT_ARGUMENT: PROJECT_PARAMETER_SCHEMA},
    }


def without_project_argument(arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        name: value for name, value in arguments.items() if name != PROJECT_ARGUMENT
    }
