# Reference learning and promotion loop

Use references to improve reusable structure, never to imitate wording.

1. Store each reference caption file and a metrics JSON under `work/references/`.
2. Record measurement limitations. Automatic captions may combine reviewer speech and movie dialogue; caption-free time is not automatically silence.
3. Convert observations into explicit candidate rules with evidence, scope, and a rollback condition.
4. Promote only user-approved rules to `work/references/learning_registry.json` with `status: approved`.
5. Feed only approved rules into narration generation. Never feed raw reference wording, jokes, titles, or distinctive phrases.
6. Route rules per story unit. Do not average unlike reference densities into one global narration rate.
7. Validate the registry with `python scripts/validate_reference_learning.py work/references/learning_registry.json`.
8. Test a promoted rule on a short preview before a full rerender. Keep it only if causality, dialogue clarity, protected scenes, and pacing all pass.
9. If a promoted rule causes repeated narration, dialogue masking, emotional interruption, future-result narration, or style imitation, mark it rejected and restore the prior approved rule set.

The learning order is `observe → measure → state a hypothesis → preview → user approval → promote → regression check`. A new reference never overrides spoiler protection, story-map causality, voice lock, subtitle timing, or protected-scene rules.
