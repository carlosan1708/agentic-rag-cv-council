import os
from pathlib import Path
from typing import Dict

import yaml

from logger import logger
from models import Persona


class PersonaService:
    @staticmethod
    def load_personas() -> Dict[str, Persona]:
        """Loads all agent personas from the personas directory and returns them as Persona objects."""
        # Use current working directory to find personas
        base_dir = Path(os.getcwd())
        persona_dir = base_dir / "personas"

        all_personas: Dict[str, Persona] = {}

        if not persona_dir.exists():
            logger.error(f"Persona directory not found at {persona_dir}")
            return {}

        logger.info(f"Loading personas from {persona_dir}")

        for file_path in persona_dir.glob("*.yaml"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if not data:
                        continue

                    for p_data in data:
                        # Map the legacy 'prompt' field to our new model if necessary
                        # Existing personas use 'name' and 'prompt'
                        name = p_data.get("name", "Unknown Specialist")
                        prompt = p_data.get("prompt", "")

                        # In the new model, we split prompt into role/goal/backstory
                        # For compatibility, we'll map them reasonably
                        persona = Persona(
                            name=name,
                            role=p_data.get("role", name),
                            goal=p_data.get("goal", f"Analyze CV as a {name}"),
                            backstory=p_data.get("backstory", prompt),
                            tools=p_data.get("tools", []),
                        )

                        # Create a unique display name including the source file
                        display_name = f"{persona.name} ({file_path.stem})"
                        all_personas[display_name] = persona

            except Exception as e:
                logger.error(f"Error loading personas from {file_path.name}: {str(e)}")

        # Recommended packs first, then alphabetical - keeps the default
        # selection (matchmaker) at the top of the team list.
        priority = {"matchmaker": 0, "general": 1}

        def sort_key(item):
            name, persona = item
            stem = name.rsplit("(", 1)[-1].rstrip(")")
            return (priority.get(stem, 2), name.lower())

        all_personas = dict(sorted(all_personas.items(), key=sort_key))

        logger.info(f"Successfully loaded {len(all_personas)} personas.")
        return all_personas
