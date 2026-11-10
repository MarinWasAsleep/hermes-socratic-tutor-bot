"""Tool handler. Never raises; always returns a JSON string."""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from . import core

logger = logging.getLogger(__name__)
PLUGIN = "socratic-tutor"


def _data_dir() -> Path:
    try:
        from plugins.plugin_storage import plugin_data_dir
        return Path(plugin_data_dir(PLUGIN))
    except Exception:  # running outside Hermes (tests, scripts)
        home = os.environ.get("HERMES_HOME") or str(Path.home() / ".hermes")
        return Path(home) / "plugin-data" / PLUGIN


def tutor_course(args: dict, **kwargs) -> str:
    try:
        store = core.Store(_data_dir())
        learner = args.get("learner")
        data = store.load(learner)
        a, course = args.get("action"), args.get("course")
        mutating = True
        if a == "list":
            out, mutating = core.overview(data), False
        elif a == "create":
            out = core.create(data, args.get("topic", ""), args.get("subskills") or [],
                              int(args.get("target") or 4), args.get("language"))
        elif a == "show":
            out, mutating = core.summary(core._find_course(data, course)), False
        elif a == "record":
            out = core.record(data, course, args.get("subskill"), args.get("result", ""),
                              bool(args.get("unprompted")), bool(args.get("edge_case")),
                              bool(args.get("explained")), args.get("note"))
        elif a == "focus":
            out = core.set_focus(data, course, args.get("subskill"))
        elif a == "finish":
            if "passed" not in args:
                raise core.TutorError("finish needs passed=true|false.")
            out = core.finish(data, course, bool(args["passed"]))
        elif a == "export":
            out, mutating = core.export_state(data, course), False
        elif a == "import":
            out = core.import_state(data, args.get("state"))
        elif a == "archive":
            out = core.archive(data, course)
        else:
            raise core.TutorError(f"Unknown action '{a}'.")
        if mutating:
            store.save(learner, data)
        return json.dumps(out, ensure_ascii=False)
    except core.TutorError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001
        logger.exception("tutor_course failed")
        return json.dumps({"error": f"Internal error: {e}"})
