# Frequently asked questions

## Is this an AI model or an autonomous agent service?

It is a local CAD toolkit and an agent skill. Your terminal/vision agent writes
the model and inspects the images. The toolkit executes, measures and exports
geometry. It does not make LLM calls or operate its own multi-agent service.

## Can I use an agent subscription I already have?

Yes, if that agent has terminal/file access and can inspect images. The included
skill works as repository instructions or can be installed into an agent's
skills folder. Codex uses `.agents/skills`; Claude Code uses `.claude/skills`.
The package does not require another generation API account. A plain chat page
without execution and image-inspection tools cannot run the local workflow.

## Is it fully local?

CAD, rendering and geometric checks run locally. Agent inference uses your
chosen harness: a subscription, an API or a local model. This package does not
bundle a model or a GPU runtime. Installing the CAD extra downloads substantial
native dependencies; allow extra time for the first installation and build.

## Do I need a Bambu printer?

No. Design and export do not need printer credentials or even a slicer.
The optional print adapters target Bambu A1. STEP/STL exports can be used in
other CAD tools and slicers; this is an independent project, not a Bambu product.

## What does a green report actually prove?

The checks listed in that report passed: for example, dimensions, solid count,
watertight export and material/void probes. Probes sample selected locations.
They do not prove every feature, strength, clearance or support strategy.
Visual review is a recorded attestation by an agent or person who inspected
all four views. It is not a hidden automated judge or a print certification.

## What is in the launch demo?

A desk-hook CAD prototype authored in a Codex session from a published brief,
its 24 mm and 32 mm desk variants, and an intentionally seeded missing pilot
hole that fails the checks. The video is an edited replay of those artifacts.
It does not show real-time agent inference, an unprompted agent failure, a
measured generation speed, a physical print or a multi-agent benchmark.

## Why does `design init --brief ...` give me a plate?

It initializes a starter workspace. It does not interpret natural language.
Your agent must replace the source and acceptance spec to match your brief.

## Why does my STL stop verifying after an edit?

The accepted review binds to input, output, image and report hashes. An edit or
rebuild requires fresh inspection. This prevents accidental stale reviews;
the evidence is not signed against a malicious user rewriting the chain.

## What if the slicer crashes?

CAD export still works. Use a working headless OrcaSlicer/Bambu Studio binary
and complete material/machine/process profiles. Some macOS Bambu Studio builds
crash in their CLI's GUI initialization. See [the design guide](design.md).
Never report a successful slice after a crash, or reuse an older sliced file.
