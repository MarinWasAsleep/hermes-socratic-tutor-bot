"""Pure-Python state engine for the Socratic tutor (no Hermes imports)."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

LEVEL_NAMES = {
    0: "unaware", 1: "heard of it", 2: "can follow along",
    3: "can do with help", 4: "can do independently", 5: "can teach it / edge cases",
}
# Days until a subskill is due for review again, by current level.
REVIEW_DAYS = {0: 0, 1: 1, 2: 2, 3: 4, 4: 10, 5: 21}
RESULTS = ("pass", "partial", "fail")
MAX_NOTES = 30


class TutorError(ValueError):
    """User-facing error: message is returned to the model verbatim."""


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower().strip()).strip("-")
    return s[:48] or "course"


def safe_learner(learner: str | None) -> str:
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", (learner or "default").strip())[:64]
    return s.strip("._") or "default"


class Store:
    """One JSON file per learner: {"courses": {course_id: course}}."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, learner: str) -> Path:
        return self.root / f"{safe_learner(learner)}.json"

    def load(self, learner: str) -> dict:
        p = self._path(learner)
        if not p.exists():
            return {"courses": {}}
        return json.loads(p.read_text(encoding="utf-8"))

    def save(self, learner: str, data: dict) -> None:
        p = self._path(learner)
        fd, tmp = tempfile.mkstemp(dir=self.root, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, p)  # atomic: never leaves a half-written file
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


# --------------------------------------------------------------------------- helpers

def _find_course(data: dict, course: str | None) -> dict:
    courses = data["courses"]
    active = [c for c in courses.values() if c["status"] == "active"]
    if course:
        if course in courses:
            return courses[course]
        hits = [c for c in courses.values() if course.lower() in c["topic"].lower()]
        if len(hits) == 1:
            return hits[0]
        raise TutorError(f"Unknown or ambiguous course '{course}'. Known: {sorted(courses)}")
    if len(active) == 1:
        return active[0]
    if not active:
        raise TutorError("No active course. Create one with action='create'.")
    raise TutorError(f"Several active courses; pass course=<id>. Active: {[c['id'] for c in active]}")


def _find_sub(course: dict, name: str | None) -> dict:
    if not name:
        raise TutorError("subskill is required.")
    for s in course["subskills"]:
        if s["name"].lower() == name.lower():
            return s
    hits = [s for s in course["subskills"] if name.lower() in s["name"].lower()]
    if len(hits) == 1:
        return hits[0]
    raise TutorError(f"Unknown or ambiguous subskill '{name}'. Known: {[s['name'] for s in course['subskills']]}")


def _schedule(sub: dict, t: datetime, fail: bool = False) -> None:
    days = 1 if fail else REVIEW_DAYS[sub["level"]]
    sub["due"] = iso(t + timedelta(days=days))


def _bar(level: int, width: int = 10) -> str:
    filled = round(level / 5 * width)
    return "█" * filled + "░" * (width - filled)


def render_map(course: dict) -> str:
    subs = course["subskills"]
    total = sum(s["level"] for s in subs)
    pct = round(100 * total / (5 * len(subs))) if subs else 0
    head = f"Topic: {course['topic']}"
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
    lines = [f"{head:<40}overall: {bar} {pct}%", "-" * 66]
    width = max((len(s["name"]) for s in subs), default=10)
    focus = course.get("focus")
    target = course["target"]
    for s in subs:
        mark = ""
        if s["name"] == focus:
            mark = "  <- current focus"
        elif s["level"] >= target:
            mark = "  * reached target"
        lines.append(f"{s['name']:<{width}}  [{_bar(s['level'])}]  {s['level']}/5{mark}")
    lines.append("-" * 66)
    return "\n".join(lines)


def _due(course: dict, t: datetime) -> list[dict]:
    out = []
    for s in course["subskills"]:
        if s["level"] > 0 and s.get("due") and parse(s["due"]) <= t:
            out.append({"subskill": s["name"], "level": s["level"], "overdue_days": (t - parse(s["due"])).days})
    return sorted(out, key=lambda d: -d["overdue_days"])


def summary(course: dict, t: datetime | None = None) -> dict:
    t = t or now()
    return {
        "course": course["id"], "topic": course["topic"], "status": course["status"],
        "target": course["target"], "focus": course.get("focus"),
        "map": render_map(course), "due_for_review": _due(course, t),
        "mastered": all(s["level"] >= course["target"] for s in course["subskills"]),
        "final_assessment_passed": course.get("final_passed", False),
        "notes": course.get("notes", [])[-8:],
    }


# --------------------------------------------------------------------------- actions

def create(data: dict, topic: str, subskills: list[dict], target: int = 4, language: str | None = None, t=None) -> dict:
    t = t or now()
    if not topic or not subskills:
        raise TutorError("create needs topic and subskills (list of {name, level}).")
    if target not in (4, 5):
        raise TutorError("target must be 4 (default) or 5 (full mastery).")
    cid = slug(topic)
    if cid in data["courses"] and data["courses"][cid]["status"] == "active":
        raise TutorError(f"Course '{cid}' already exists and is active; use action='show' to resume it.")
    seen, subs = set(), []
    for item in subskills:
        item = {"name": item} if isinstance(item, str) else item
        name = str(item.get("name", "")).strip()
        level = int(item.get("level", 0))
        if not name or name.lower() in seen:
            raise TutorError(f"Empty or duplicate subskill name: '{name}'.")
        if not 0 <= level <= 5:
            raise TutorError("Diagnostic levels must be 0-5.")
        seen.add(name.lower())
        s = {"name": name, "level": level, "checks": [], "history": [], "due": None}
        if level > 0:
            _schedule(s, t)
        subs.append(s)
    if len(subs) > 10:
        raise TutorError("At most 10 subskills per course; split broad topics into a two-level tree.")
    course = {"id": cid, "topic": topic.strip(), "status": "active", "target": target,
              "language": language, "created": iso(t), "updated": iso(t),
              "focus": subs[0]["name"], "subskills": subs, "notes": [], "final_passed": False}
    data["courses"][cid] = course
    return summary(course, t)


def record(data: dict, course: str | None, subskill: str, result: str, unprompted: bool = False,
           edge_case: bool = False, explained: bool = False, note: str | None = None, t=None) -> dict:
    """Log one check. Levels move only through the strict rules below."""
    t = t or now()
    if result not in RESULTS:
        raise TutorError(f"result must be one of {RESULTS}.")
    c = _find_course(data, course)
    s = _find_sub(c, subskill)
    s["checks"].append({"at": iso(t), "result": result, "unprompted": bool(unprompted),
                        "edge_case": bool(edge_case), "explained": bool(explained)})
    old = s["level"]
    reason = "check logged, level unchanged"
    if result == "fail" and old > 0 and unprompted:
        # A failed unprompted check (typically a spaced review) lowers the level.
        s["level"] = old - 1
        s["checks"] = []
        reason = "failed unprompted check: level lowered"
    elif result == "pass":
        recent = s["checks"][-2:]
        passes = len(recent) == 2 and all(x["result"] == "pass" for x in recent)
        if old >= 5:
            reason = "already at max level"
        elif passes and any(x["unprompted"] for x in recent):
            if old + 1 == 5 and not (any(x["edge_case"] for x in recent) and any(x["explained"] for x in recent)):
                reason = "level 5 needs an edge-case/adversarial pass AND a clear explanation (explained=true)"
            else:
                s["level"] = old + 1
                s["checks"] = []
                reason = "2 consecutive passes incl. unprompted recall: level raised"
        else:
            reason = "pass logged; level rises after 2 consecutive passes incl. 1 unprompted recall"
    new = s["level"]
    if new != old:
        s["history"].append({"at": iso(t), "from": old, "to": new})
    _schedule(s, t, fail=(result == "fail"))
    if note:
        c["notes"].append(f"[{s['name']}] {note.strip()}"[:300])
        c["notes"] = c["notes"][-MAX_NOTES:]
    c["updated"] = iso(t)
    out = summary(c, t)
    out.update({"subskill": s["name"], "old_level": old, "new_level": new, "reason": reason,
                "next_review": s["due"]})
    return out


def set_focus(data: dict, course: str | None, subskill: str, t=None) -> dict:
    t = t or now()
    c = _find_course(data, course)
    c["focus"] = _find_sub(c, subskill)["name"]
    c["updated"] = iso(t)
    return summary(c, t)


def finish(data: dict, course: str | None, passed: bool, t=None) -> dict:
    """Record the final mixed assessment. Only allowed when every subskill hit the target."""
    t = t or now()
    c = _find_course(data, course)
    low = [s["name"] for s in c["subskills"] if s["level"] < c["target"]]
    if low:
        raise TutorError(f"Final assessment not allowed yet; below target {c['target']}: {low}")
    c["final_passed"] = bool(passed)
    if passed:
        c["status"] = "completed"
    c["updated"] = iso(t)
    return summary(c, t)


def archive(data: dict, course: str | None) -> dict:
    c = _find_course(data, course)
    c["status"] = "archived"
    return {"course": c["id"], "status": "archived"}


def overview(data: dict, t=None) -> dict:
    t = t or now()
    rows = []
    for c in data["courses"].values():
        rows.append({"course": c["id"], "topic": c["topic"], "status": c["status"],
                     "due_count": len(_due(c, t)) if c["status"] == "active" else 0,
                     "levels": {s["name"]: s["level"] for s in c["subskills"]}})
    return {"courses": rows, "total_due": sum(r["due_count"] for r in rows)}


def export_state(data: dict, course: str | None) -> dict:
    c = _find_course(data, course)
    return {"format": "hermes-socratic-tutor/1", "course": c}


def import_state(data: dict, state: dict, t=None) -> dict:
    t = t or now()
    if not isinstance(state, dict) or state.get("format") != "hermes-socratic-tutor/1":
        raise TutorError("Not a hermes-socratic-tutor state block (bad 'format').")
    c = state["course"]
    for key in ("id", "topic", "target", "subskills"):
        if key not in c:
            raise TutorError(f"State block missing '{key}'.")
    for s in c["subskills"]:
        if not 0 <= int(s["level"]) <= 5:
            raise TutorError("State block has an out-of-range level.")
    data["courses"][c["id"]] = c
    return summary(c, t)
