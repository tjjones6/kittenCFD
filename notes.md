# Kitten CFD

## Geometry pipeline
1. Source: Kitten.obj (Sketchfab, CC-BY — credit the creator if published)
2. ParaView Transform: scale 0.025, translate (0, -0.005, 0)
3. Export binary STL
4. Blender: voxel remesh, voxel size 0.001 m, adaptivity 0
   - fixes: 3 disconnected parts (2 eye shells), 134 open edges, inconsistent normals
   - result: 122,284 tris, closed, 1 part, 1 zone
   - note: voxel snapping shifted ymin to -0.0068

## Domain
X: -0.5 to 0.5, Y: 0 to 1.0, Z: -1.5 to 3.0
Flow in +Z (nose at -Z). Base cell 0.05 m.

## Case
- simpleFoam, kOmegaSST, U = 5 m/s, nu = 1.5e-5
- mesh: 400,186 cells, 4 layers requested / 3.03 achieved, 90% coverage
- Aref = 0.015 PLACEHOLDER — measure actual frontal area
- y+ expected ~8 (buffer layer) — revisit
- 9 under-determined cells at paw/ground contact, unresolved

## Grid study results (2-layer absolute sizing, Aref = 0.0268)

| mesh   | cells | iters | Cd              | Cl              | y+ avg | layers |
|--------|-------|-------|-----------------|-----------------|--------|--------|
| coarse | 265k  | 459   | 0.6105 ± 0.0001 | 0.2616 ± 0.0001 | 10.8   | 94.2%  |
| medium | 400k  | 612   | 0.6117 ± 0.0019 | 0.2817 ± 0.0029 | 10.6   | 92.8%  |
| fine   | 880k  | 1000  | 0.6131 ± 0.0044 | 0.3316 ± 0.0073 | 10.4   | 91.5%  |

- Cd grid-converged: 0.43% coarse to fine, near-equal increments. Report 0.613 ± 0.005.
- Cl NOT converged: 27% spread, diverging with refinement. Finer meshes admit more
  of the unsteady wake that coarser ones damp out. Steady RANS cannot resolve it.
- Force split ~95% pressure / 5% viscous, so skin-friction error contributes little to Cd.
- y+ spans ~0.3 to 45 on all meshes (avg ~10.8) — buffer layer, where neither
  wall-function asymptote is strictly valid. nutUSpaldingWallFunction blends across it.
- runTimeControl never triggered; coarse stopped on residualControl at 459,
  fine ran to endTime. Stopping criteria differ between meshes.

## Open
- y+ sensitivity test (medium mesh at y+ ~50) to confirm wall treatment is not
  driving the Cl spread
- pimpleFoam on medium mesh for a time-averaged Cl
