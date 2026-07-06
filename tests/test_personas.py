"""Tests for persona loading and YAML validation."""

from pathlib import Path

import yaml

from models import Persona
from services.persona_service import PersonaService

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_load_real_personas(monkeypatch):
    """All shipped personas load as Persona objects."""
    monkeypatch.chdir(REPO_ROOT)
    personas = PersonaService.load_personas()

    assert len(personas) >= 10
    for display_name, persona in personas.items():
        assert isinstance(persona, Persona)
        assert persona.name
        assert persona.goal
        assert persona.backstory
        assert "(" in display_name  # display name includes source file


def test_load_personas_from_custom_dir(tmp_path, monkeypatch):
    """Both the new (role/goal/backstory) and legacy (prompt) schemas load."""
    persona_dir = tmp_path / "personas"
    persona_dir.mkdir()
    entries = [
        {"name": "New Style", "role": "R", "goal": "G", "backstory": "B"},
        {"name": "Legacy Style", "prompt": "Legacy prompt"},
    ]
    (persona_dir / "test.yaml").write_text(yaml.safe_dump(entries), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    personas = PersonaService.load_personas()

    assert set(personas) == {"New Style (test)", "Legacy Style (test)"}
    assert personas["New Style (test)"].backstory == "B"
    assert personas["Legacy Style (test)"].backstory == "Legacy prompt"


def test_missing_dir_returns_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert PersonaService.load_personas() == {}


def test_persona_files_valid():
    """All persona YAML files use the role/goal/backstory schema."""
    persona_dir = REPO_ROOT / "personas"
    files = sorted(persona_dir.glob("*.yaml"))
    assert len(files) >= 11

    for file_path in files:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        assert isinstance(data, list), f"{file_path.name} should be a list"
        for entry in data:
            for field in ("name", "role", "goal", "backstory"):
                assert entry.get(field), f"Entry in {file_path.name} missing '{field}'"
