# cv-gen-ai

A GitHub template for a YAML-driven resume rendered to PDF with [Typst](https://typst.app/), paired with Claude Code skills for interviewing, concurrent-job strategy, multi-reviewer critique, and job hunting.

| Path | What it is |
|---|---|
| `resume.yml` | The resume content. Edit this one. |
| `resume.typ` | Layout settings and which sections appear |
| `work-history.example.yml` | Example private record of every job (copy to `work-history.yml`, gitignored) |
| `job-hunt.example.yml` | Example search/filter config for `/job-hunt` (copy to `job-hunt.yml`, gitignored) |
| `applications/` | Per-company tailored resumes, cover notes, and `tracker.example.yml` |
| `cv.typ/` | The [imprecv](https://github.com/jskherman/imprecv) template, as a git submodule |
| `.claude/skills/` | Claude Code skills for updating, reviewing, and tailoring the resume |

## Quick Start

1. Click **Use this template** on GitHub, then clone with submodules:

```sh
git clone --recurse-submodules <your-repo-url>
cd <your-repo-name>
typst compile resume.typ
```

This requires `typst` and the Linux Libertine font. If you cloned without `--recurse-submodules`, run `git submodule update --init`.

2. (Optional) Copy the example configs if you plan to use the skills:

```sh
cp work-history.example.yml work-history.yml
cp job-hunt.example.yml job-hunt.yml
cp applications/tracker.example.yml applications/tracker.yml
```

In `resume.yml`:

- Dates must be full `YYYY-MM-DD`. Use `endDate: "present"` for a current job.
- `highlights` are rendered as Typst markup, so `#`, `$`, `*`, `_`, `@` and `<` have special meaning.

## Skills

Run these inside Claude Code, from this directory.

| Command | What it does | Output |
|---|---|---|
| `/resume-interview` | Interviews you about what's missing or what you've done, then writes it into the resume. Works with no resume at all. | `.resume-interview/` |
| `/overemployment` | For concurrent jobs: decides which to list for a target role and pools the skills. | `.overemployment/` |
| `/hiring-panel` | Seven reviewers try to reject the resume, then it's rebuilt with the mistakes fixed. Starts 8 sub-agents. | `.hiring-panel/` |
| `/job-hunt` | Fetches public job feeds, ranks them against `job-hunt.yml`, verifies company boards, and prepares tailored resumes and cover notes (`pyyaml` required). | `applications/` |

A typical order is `/overemployment` if jobs overlap, then `/resume-interview`, then `/hiring-panel`, then `/job-hunt`.

Each review/interview skill writes a commented copy of the YAML to its output folder and leaves `resume.yml` alone. Those folders (`.hiring-panel/`, `.overemployment/`, `.resume-interview/`), along with `work-history.yml`, `job-hunt.yml`, `applications/tracker.yml`, and `*.pdf`, are ignored by git. To use a skill's output, compare it with `diff`, then copy over what you want or point the `yaml("...")` call in `resume.typ` at the new file.

## Credits

- Template: [imprecv](https://github.com/jskherman/imprecv) by jskherman.
