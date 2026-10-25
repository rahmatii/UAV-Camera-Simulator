import sys

import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import pandas as pd

# ── Style Settings ──────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  "#0f1117",
    "axes.facecolor":    "#1a1d27",
    "axes.edgecolor":    "#2e3247",
    "axes.labelcolor":   "#c8cde0",
    "axes.titlecolor":   "#e8ebf5",
    "xtick.color":       "#7a80a0",
    "ytick.color":       "#7a80a0",
    "grid.color":        "#2e3247",
    "grid.linewidth":    0.6,
    "text.color":        "#c8cde0",
    "font.family":       "DejaVu Sans",
    "font.size":         9,
})

ACCENT   = "#4f9cf9"   # Blue
ACCENT2  = "#f97b4f"   # Orange
ACCENT3  = "#4ff9b4"   # Green


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {
        "frame_number", "timestamp_seconds",
        "pixel_x_col", "pixel_y_row",
        "altitude_meters", "latitude", "longitude",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"The following columns are missing from the file: {missing}")
    return df


def plot_all(df: pd.DataFrame, save_path: str = "output_plots.png"):
    fig = plt.figure(figsize=(16, 10), facecolor="#0f1117")
    fig.suptitle("Flight Path Analysis",
                 fontsize=15, color="#e8ebf5", fontweight="bold", y=0.98)

    gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.38,
                           left=0.07, right=0.97, top=0.92, bottom=0.08)

    t = df["timestamp_seconds"]

    # ── 1. Geographic Path (Lat / Lon) ────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    sc = ax1.scatter(df["longitude"], df["latitude"],
                     c=t, cmap="plasma", s=18, linewidths=0, zorder=3)
    ax1.plot(df["longitude"], df["latitude"],
             color=ACCENT, lw=0.6, alpha=0.35, zorder=2)
    cb = fig.colorbar(sc, ax=ax1, pad=0.02, fraction=0.045)
    cb.set_label("Time (seconds)", fontsize=8)
    cb.ax.yaxis.set_tick_params(color="#7a80a0")
    plt.setp(cb.ax.yaxis.get_ticklabels(), color="#7a80a0", fontsize=7)
    ax1.set_title("Geographic Path", fontsize=10)
    ax1.set_xlabel("Longitude")
    ax1.set_ylabel("Latitude")
    ax1.grid(True)

    # ── 2. Altitude over Time ────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.fill_between(t, df["altitude_meters"],
                     alpha=0.25, color=ACCENT2)
    ax2.plot(t, df["altitude_meters"], color=ACCENT2, lw=1.5)
    ax2.set_title("Altitude over Time", fontsize=10)
    ax2.set_xlabel("Time (seconds)")
    ax2.set_ylabel("Altitude (meters)")
    ax2.grid(True)

    # ── 3. Pixel Position (X-Y Image) ───────────────────────────────────
    ax3 = fig.add_subplot(gs[0, 2])
    sc3 = ax3.scatter(df["pixel_x_col"], df["pixel_y_row"],
                      c=t, cmap="viridis", s=14, linewidths=0, zorder=3)
    ax3.plot(df["pixel_x_col"], df["pixel_y_row"],
             color=ACCENT3, lw=0.5, alpha=0.3, zorder=2)
    cb3 = fig.colorbar(sc3, ax=ax3, pad=0.02, fraction=0.045)
    cb3.set_label("Time (seconds)", fontsize=8)
    cb3.ax.yaxis.set_tick_params(color="#7a80a0")
    plt.setp(cb3.ax.yaxis.get_ticklabels(), color="#7a80a0", fontsize=7)
    ax3.set_title("Pixel Path in Frame", fontsize=10)
    ax3.set_xlabel("Pixel X (column)")
    ax3.set_ylabel("Pixel Y (row)")
    ax3.invert_yaxis()   # Y-axis starts from top in images
    ax3.grid(True)

    # ── 4. Pixel X & Y over Time ───────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.plot(t, df["pixel_x_col"], color=ACCENT,  lw=1.4, label="X (column)")
    ax4.plot(t, df["pixel_y_row"],  color=ACCENT2, lw=1.4, label="Y (row)")
    ax4.set_title("Pixel Position over Time", fontsize=10)
    ax4.set_xlabel("Time (seconds)")
    ax4.set_ylabel("Pixel Value")
    ax4.legend(framealpha=0.3, fontsize=8)
    ax4.grid(True)

    # ── 5. Lat & Lon over Time ─────────────────────────────────────────
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.plot(t, df["latitude"],  color=ACCENT,  lw=1.4, label="Latitude")
    ax5.plot(t, df["longitude"], color=ACCENT3, lw=1.4, label="Longitude")
    ax5.set_title("Geographic Coordinates over Time", fontsize=10)
    ax5.set_xlabel("Time (seconds)")
    ax5.set_ylabel("Degrees")
    ax5.legend(framealpha=0.3, fontsize=8)
    ax5.grid(True)

    # ── 6. 3D Path Plot ────────────────────────────────────────────
    ax6 = fig.add_subplot(gs[1, 2], projection="3d")
    ax6.set_facecolor("#1a1d27")
    colors_3d = plt.cm.plasma(
        (t - t.min()) / max(t.max() - t.min(), 1e-9)
    )
    ax6.scatter(df["longitude"], df["latitude"], df["altitude_meters"],
                c=colors_3d, s=12, depthshade=True)
    ax6.plot(df["longitude"], df["latitude"], df["altitude_meters"],
             color=ACCENT, lw=0.5, alpha=0.4)
    ax6.set_title("3D Path", fontsize=10, pad=8)
    ax6.set_xlabel("Lon", fontsize=7, labelpad=4)
    ax6.set_ylabel("Lat", fontsize=7, labelpad=4)
    ax6.set_zlabel("Alt (m)", fontsize=7, labelpad=4)
    ax6.tick_params(labelsize=6)
    ax6.xaxis.pane.fill = False
    ax6.yaxis.pane.fill = False
    ax6.zaxis.pane.fill = False
    ax6.xaxis.pane.set_edgecolor("#2e3247")
    ax6.yaxis.pane.set_edgecolor("#2e3247")
    ax6.zaxis.pane.set_edgecolor("#2e3247")

    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor="#0f1117")
    print(f"✅ Plot saved: {save_path}")
    plt.show()


# ── Direct Execution ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data.csv"


    df = load_csv(csv_path)
    print(f"📊 Loaded {len(df)} rows.")
    plot_all(df, save_path="output_plots.png")