# kittenCFD

External aerodynamics of a (chunky) kitten, solved with OpenFOAM v2312.

![Vortex shedding, Q-criterion coloured by Cp](figures/Cp_Qcrit.mp4)
![Surface pressure coefficient](figures/Cp_medium.png)

![Vortex shedding, Q-criterion coloured by Cp](figures/Cp_Qcrit.mp4)

## Setup

| | |
|---|---|
| Solver | simpleFoam, k-omega SST |
| Freestream | 5 m/s, Re ~ 1e5 |
| Reference length | 0.30 m |
| Frontal area | 0.0268 m2 (measured from the STL silhouette) |
| Domain | 1.0 x 1.0 x 4.5 m, flow in +Z |
| Mesh | snappyHexMesh, 265k-880k cells, 2 prism layers |

## Results

| mesh | cells | Cd | Cl |
|---|---|---|---|
| coarse | 265k | 0.6105 | 0.2616 |
| medium | 400k | 0.6117 | 0.2817 |
| fine | 880k | 0.6131 | 0.3316 |

**Cd = 0.613 +/- 0.005.** Drag is grid-converged, varying 0.43% across the
series, and is ~95% pressure drag.

Lift is not grid-converged and diverges with refinement -- finer meshes admit
more of the unsteady wake that coarser ones damp out. Steady RANS cannot
resolve it; a time-accurate run is needed for a meaningful Cl.

## Layout

    geometry/        source mesh + frontal-area script
    run/steady-*/    the three grid levels
    run/plot_run.py  residual / coefficient plots
    notes.md         full method and caveats

## Running

    cd run/steady-medium && ./Allrun
    cd .. && ./plot_run.py steady-coarse steady-medium steady-fine

Geometry: "Sitting cat (British Shorthair Blue Cat)" by 3D Creator, CC-BY.
