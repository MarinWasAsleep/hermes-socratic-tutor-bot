# hermes-socratic-tutor-bot

A ready-to-install **Hermes Bot** (profile distribution) named `tuteur`: a strict Socratic tutor in
English / Français. It shows up in the desktop **Bots** tab with its own permanent chat.

Built on Jane Street's [`socratic-tutor`](https://github.com/janestreet/agent_skills) skill (MIT).
Progress tracking comes from the plugin
[hermes-socratic-tutor](https://github.com/MarinWasAsleep/hermes-socratic-tutor), vendored here in
`plugins/` so one command installs everything.

## Install

```bash
hermes profile install github.com/MarinWasAsleep/hermes-socratic-tutor-bot --alias
hermes -p tuteur model              # pick a model (a cheap one is enough for tutoring)
```

Open the Bots tab, click **tuteur**, say « apprends-moi les jointures SQL » / "teach me Rust ownership".
Update with `hermes profile update tuteur`; your progress and memories are never touched.

No model is pinned: choose one with `hermes -p tuteur model` (your choice survives updates). Tutoring means many short turns, so a cheap model is fine.

## What's inside

| File | Role |
|---|---|
| `SOUL.md` | The tutor persona and standing rules |
| `skills/socratic-tutor` | The adapted skill (diagnostic, levels 0-5, strict grading) |
| `plugins/socratic-tutor` | `tutor_course` tool: persistent map, enforced level rules, review dates |
| `config.yaml` | Enables the plugin |

Due reviews are shown when you open the chat; there are no automatic reminders.

MIT. Skill © Jane Street Group, LLC, adaptations © MarinWasAsleep (see `NOTICE.md`).
