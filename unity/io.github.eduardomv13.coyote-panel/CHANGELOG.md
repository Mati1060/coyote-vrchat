# Changelog

## 0.1.0

First public version. Generalized from a panel that was built for one specific avatar.

- Installs on the avatar you select (menu **Tools > Coyote Panel > Install on selected avatar**, or the options window).
  Nothing about the author's avatar is hard-coded any more.
- The hand frame (where the palm faces, where the fingers point) is derived from the humanoid skeleton, with
  configurable distances, roll, scale, left/right hand and a "flip facing" option. A fixed-bone-axes mode reproduces the
  geometry the panel was originally tuned with.
- Generated meshes, materials and the animator controller are written to `Assets/CoyotePanel/Generated/<avatar name>/`,
  one folder per avatar. The two textures ship inside the package.
- Same panel as before: 14-layer FX controller, A/B bars with PhysBone grips, -/+ buttons, one +/-10 Hz frequency pair,
  "Show panel", "Lock in world", "Zero channels", "STOP". Verified identical (controller, hierarchy, meshes) to the
  original build on the original avatar.
- Developer tools: controller JSON exporter and an offline simulator (`Tools~/simulate_controller.py`), plus tests in the
  repository that check the package without Unity.
