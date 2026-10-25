import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers the 3D projection)

def plot_trajectory(filepath):
    # خواندن فایل
    df = pd.read_excel(filepath)
    
    required_cols = ['X_m', 'Y_m', 'Z_m', 'lat', 'lon', 'alt']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"ستون '{col}' در فایل وجود ندارد!")
    
    X, Y, Z = df['X_m'].values, df['Y_m'].values, df['Z_m'].values
    lat, lon, alt = df['lat'].values, df['lon'].values, df['alt'].values
    
    # رنگ‌بندی بر اساس ارتفاع
    norm_alt = (Z - Z.min()) / (Z.max() - Z.min() + 1e-9)
    
    fig = plt.figure(figsize=(18, 14), facecolor='#0d1117')
    fig.suptitle('مسیر پهپاد', fontsize=18, color='white', fontweight='bold', y=0.98)
    
    # ---- نمودار 1: مسیر سه‌بعدی ----
    ax1 = fig.add_subplot(2, 2, 1, projection='3d', facecolor='#161b22')
    sc = ax1.scatter(X, Y, Z, c=norm_alt, cmap='plasma', s=2, alpha=0.8)
    ax1.plot(X, Y, Z, color='#58a6ff', linewidth=0.5, alpha=0.4)
    ax1.scatter(X[0], Y[0], Z[0], color='#3fb950', s=80, zorder=5, label='شروع')
    ax1.scatter(X[-1], Y[-1], Z[-1], color='#f85149', s=80, zorder=5, label='پایان')
    ax1.set_xlabel('X (m)', color='#8b949e', fontsize=8)
    ax1.set_ylabel('Y (m)', color='#8b949e', fontsize=8)
    ax1.set_zlabel('Z (m)', color='#8b949e', fontsize=8)
    ax1.set_title('مسیر سه‌بعدی', color='white', fontsize=11)
    ax1.tick_params(colors='#8b949e', labelsize=7)
    ax1.legend(fontsize=8, labelcolor='white', facecolor='#21262d')
    plt.colorbar(sc, ax=ax1, label='ارتفاع نرمال‌شده', shrink=0.6)
    
    # ---- نمودار 2: نمای بالا (X-Y) ----
    ax2 = fig.add_subplot(2, 2, 2, facecolor='#161b22')
    ax2.scatter(X, Y, c=norm_alt, cmap='plasma', s=2, alpha=0.8)
    ax2.plot(X, Y, color='#58a6ff', linewidth=0.6, alpha=0.4)
    ax2.scatter(X[0], Y[0], color='#3fb950', s=80, zorder=5, label='شروع', marker='^')
    ax2.scatter(X[-1], Y[-1], color='#f85149', s=80, zorder=5, label='پایان', marker='s')
    ax2.set_xlabel('X - شرق (m)', color='#8b949e')
    ax2.set_ylabel('Y - شمال (m)', color='#8b949e')
    ax2.set_title('نمای بالا (X-Y)', color='white', fontsize=11)
    ax2.tick_params(colors='#8b949e')
    ax2.legend(fontsize=8, labelcolor='white', facecolor='#21262d')
    ax2.grid(True, color='#21262d', linewidth=0.5)
    for spine in ax2.spines.values():
        spine.set_edgecolor('#30363d')
    
    # ---- نمودار 3: ارتفاع در طول زمان ----
    ax3 = fig.add_subplot(2, 2, 3, facecolor='#161b22')
    t = np.arange(len(Z))
    ax3.fill_between(t, Z, alpha=0.3, color='#58a6ff')
    ax3.plot(t, Z, color='#58a6ff', linewidth=1.2)
    ax3.plot(t, alt, color='#f0883e', linewidth=1.0, linestyle='--', alpha=0.7, label='alt GPS')
    ax3.set_xlabel('نمونه', color='#8b949e')
    ax3.set_ylabel('ارتفاع (m)', color='#8b949e')
    ax3.set_title('پروفایل ارتفاع', color='white', fontsize=11)
    ax3.tick_params(colors='#8b949e')
    ax3.legend(fontsize=8, labelcolor='white', facecolor='#21262d')
    ax3.grid(True, color='#21262d', linewidth=0.5)
    for spine in ax3.spines.values():
        spine.set_edgecolor('#30363d')
    
    # ---- نمودار 4: مسیر GPS (lat-lon) ----
    ax4 = fig.add_subplot(2, 2, 4, facecolor='#161b22')
    ax4.scatter(lon, lat, c=norm_alt, cmap='plasma', s=2, alpha=0.8)
    ax4.plot(lon, lat, color='#58a6ff', linewidth=0.6, alpha=0.4)
    ax4.scatter(lon[0], lat[0], color='#3fb950', s=80, zorder=5, label='شروع', marker='^')
    ax4.scatter(lon[-1], lat[-1], color='#f85149', s=80, zorder=5, label='پایان', marker='s')
    ax4.set_xlabel('طول جغرافیایی (lon)', color='#8b949e')
    ax4.set_ylabel('عرض جغرافیایی (lat)', color='#8b949e')
    ax4.set_title('مسیر GPS', color='white', fontsize=11)
    ax4.tick_params(colors='#8b949e')
    ax4.legend(fontsize=8, labelcolor='white', facecolor='#21262d')
    ax4.grid(True, color='#21262d', linewidth=0.5)
    for spine in ax4.spines.values():
        spine.set_edgecolor('#30363d')
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # ذخیره
    out_path = os.path.splitext(filepath)[0] + '_trajectory.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='#0d1117')
    print(f"✅ نمودار ذخیره شد: {out_path}")
    plt.show()


if __name__ == "__main__":
    plot_trajectory("../src/data2/trajectory_full_data.csv")