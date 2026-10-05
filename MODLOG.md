# Mod log

## Goal

Build a four-player co-op TF2 holdout map using TF2's native skeleton spawner. L4D2 contributes its horde warning music from the player's local game files, with no Valve audio redistributed.

## Environment

- TF2 install: `C:\Program Files (x86)\Steam\steamapps\common\Team Fortress 2`
- TF2 build ID: `25687524` (Steam manifest); client patch version `11076587`.
- L4D2 install: `C:\Program Files (x86)\Steam\steamapps\common\Left 4 Dead 2`
- L4D2 build ID: `23990068` (Steam manifest); patch version `2.2.4.3`.
- Engine: Source 1 for both games.
- Route: TF2 custom map/add-on under `tf/custom`; no loader installed by Melty for either title.
- Toolkit: official `universal-modder` checkout in workspace `work/universal-modder-checkout`; Source-engine playbook followed.
- TF2 mapping tools available locally: Hammer, VBSP, VVIS, VRAD, and VPK.
- Safety: local/private TF2 launch with `-insecure`; never use official secure servers.

## Findings

- Melty currently has no draft for this project and no close mashup to remix.
- TF2's installed `tf.fgd` defines `tf_zombie_spawner`, `team_round_timer`, and the standard RED team spawn entity.
- The selected L4D2 cue exists at `left4dead2/sound/music/zombat/snare_horde_01_01a.wav` on this PC. It must stay out of uploads and be sourced from a player's own installation at run time.
- The two-game launch path and the zombie round behavior remain unverified.

## Progress

- [x] Inspect installed game versions and source folders.
- [x] Review toolkit Source-engine guidance and local TF2 entity definitions.
- [ ] Clean JSON-sheet preflight.
- [ ] Generate and compile the first map.
- [ ] Install in TF2 and verify map, skeleton behavior, sound, and timer.
- [ ] Test host and join with two running copies; keep Melty `connect` omitted until that passes.
- [ ] Package and run Melty recipe checks.
- [ ] Ask for listing metadata, credits/license/remix choice, and gameplay media.
- [ ] Melty install test before any publication request.
