import numpy as np

def read_binary_stl(path):
    with open(path, 'rb') as f:
        f.read(80)
        n = int(np.frombuffer(f.read(4), dtype=np.uint32)[0])
        raw = np.frombuffer(f.read(n * 50), dtype=np.uint8).reshape(n, 50)
    return raw[:, 12:48].copy().view(np.float32).reshape(n, 3, 3).astype(np.float64)

tris = read_binary_stl('constant/triSurface/kitten.stl')
print(f"{len(tris)} triangles")

res = 0.00025                      # 0.5 mm pixels
xy = tris[:, :, :2]               # drop Z: project along flow direction
lo, hi = xy.reshape(-1, 2).min(0), xy.reshape(-1, 2).max(0)
nx, ny = (np.ceil((hi - lo) / res).astype(int) + 1)
mask = np.zeros((ny, nx), dtype=bool)

ij = np.floor((xy - lo) / res).astype(int)
for t in range(len(tris)):
    i0, j0 = ij[t].min(0); i1, j1 = ij[t].max(0)
    ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1))
    px = lo[0] + (ii + 0.5) * res
    py = lo[1] + (jj + 0.5) * res
    (ax, ay), (bx, by), (cx, cy) = xy[t]
    d = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
    if abs(d) < 1e-14:
        continue
    u = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / d
    v = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / d
    inside = (u >= 0) & (v >= 0) & (u + v <= 1)
    mask[jj[inside], ii[inside]] = True

y_centers = lo[1] + (np.arange(ny) + 0.5) * res
mask[y_centers <= 0, :] = False   # discard anything below the ground plane

area = mask.sum() * res * res
bbox = (hi[0] - lo[0]) * (hi[1] - lo[1])
print(f"frontal area   = {area:.6f} m^2")
print(f"bounding box   = {bbox:.6f} m^2  ({100*area/bbox:.1f}% fill)")
