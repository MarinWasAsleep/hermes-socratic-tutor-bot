"""Hermes Socratic Tutor: bundled skill + persistent skill-map tool."""
from __future__ import annotations

from pathlib import Path

from . import schemas, tools


def register(ctx) -> None:
    ctx.register_tool(name="tutor_course", toolset="socratic_tutor",
                      schema=schemas.TUTOR_COURSE, handler=tools.tutor_course)
    skills_dir = Path(__file__).parent / "skills"
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.exists():
            ctx.register_skill(child.name, skill_md)
