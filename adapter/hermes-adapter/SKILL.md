---
name: hermes-adapter
description: Maps the Cursor tool, subagent, model and path names used in pstack skills to Hermes. Load it once per session before following any pstack skill.
---

# pstack in Hermes

pstack skills use Cursor names. In Hermes, read this once per session, then map each Cursor name in a skill with the tables below. `<pstack>` means the folder that holds `skills/`, `agents/` and `docs/`. If a Cursor field has no row, drop it and say so. Never pass a field or value the tool schema rejects.

## Tools

| Cursor | Hermes |
| --- | --- |
| `Task` | `delegate_task`. Put each subagent in `tasks=[{goal, context}]`. Several entries run in parallel. Results come back as a new message, so finish what does not depend on them and end your turn. |
| `AskQuestion` | `clarify`. In a session with no user to answer (cron, one-shot), ask in plain text or decide under the skill's autonomy rules. |
| Open a todolist | `todo_list`. |
| Run another pstack skill (`/name` or "the **name** skill") | `skill_view(name="pstack:<name>")` and follow it. A file linked inside a skill is `skill_view(name="pstack:<name>", file_path="<relative path>")`. When you tell the user to type it, write `/pstack:<name>`. |
| `Grep`, `Glob` | `search_files`. |

## Subagent fields

| Cursor | Hermes |
| --- | --- |
| `subagent_type: generalPurpose` | Omit. Every `delegate_task` child is general purpose. |
| `poteto-agent`, `comment-sicko` | Subagent definitions live in `<pstack>/agents/<name>.md`. Hermes has no named agents, so start the child's `goal` with that file's body (without the frontmatter) and keep the rest of the brief as written. For `poteto-agent`, also tell it to load `pstack:poteto-mode` with `skill_view`. |
| `readonly: true` | `readonly: true` on the task. The child then reads and searches files and the web and loads skills, and has no shell and no edit tools. If the `delegate_task` schema has no `readonly` field, say "do not edit files" in the brief and check `git status` afterward. |
| `readonly: false` | Omit. |
| `environment: "cloud"` | Hermes isolates children only through `delegation.worktree_isolation: true` in the config, which gives every child its own git worktree. Name the branch or commit the worker checks out. If isolation is off, say so in the reply. |
| `environment: "local"` | Omit. |
| `cloud_base_branch: <b>` | Tell the worker to check out `<b>` first. |
| `run_in_background: true` | Omit. `delegate_task` always runs in the background and re-enters when done. |
| `resume` | Spawn a new child and paste the earlier result into its brief. |
| `file_attachments` | List the paths in `context`. Pass images with the task's `images` field. |

## Models

| Cursor | Hermes |
| --- | --- |
| `claude-<family>-<version>-<effort>[-fast]`, such as `claude-opus-5-5-xhigh` | `model: "<model id>"` and `reasoning_effort: "xhigh"` on the task. The model id must exist on the provider that `delegation` uses. Drop `-fast`. If the schema has no `model` field, omit both and say so. |
| A `grok-*`, `gpt-*`, or other non-Claude slug | Use it as `model` only when the delegation provider serves it. Otherwise omit `model` so the child runs on the configured model, and say so. |
| `auto` or `inherit-parent` | Omit `model` and `reasoning_effort`. |
| The `pstack-models.mdc` rule, `~/.cursor/rules/pstack-models.mdc` | `$HERMES_HOME/rules/pstack-models.md` (`~/.hermes/rules/pstack-models.md`). The pstack plugin shows it on the first turn of every session, so its role lines are already in context. If they are not, read the file. If the file or the role's line is missing, use the skill's default slug. |
| A role value `<model> <effort>`, such as `opus high` | `model: "<model id>"` and `reasoning_effort: "high"`. |

## setup-pstack

Follow its steps with these changes:

- Detect. The detected models are the model ids the user's `delegation` provider serves, from the config and `hermes models` output. If you cannot list them, ask the user to paste the ids. Write a real model as `<model> <effort>`. The effort is the last token, so the budget step works as written.
- Defaults. Map each default slug with the rows above. A slug the delegation provider does not serve is `inherit-parent`.
- Write. Write `~/.hermes/rules/pstack-models.md` with no frontmatter, then the comment lines, the `# budget` line, and one line per role from step 5. Overwrite the whole file. Never put the role lines in `AGENTS.md`, memory or `SOUL.md`.

## Paths

| Cursor | Hermes |
| --- | --- |
| `.cursor/skills/`, `~/.cursor/skills/` | `.hermes/skills/`, `~/.hermes/skills/` |
| `~/.cursor/plugins/`, `.cursor-plugin/plugin.json` | `~/.hermes/plugins/`, `plugin.yaml` |
| `.cursor/rules/*.mdc`, always-applied rules | `AGENTS.md` in the workspace. Hermes never reads `.mdc` files. The model rule is the exception. See Models. |
| `https://github.com/cursor/plugins/blob/main/pstack/<path>` | `<pstack>/<path>` when that file exists. Read the local copy and never fetch it. Give the user the URL when they need a link. |
| Transcripts in `~/.cursor/projects/<slug>/agent-transcripts/` | Past sessions through `session_search`. Read only this workspace's sessions. |

## Cursor-only features

Hermes has no Cursor Automations, Bugbot, Cursor cloud agents, or built-in PR tool. When a step needs one, put one line in your reply, `Skipped in Hermes: <step>. <reason>.`, then go on to the next step. Do not stop, ask, or retry. When a later step needs what the skipped step made, such as a URL or a key, leave a placeholder and name it in the line.

| Cursor | Hermes |
| --- | --- |
| Cursor Automations: routines, `update_state` routine calls, `api2.cursor.sh/automations` webhooks, routine wakes, and `SendToUser` secret requests | Skip with the line. |
| Bugbot | Bugbot comments on a GitHub PR are ordinary review threads, so triage them with the forge command that the step gives. Skip a step that starts, waits for, or configures Bugbot when the PR has no Bugbot check or comment. |
| Cursor cloud agents | `environment: "cloud"` maps to worktree isolation, as in Subagent fields. Skip a step that needs the cloud agent itself, such as its dashboard status or its own machine. |
| A built-in PR tool | Use the forge command that the step gives, such as `gh pr create`. That is not a skip, so write no line. |
