# A reproducible desk-hook showcase

The launch demo shows one useful loop: adapt a dimensioned part, inspect the
result, and catch a feature that looks plausible but is missing. The finished
video, review evidence and CAD files are attached to the
[v0.3.0 release](https://github.com/aeshef/bambu-pipe/releases/tag/v0.3.0).

## What actually happened

- Codex authored the saved [model](../cad/desk-hook/model.py) in a project session
  from the included [dimensioned brief](../cad/desk-hook/brief.md).
- Local CadQuery built two variants, for 24 mm and 32 mm desk edges. Both passed
  22 checks, including 13 material/void probes, and their four rendered PNG views
  were inspected before an accepted review was recorded.
- A third case deliberately removes the pilot-hole cut. Its single solid,
  outside dimensions and watertight mesh still pass; the independently specified
  `probe:screw through hole` fails. It cannot receive an accepted review.
- The video and README GIF are **edited replays of those saved builds**, rendered
  offline. They are not a screen recording of a live agent session or evidence
  of inference speed. The missing-hole case is a **seeded negative control**, not
  a mistake observed during model inference.
- The display rotates the model into use orientation. The original verified
  STL remains on its side for the intended print orientation. No slicing,
  hardware fit, load or physical-print test was completed for this prototype.

This is an example of an agent-assisted workflow, not an independent benchmark
or proof that all generated parts will work. Reproduction below executes saved
Python and uses no LLM. CAD sources execute trusted local Python, not a sandbox.

## Rebuild the evidence

From the repository root, after the [CAD quick start](../../README.md#quick-start):

```bash
python examples/showcase/build_cases.py --output output/showcase
```

The output directory must be empty. The script preserves every build's source,
specification, STEP/STL, checks and four views, and never automatically accepts
a visual review. It prints the two passing cases and the expected failed probe.

For **each passing case**, open its `builds/<id>/preview.html` and inspect
`isometric.png`, `front.png`, `right.png` and `top.png`. Then record what you
actually saw; the command below is a template, not an instruction to skip review:

```bash
bambu-pipe design review output/showcase/desk24 --decision accept --reviewer me \
  --view isometric.png --view front.png --view right.png --view top.png \
  --notes 'REPLACE with your findings and remaining fit/strength assumptions.'
bambu-pipe design verify output/showcase/desk24
# Repeat the actual inspection and review for output/showcase/desk32.
```

Keep `missing-hole` unaccepted. Its report is a failure demonstration. Changing
any source, specification or recorded artifact invalidates the corresponding
review. To try a fresh agent run rather than a replay, give your agent the brief
and an empty workspace; do not ask it to copy the saved model.

## Render launch media

Install ffmpeg locally. Pillow is included by the CAD extra's Matplotlib
dependency. The media tool requires matching accepted reviews for both passing
cases and hash-checks the failed control as well:

```bash
python examples/showcase/render_media.py --cases output/showcase \
  --output output/launch-assets
```

It writes a 24-second square MP4, a compact README GIF, a social preview card,
scene stills and a manifest of build and asset hashes. Keep videos and generated
CAD evidence in local output or release assets. The committed previews can be
regenerated explicitly with `--preview-assets docs/assets`; review them before
committing. Neither script calls a generation service or contacts a printer.

## The Twitter/X launch

The angle is **“AI CAD you can check and edit”**. Lead with the useful part and
the changed dimension; show the blocked hole as evidence for why checks matter.
Avoid “first text-to-CAD”, “guaranteed printable” and generation-speed claims.
The readable CAD and independently specified constraints are the point.

| Video time | What viewers see | Evidence |
| --- | --- | --- |
| 0–6 s | A desk hook, “Your coding agent. Now with CAD.” | Reviewed 24 mm variant |
| 6–12 s | “Change the desk. Keep the design.” | Reviewed 32 mm variant |
| 12–18 s | “Skip an important hole? The check blocks it.” | Explicitly seeded missing-hole control |
| 18–24 s | Editable Python + STEP + STL, MIT, repository address | Actual release contents |

Upload `bambu-pipe-demo.mp4` as a native video with the draft below, then put the
repository link in the first reply. The MP4 uses square 720×720, 30 fps, H.264
High Profile and YUV420p, with captions built into the image; it is readable
without audio. These choices follow the
[X media recommendations](https://docs.x.com/x-api/media/quickstart/best-practices).
The 1280×640 PNG follows
[GitHub's social preview guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview).
To set the repository's link card, upload `docs/assets/social-preview.png` in
GitHub **Settings → General → Social preview** while signed in as the owner.
The prepared image is also included in the release.

Suggested first post (231 characters, excluding the video):

> I gave my coding agent a local CAD workbench.
>
> Same desk hook: 24 → 32 mm. Editable Python + STEP/STL, with geometry checks
> that catch a deliberately missing hole.
>
> Open source, no extra generation API. What part should I try next?

Suggested first reply:

> Code + reproducible demo: https://github.com/aeshef/bambu-pipe
>
> This is an edited CAD replay, not a real-time agent recording. The failed hole
> is a seeded control. Physical fit and printing are still untested. Bring a
> dimensioned brief and your existing terminal/vision agent.

Before posting, watch the complete video and check that the release link works.
After launch, respond to concrete part requests and reproduce one useful
failure; add the source, checks and limitation to the repo. A measured test print
would make a stronger follow-up once one actually exists. Invite briefs and
contributions, rather than promising virality or claiming unmeasured reliability.

Posting and replies are manual. Preparing these files does not publish anything
to a social account.
