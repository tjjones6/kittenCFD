#!/usr/bin/env python3
"""
Plot residuals, force coefficients and y+ history for one or more OpenFOAM cases.

Usage:
    ./plot_run.py                                  # current case directory
    ./plot_run.py steady-coarse                    # one case
    ./plot_run.py steady-coarse steady-medium ...  # overlay several

Writes <case>/logs/summary.png for a single case, or ./plots/summary.png when
overlaying, plus a text table on stdout.
"""

import sys
import glob
import os
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AVG_FRACTION = 0.2      # average the coefficients over the last 20% of iterations
WALL_PATCH = "kitten"   # patch to report y+ for
DOMAIN_VOLUME = 4.5     # m^3, for the representative cell size h


# ---------------------------------------------------------------- parsing ---

def read_dat(path):
    """Parse an OpenFOAM function-object .dat file.

    Column names come from the last '#' line. Non-numeric fields (solver
    names, patch names) become NaN so the array stays rectangular; callers
    look columns up by name, never by position.
    """
    names, rows = None, []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                body = line.lstrip("#").strip()
                if body:
                    names = body.split()
                continue
            vals = []
            for tok in line.split():
                try:
                    vals.append(float(tok))
                except ValueError:
                    vals.append(np.nan)
            rows.append(vals)

    if not rows:
        return names, np.empty((0, 0))

    width = max(len(r) for r in rows)
    arr = np.full((len(rows), width), np.nan)
    for i, r in enumerate(rows):
        arr[i, :len(r)] = r
    return names, arr


def dedupe_by_time(data):
    """Sort ascending by column 0, keeping the last row for duplicate times."""
    if data.size == 0:
        return data
    order = np.argsort(data[:, 0], kind="stable")
    data = data[order]
    _, keep = np.unique(data[:, 0][::-1], return_index=True)
    return data[::-1][keep]


def collect(case, func):
    """Merge every .dat under postProcessing/<func>/*/ into one array.

    Files are read oldest-first so that on a restart the newer run's values
    replace the ones it resumed from.
    """
    pattern = os.path.join(case, "postProcessing", func, "*", "*.dat")
    files = sorted(glob.glob(pattern), key=os.path.getmtime)
    if not files:
        return None, None

    names, chunks = None, []
    for path in files:
        n, d = read_dat(path)
        if d.size == 0:
            continue
        if names is None or (n and len(n) > len(names)):
            names = n
        chunks.append(d)

    if not chunks:
        return None, None

    width = max(c.shape[1] for c in chunks)
    data = np.vstack([np.pad(c, ((0, 0), (0, width - c.shape[1])),
                             constant_values=np.nan) for c in chunks])
    return names, dedupe_by_time(data)


def column(names, data, key):
    """Column whose header is exactly `key`. No substring fallback --
    'Cd' must not silently match 'Cd(f)'."""
    if not names:
        return None
    for i, n in enumerate(names):
        if n == key and i < data.shape[1]:
            return data[:, i]
    return None


def yplus_history(case, patch=WALL_PATCH):
    """(time, min, max, avg) for one patch, from the patch-name-keyed yPlus.dat."""
    rows = []
    pattern = os.path.join(case, "postProcessing", "yPlus", "*", "*.dat")
    for path in sorted(glob.glob(pattern), key=os.path.getmtime):
        with open(path) as fh:
            for line in fh:
                if line.startswith("#"):
                    continue
                tok = line.split()
                if patch not in tok:          # exact field, not substring
                    continue
                nums = []
                for x in tok:
                    try:
                        nums.append(float(x))
                    except ValueError:
                        pass
                if len(nums) >= 4:
                    rows.append(nums[:4])
    if not rows:
        return None
    return dedupe_by_time(np.array(rows))


def scrape(case, filename, pattern, cast=float):
    """First regex capture across a log file, or None."""
    path = os.path.join(case, "logs", filename)
    if not os.path.isfile(path):
        path = os.path.join(case, filename)
        if not os.path.isfile(path):
            return None
    rx = re.compile(pattern)
    with open(path, errors="ignore") as fh:
        for line in fh:
            m = rx.search(line)
            if m:
                try:
                    return cast(m.group(1))
                except ValueError:
                    return None
    return None


def case_info(case):
    """Cell count, layer coverage and convergence iteration, where available."""
    return {
        "cells": scrape(case, "log.snappyHexMesh",
                        r"Mesh with layers\s*:\s*cells:(\d+)", int),
        "layer_pct": scrape(case, "log.snappyHexMesh",
                            rf"{WALL_PATCH}\s+\d+\s+\d+\s+[\d.]+\s+[\d.]+\s+([\d.]+)"),
        "converged": scrape(case, "log.simpleFoam",
                            r"solution converged in (\d+) iterations", int),
    }


def tail_mean(t, y, frac=AVG_FRACTION):
    if y is None or len(t) < 2:
        return np.nan, np.nan, 0
    cut = t[-1] - frac * (t[-1] - t[0])
    m = (t >= cut) & np.isfinite(y)
    if m.sum() < 2:
        return np.nan, np.nan, 0
    return float(y[m].mean()), float(y[m].std()), int(m.sum())


# --------------------------------------------------------------- plotting ---

def plot_residuals(ax, cases, colors):
    single = len(cases) == 1
    fields = ["Ux", "Uy", "Uz", "p", "k", "omega"] if single else ["Ux", "p"]
    styles = {"Ux": "-", "p": "--"}
    for (label, case), c in zip(cases, colors):
        names, data = collect(case, "solverInfo")
        if data is None:
            continue
        t = data[:, 0]
        for f in fields:
            y = column(names, data, f"{f}_initial")
            if y is None:
                continue
            ax.semilogy(t, np.abs(y), lw=1.0,
                        color=None if single else c,
                        ls="-" if single else styles.get(f, "-"),
                        label=f if single else f"{label}: {f}")
    ax.set_xlabel("iteration")
    ax.set_ylabel("initial residual")
    ax.set_title("Residuals")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=7, ncol=2)


def plot_coeff(ax, cases, colors, key, title):
    """Means go in the legend, not as free-floating annotations -- with more
    than one case, annotations at a fixed corner draw on top of each other."""
    for (label, case), c in zip(cases, colors):
        names, data = collect(case, "forceCoeffs")
        if data is None:
            continue
        t, y = data[:, 0], column(names, data, key)
        if y is None:
            continue
        mean, sd, n = tail_mean(t, y)
        tag = label if not np.isfinite(mean) else f"{label}: {mean:.4f} ± {sd:.4f}"
        ax.plot(t, y, lw=1.0, color=c, label=tag)
        if np.isfinite(mean):
            ax.axhline(mean, ls="--", lw=0.8, alpha=0.5, color=c)
    ax.set_xlabel("iteration")
    ax.set_ylabel(key)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc="best")

    # the startup transient compresses the converged region into a flat line,
    # so clip the view to the settled part
    ys = [ln.get_ydata() for ln in ax.lines if len(ln.get_ydata()) > 10]
    if ys:
        tails = np.concatenate([y[int(0.4 * len(y)):] for y in ys])
        tails = tails[np.isfinite(tails)]
        if tails.size:
            lo, hi = tails.min(), tails.max()
            pad = max(0.05 * (hi - lo), 0.02 * abs(hi) + 1e-6)
            ax.set_ylim(lo - pad, hi + pad)


def plot_yplus(ax, cases, colors):
    plotted = False
    for (label, case), c in zip(cases, colors):
        a = yplus_history(case)
        if a is None:
            continue
        ax.plot(a[:, 0], a[:, 3], lw=1.2, color=c, label=f"{label}: avg")
        ax.fill_between(a[:, 0], a[:, 1], a[:, 2], color=c, alpha=0.10, lw=0)
        plotted = True
    if not plotted:
        ax.set_visible(False)
        return
    ax.set_yscale("log")          # min/max span two decades; linear hides the mean
    ax.set_xlabel("iteration")
    ax.set_ylabel("y+")
    ax.set_title(f"y+ on '{WALL_PATCH}' (band = min/max)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(fontsize=8)


# ------------------------------------------------------------------- main ---

def fmt(v, w, p=4):
    return f"{v:>{w}.{p}f}" if v is not None and np.isfinite(v) else f"{'-':>{w}}"


def main():
    args = sys.argv[1:] or ["."]
    cases = [(os.path.basename(os.path.abspath(a)) or "case", a) for a in args]

    missing = [c for _, c in cases
               if not os.path.isdir(os.path.join(c, "postProcessing"))]
    if missing:
        print("error: no postProcessing/ in: " + ", ".join(missing),
              file=sys.stderr)
        return 1

    cyc = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    colors = [cyc[i % len(cyc)] for i in range(len(cases))]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    plot_residuals(axes[0, 0], cases, colors)
    plot_coeff(axes[0, 1], cases, colors, "Cd", "Drag coefficient")
    plot_coeff(axes[1, 0], cases, colors, "Cl", "Lift coefficient")
    plot_yplus(axes[1, 1], cases, colors)
    fig.tight_layout()

    outdir = os.path.join(cases[0][1], "logs") if len(cases) == 1 else "plots"
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "summary.png")
    fig.savefig(out, dpi=150)
    print(f"wrote {out}\n")

    hdr = (f"{'case':<16}{'cells':>9}{'h [mm]':>9}{'layer%':>8}"
           f"{'iters':>7}{'y+':>7}{'Cd':>20}{'Cl':>20}")
    print(hdr)
    print("-" * len(hdr))
    for label, case in cases:
        names, data = collect(case, "forceCoeffs")
        info = case_info(case)
        cd = cl = (np.nan, np.nan, 0)
        if data is not None:
            t = data[:, 0]
            cd = tail_mean(t, column(names, data, "Cd"))
            cl = tail_mean(t, column(names, data, "Cl"))

        yp = yplus_history(case)
        ypv = yp[-1, 3] if yp is not None else np.nan

        cells = info["cells"]
        h = 1000 * (DOMAIN_VOLUME / cells) ** (1 / 3) if cells else np.nan

        print(f"{label:<16}"
              f"{cells if cells else '-':>9}"
              f"{fmt(h, 9, 3)}"
              f"{fmt(info['layer_pct'], 8, 1)}"
              f"{info['converged'] if info['converged'] else '-':>7}"
              f"{fmt(ypv, 7, 2)}"
              f"  {fmt(cd[0], 8)} ± {fmt(cd[1], 7, 5)}"
              f"  {fmt(cl[0], 8)} ± {fmt(cl[1], 7, 5)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())