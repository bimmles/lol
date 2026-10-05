# Holdout: Four Corners

An in-progress Team Fortress 2 and Left 4 Dead 2 co-op holdout mashup. Players fortify a small arena as TF2 classes, then defend against TF2 skeletons while an L4D2 horde warning cue plays from the player's own L4D2 installation.

## First playable target

- One compact, four-player TF2 arena.
- A 60-second setup period for class selection and Engineer buildings.
- Three zombie entrances that grow from one active skeleton each to three each during a five-minute holdout.
- A Left 4 Dead 2 horde cue read from the player's installed copy. Valve audio is not included in the source or release package.
- Private/offline testing with TF2's `-insecure` launch option. Do not connect this modded client to VAC-secured servers.

The map and launch flow are not yet runtime-tested. Multiplayer capacity and join behavior are targets until tested with two running copies. Credits, content license, remix permission, Melty recipe validation, and gameplay media still need to be established before a release listing can be completed.

## Source of truth

The JSON sheets in `sheets/` define map geometry, entities, sound use, game requirements, and launch/package behavior. `tools/preflight.py` checks sheet completeness and entity links before the map compiler runs. `tools/build_map.py` generates the VMF from those sheets.

## Build tools

Build uses the TF2 installation's own Source map tools. The compiled BSP references stock TF2 materials and models from the player's local TF2 install. The release must not contain copied Valve game assets.
