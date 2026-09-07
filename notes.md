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
