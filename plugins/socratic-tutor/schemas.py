TUTOR_COURSE = {
    "name": "tutor_course",
    "description": (
        "Persistent progress store for the Socratic tutor. Use ONLY when the user explicitly asks to be "
        "taught/tutored/quizzed/drilled on a topic (not for one-off questions); first load the skill "
        "'socratic-tutor:socratic-tutor'. Actions: list (all courses + reviews due), create (new course "
        "from the diagnostic), show (resume: map + due reviews + notes), record (log ONE check; the tool "
        "alone decides level changes and review dates), focus, finish (final assessment result), "
        "export / import (portable state block), archive."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "create", "show", "record", "focus", "finish", "export", "import", "archive"]},
            "learner": {"type": "string", "description": "Learner id; default 'default'. Use a stable id per person (e.g. chat user id) when several people share the bot."},
            "course": {"type": "string", "description": "Course id or part of its topic. Optional if exactly one course is active."},
            "topic": {"type": "string", "description": "create: topic name."},
            "subskills": {
                "type": "array",
                "description": "create: 4-10 subskills with their diagnostic level 0-5.",
                "items": {"type": "object", "properties": {"name": {"type": "string"}, "level": {"type": "integer", "minimum": 0, "maximum": 5}}, "required": ["name"]},
            },
            "target": {"type": "integer", "enum": [4, 5], "description": "create: target level (default 4; 5 = full mastery)."},
            "language": {"type": "string", "description": "create: language the user is taught in (e.g. 'fr', 'en')."},
            "subskill": {"type": "string", "description": "record/focus: subskill name."},
            "result": {"type": "string", "enum": ["pass", "partial", "fail"], "description": "record: strict verdict on the user's answer. Vague or partly right = partial."},
            "unprompted": {"type": "boolean", "description": "record: true if the answer was unprompted recall (not right after you told the answer, and not a hint-led answer). A failed unprompted check lowers the level."},
            "edge_case": {"type": "boolean", "description": "record: the check was an edge-case/adversarial question (needed for level 5)."},
            "explained": {"type": "boolean", "description": "record: the user explained the idea clearly enough to teach it (needed for level 5)."},
            "note": {"type": "string", "description": "record: short note on a misconception or what was covered."},
            "passed": {"type": "boolean", "description": "finish: whether the user passed the final mixed assessment."},
            "state": {"type": "object", "description": "import: a block previously returned by export."},
        },
        "required": ["action"],
    },
}
