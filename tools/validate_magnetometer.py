import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

class MagneticYawCorrelation:
    """
    کلاس بررسی همبستگی داده‌های مغناطیسی با زاویه یاو در سیستم ENU
    """
    def __init__(self, filepath):
        self.filepath = filepath
        self.load_data()
        
    def load_data(self):
        """بارگذاری داده‌ها از فایل Excel"""
        df = pd.read_excel(self.filepath)
        
        # ستون‌های مورد نیاز
        required_cols = ['roll_rad', 'pitch_rad', 'yaw_rad',
                        'mag_x', 'mag_y', 'mag_z']
        
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            raise ValueError(f"ستون‌های زیر در فایل وجود ندارند: {missing}")
        
        # ذخیره داده‌ها
        self.roll = df['roll_rad'].values
        self.pitch = df['pitch_rad'].values
        self.yaw = df['yaw_rad'].values
        
        self.mag_body = df[['mag_x', 'mag_y', 'mag_z']].values
        
        print(f"✅ داده‌ها بارگذاری شدند: {len(self.mag_body)} نمونه")
        
    def body_to_enu(self, mag_body, roll, pitch, yaw):
        """
        تبدیل میدان مغناطیسی از دستگاه بدنه به ENU
        """
        # ماتریس چرخش Body → ENU
        Rz = np.array([
            [np.cos(yaw), -np.sin(yaw), 0],
            [np.sin(yaw), np.cos(yaw), 0],
            [0, 0, 1]
        ])
        
        Ry = np.array([
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)]
        ])
        
        Rx = np.array([
            [1, 0, 0],
            [0, np.cos(roll), -np.sin(roll)],
            [0, np.sin(roll), np.cos(roll)]
        ])
        
        R_body_to_enu = Rz @ Ry @ Rx
        mag_enu = R_body_to_enu @ mag_body
        
        return mag_enu
    
    def calculate_heading_from_mag(self, mag_enu):
        """
        محاسبه هدینگ از میدان مغناطیسی در ENU
        
        در ENU:
        - mag_x: East
        - mag_y: North
        - heading = atan2(mag_y, mag_x)  # زاویه از North
        """
        heading = np.degrees(np.arctan2(mag_enu[:, 1], mag_enu[:, 0]))
        heading = heading % 360  # نرمال‌سازی به 0-360
        return heading
    
    def analyze_yaw_correlation(self):
        """
        تحلیل کامل همبستگی داده‌های مغناطیسی با یاو
        """
        print("\n" + "="*70)
        print("تحلیل همبستگی داده‌های مغناطیسی با زاویه یاو (سیستم ENU)")
        print("="*70)
        
        n = len(self.mag_body)
        
        # 1. تبدیل داده‌های مغناطیسی از Body به ENU
        print("\n1. تبدیل داده‌های مغناطیسی به ENU...")
        self.mag_enu = np.zeros_like(self.mag_body)
        for i in range(n):
            self.mag_enu[i] = self.body_to_enu(
                self.mag_body[i],
                self.roll[i],
                self.pitch[i],
                self.yaw[i]
            )
        print(f"   ✅ تبدیل کامل شد.")
        
        # 2. محاسبه هدینگ از میدان مغناطیسی
        print("\n2. محاسبه هدینگ از میدان مغناطیسی...")
        self.heading_from_mag = self.calculate_heading_from_mag(self.mag_enu)
        
        # 3. تبدیل یاو به درجه و نرمال‌سازی
        self.yaw_deg = np.degrees(self.yaw) % 360
        
        # 4. محاسبه خطای هدینگ (دایره‌ای)
        self.heading_error = np.abs(self.heading_from_mag - self.yaw_deg)
        self.heading_error_circular = np.where(
            self.heading_error > 180,
            360 - self.heading_error,
            self.heading_error
        )
        
        # 5. محاسبه ضرایب همبستگی
        print("\n3. محاسبه ضرایب همبستگی...")
        
        # 5.1. همبستگی پیرسون (خطی)
        self.corr_pearson, self.p_value = pearsonr(self.yaw_deg, self.heading_from_mag)
        print(f"   همبستگی پیرسون: {self.corr_pearson:.6f}")
        print(f"   P-value: {self.p_value:.6e}")
        
        # 5.2. همبستگی دایره‌ای (Circular Correlation)
        self.corr_circular = self.circular_correlation(self.yaw_deg, self.heading_from_mag)
        print(f"   همبستگی دایره‌ای: {self.corr_circular:.6f}")
        
        # 5.3. همبستگی مولفه‌ها با سینوس/کسینوس یاو
        sin_yaw = np.sin(np.radians(self.yaw_deg))
        cos_yaw = np.cos(np.radians(self.yaw_deg))
        
        self.corr_magx_cos = np.corrcoef(self.mag_enu[:, 0], cos_yaw)[0, 1]
        self.corr_magy_sin = np.corrcoef(self.mag_enu[:, 1], sin_yaw)[0, 1]
        self.corr_magz_yaw = np.corrcoef(self.mag_enu[:, 2], self.yaw_deg)[0, 1]
        
        print(f"\n   همبستگی mag_x (East) با cos(yaw): {self.corr_magx_cos:.6f}")
        print(f"   همبستگی mag_y (North) با sin(yaw): {self.corr_magy_sin:.6f}")
        print(f"   همبستگی mag_z (Up) با yaw: {self.corr_magz_yaw:.6f}")
        
        # 6. آمار خطاها
        self.error_stats = {
            'mean_error': np.mean(self.heading_error_circular),
            'std_error': np.std(self.heading_error_circular),
            'min_error': np.min(self.heading_error_circular),
            'max_error': np.max(self.heading_error_circular),
            'percentile_95': np.percentile(self.heading_error_circular, 95),
            'percentile_99': np.percentile(self.heading_error_circular, 99)
        }
        
        print("\n4. آمار خطای هدینگ:")
        print(f"   میانگین خطا: {self.error_stats['mean_error']:.2f}°")
        print(f"   انحراف معیار: {self.error_stats['std_error']:.2f}°")
        print(f"   حداقل خطا: {self.error_stats['min_error']:.2f}°")
        print(f"   حداکثر خطا: {self.error_stats['max_error']:.2f}°")
        print(f"   صدک ۹۵: {self.error_stats['percentile_95']:.2f}°")
        print(f"   صدک ۹۹: {self.error_stats['percentile_99']:.2f}°")
        
        # 7. نتیجه‌گیری
        self.print_conclusion()
        
        return {
            'corr_pearson': self.corr_pearson,
            'corr_circular': self.corr_circular,
            'corr_magx_cos': self.corr_magx_cos,
            'corr_magy_sin': self.corr_magy_sin,
            'error_stats': self.error_stats
        }
    
    def circular_correlation(self, angle1, angle2):
        """
        محاسبه همبستگی دایره‌ای بین دو زاویه
        
        Args:
            angle1, angle2: زاویه‌ها بر حسب درجه (0-360)
        """
        angle1_rad = np.radians(angle1)
        angle2_rad = np.radians(angle2)
        
        # تبدیل به بردارهای واحد
        x1 = np.cos(angle1_rad)
        y1 = np.sin(angle1_rad)
        x2 = np.cos(angle2_rad)
        y2 = np.sin(angle2_rad)
        
        # همبستگی بین بردارها
        corr_x = np.corrcoef(x1, x2)[0, 1]
        corr_y = np.corrcoef(y1, y2)[0, 1]
        
        # میانگین همبستگی‌ها
        return (corr_x + corr_y) / 2
    
    def print_conclusion(self):
        """چاپ نتیجه‌گیری نهایی"""
        print("\n" + "="*70)
        print("نتیجه‌گیری")
        print("="*70)
        
        # معیارهای قبولی
        criteria = {
            'همبستگی پیرسون > 0.95': self.corr_pearson > 0.95,
            'همبستگی دایره‌ای > 0.95': self.corr_circular > 0.95,
            'خطای میانگین < 5°': self.error_stats['mean_error'] < 5,
            'صدک ۹۵ خطا < 15°': self.error_stats['percentile_95'] < 15,
            'همبستگی mag_x با cos(yaw) > 0.9': self.corr_magx_cos > 0.9,
            'همبستگی mag_y با sin(yaw) > 0.9': self.corr_magy_sin > 0.9
        }
        
        for criterion, passed in criteria.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{criterion:>40}: {status}")
        
        all_passed = all(criteria.values())
        
        print("\n" + "="*70)
        if all_passed:
            print("🎉 نتیجه: داده‌های مغناطیسی با موفقیت اعتبارسنجی شدند!")
            print("   همبستگی عالی با زاویه یاو نشان‌دهنده صحت شبیه‌سازی است.")
        else:
            print("⚠️ نتیجه: برخی از معیارهای اعتبارسنجی قبول نشدند.")
            print("   لطفاً پارامترهای شبیه‌سازی مغناطیسی را بازبینی کنید.")
        print("="*70)
    
    def plot_yaw_correlation(self, save_path=None):
        """رسم نمودارهای همبستگی با یاو"""
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('تحلیل همبستگی داده‌های مغناطیسی با زاویه یاو (سیستم ENU)', fontsize=16)
        
        # 1. مقایسه هدینگ و یاو
        ax1 = axes[0, 0]
        ax1.plot(self.heading_from_mag, 'b-', linewidth=1.5, label='هدینگ از مغناطیس', alpha=0.7)
        ax1.plot(self.yaw_deg, 'r--', linewidth=1.5, label='یاو واقعی', alpha=0.7)
        ax1.set_xlabel('نمونه')
        ax1.set_ylabel('زاویه (درجه)')
        ax1.set_title('مقایسه هدینگ و یاو')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. خطای هدینگ
        ax2 = axes[0, 1]
        ax2.plot(self.heading_error_circular, 'g-', linewidth=1, alpha=0.7)
        ax2.axhline(y=np.mean(self.heading_error_circular), color='r', linestyle='--',
                   label=f'میانگین: {np.mean(self.heading_error_circular):.2f}°')
        ax2.axhline(y=np.percentile(self.heading_error_circular, 95), color='orange', 
                   linestyle='--', label=f'صدک ۹۵: {np.percentile(self.heading_error_circular, 95):.2f}°')
        ax2.set_xlabel('نمونه')
        ax2.set_ylabel('خطای هدینگ (درجه)')
        ax2.set_title('خطای هدینگ در طول زمان')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # 3. توزیع خطا
        ax3 = axes[0, 2]
        ax3.hist(self.heading_error_circular, bins=50, alpha=0.7, edgecolor='black', linewidth=0.5)
        ax3.axvline(x=np.mean(self.heading_error_circular), color='r', linestyle='--',
                   label=f'میانگین: {np.mean(self.heading_error_circular):.2f}°')
        ax3.axvline(x=np.percentile(self.heading_error_circular, 95), color='orange', 
                   linestyle='--', label=f'صدک ۹۵: {np.percentile(self.heading_error_circular, 95):.2f}°')
        ax3.set_xlabel('خطای هدینگ (درجه)')
        ax3.set_ylabel('تعداد')
        ax3.set_title('توزیع خطای هدینگ')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. نمودار پراکندگی (هدینگ vs یاو)
        ax4 = axes[1, 0]
        ax4.scatter(self.yaw_deg, self.heading_from_mag, c=self.heading_error_circular, 
                   cmap='viridis', s=1, alpha=0.5)
        ax4.plot([0, 360], [0, 360], 'r--', linewidth=2, label='خط ایده‌آل (1:1)')
        ax4.set_xlabel('یاو واقعی (درجه)')
        ax4.set_ylabel('هدینگ از مغناطیس (درجه)')
        ax4.set_title(f'پراکندگی هدینگ vs یاو (همبستگی: {self.corr_pearson:.4f})')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        ax4.set_xlim(0, 360)
        ax4.set_ylim(0, 360)
        plt.colorbar(ax4.collections[0], ax=ax4, label='خطا (درجه)')
        
        # 5. مولفه‌های مغناطیسی در ENU
        ax5 = axes[1, 1]
        ax5.plot(self.mag_enu[:, 0], label='mag_x (East)', linewidth=1.5, alpha=0.7)
        ax5.plot(self.mag_enu[:, 1], label='mag_y (North)', linewidth=1.5, alpha=0.7)
        ax5.plot(self.mag_enu[:, 2], label='mag_z (Up)', linewidth=1.5, alpha=0.7)
        ax5.set_xlabel('نمونه')
        ax5.set_ylabel('میدان مغناطیسی (μT)')
        ax5.set_title('مولفه‌های میدان مغناطیسی در ENU')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # 6. همبستگی دایره‌ای
        ax6 = axes[1, 2]
        # رسم سینوس و کسینوس یاو
        yaw_rad = np.radians(self.yaw_deg)
        ax6.plot(np.cos(yaw_rad), np.sin(yaw_rad), 'b.', alpha=0.3, markersize=1, label='یاو واقعی')
        ax6.plot(self.mag_enu[:, 0]/np.mean(np.sqrt(self.mag_enu[:, 0]**2 + self.mag_enu[:, 1]**2)),
                self.mag_enu[:, 1]/np.mean(np.sqrt(self.mag_enu[:, 0]**2 + self.mag_enu[:, 1]**2)),
                'r.', alpha=0.3, markersize=1, label='مغناطیس (نرمال‌شده)')
        ax6.set_xlabel('cos(yaw) / mag_x')
        ax6.set_ylabel('sin(yaw) / mag_y')
        ax6.set_title(f'همبستگی دایره‌ای: {self.corr_circular:.4f}')
        ax6.legend()
        ax6.grid(True, alpha=0.3)
        ax6.set_aspect('equal')
        
        plt.tight_layout()
        
        if save_path is None:
            save_path = os.path.join(os.path.dirname(self.filepath), 'yaw_correlation_enu.png')
        
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"\n✅ نمودارها در {save_path} ذخیره شدند.")
        plt.show()
    
    def save_yaw_correlation_results(self):
        """ذخیره نتایج همبستگی با یاو در فایل Excel"""
        df_results = pd.DataFrame({
            'yaw_deg': self.yaw_deg,
            'heading_from_mag': self.heading_from_mag,
            'heading_error': self.heading_error_circular,
            'mag_enu_x': self.mag_enu[:, 0],
            'mag_enu_y': self.mag_enu[:, 1],
            'mag_enu_z': self.mag_enu[:, 2],
            'sin_yaw': np.sin(np.radians(self.yaw_deg)),
            'cos_yaw': np.cos(np.radians(self.yaw_deg))
        })
        
        save_path = os.path.join(os.path.dirname(self.filepath), 'yaw_correlation_results.xlsx')
        df_results.to_excel(save_path, index=False)
        print(f"\n✅ نتایج همبستگی در {save_path} ذخیره شدند.")
    
    def run_full_analysis(self):
        """اجرای کامل تحلیل همبستگی با یاو"""
        # 1. تحلیل
        results = self.analyze_yaw_correlation()
        
        # 2. رسم نمودارها
        self.plot_yaw_correlation()
        
        # 3. ذخیره نتایج
        self.save_yaw_correlation_results()
        
        return results


def main():
    """تابع اصلی برای اجرای تحلیل همبستگی با یاو"""
    
    input_file = "uav_frames_50_150_300_30_oval/Path_IMU.xlsx"
    
    print("="*70)
    print("تحلیل همبستگی داده‌های مغناطیسی با زاویه یاو (سیستم ENU)")
    print("="*70)
    
    # ایجاد شیء تحلیل
    analyzer = MagneticYawCorrelation(input_file)
    
    # اجرای تحلیل کامل
    results = analyzer.run_full_analysis()
    
    print("\n" + "="*70)
    print("✅ تحلیل همبستگی با یاو کامل شد!")
    print("="*70)
    
    return analyzer, results


if __name__ == "__main__":
    analyzer, results = main()