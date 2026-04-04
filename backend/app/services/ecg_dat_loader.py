"""
ECG Data Loader for PTB-XL format

Handles loading and preprocessing of .dat ECG files with accompanying .hea headers.
"""
import logging
import os
import numpy as np
from typing import Tuple, Optional
import wfdb
from scipy.signal import resample

logger = logging.getLogger(__name__)


class ECGDataLoader:
    """加载和处理PTB-XL格式的ECG数据文件"""

    def __init__(
        self,
        target_length: int = 1000,
        target_leads: int = 12,
        normalize: bool = True
    ):
        """
        初始化ECG数据加载器

        Args:
            target_length: 目标信号长度（采样点数）
            target_leads: 目标导联数（标准12导联）
            normalize: 是否归一化信号
        """
        self.target_length = target_length
        self.target_leads = target_leads
        self.normalize = normalize

    def load_dat_file(
        self,
        dat_path: str,
        check_header: bool = True
    ) -> Tuple[np.ndarray, dict]:
        """
        加载.dat文件（PTB-XL格式），返回12×1000的信号数组

        Args:
            dat_path: .dat文件路径（可以带或不带.dat扩展名）
            check_header: 是否检查.hea文件存在

        Returns:
            Tuple[np.ndarray, dict]:
                - signals: shape=(12, 1000), 12导联 × 1000采样点
                - metadata: 包含采样率、导联名等元数据

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        # 规范化路径（去掉.dat扩展名，wfdb会自动添加）
        record_name = dat_path.replace('.dat', '').replace('.hea', '')

        # 检查文件存在
        if not os.path.exists(f"{record_name}.dat"):
            raise FileNotFoundError(f"Data file not found: {record_name}.dat")

        if check_header and not os.path.exists(f"{record_name}.hea"):
            raise FileNotFoundError(f"Header file not found: {record_name}.hea")

        try:
            # 使用wfdb读取记录
            record = wfdb.rdrecord(record_name)

            # 获取信号数据 (samples, leads)
            signals = record.p_signal

            # 获取元数据
            metadata = {
                'fs': record.fs,  # 采样率
                'n_leads': signals.shape[1],
                'n_samples': signals.shape[0],
                'lead_names': record.sig_name if hasattr(record, 'sig_name') else None,
                'units': record.units if hasattr(record, 'units') else None,
            }

            logger.info("📊 Loaded ECG data from %s", os.path.basename(dat_path))
            logger.info("   Original shape: %s", signals.shape)
            logger.info("   Sample rate: %s Hz", metadata['fs'])
            logger.info("   Leads: %s", metadata['lead_names'])

            # 预处理信号
            signals = self._preprocess_signal(signals, metadata['fs'])

            return signals, metadata

        except Exception as e:
            raise ValueError(f"Failed to load ECG data: {str(e)}")

    def _preprocess_signal(
        self,
        signals: np.ndarray,
        original_fs: float
    ) -> np.ndarray:
        """
        预处理ECG信号

        Args:
            signals: 原始信号 (samples, leads)
            original_fs: 原始采样率

        Returns:
            处理后的信号 (leads, target_length)
        """
        # 1. 选择/重排导联到12导联
        if signals.shape[1] < self.target_leads:
            # 如果导联数不足，用零填充
            padding = np.zeros((signals.shape[0], self.target_leads - signals.shape[1]))
            signals = np.concatenate([signals, padding], axis=1)
            logger.warning("   ⚠️  Padded to %d leads with zeros", self.target_leads)
        elif signals.shape[1] > self.target_leads:
            # 如果导联数过多，只取前12个
            signals = signals[:, :self.target_leads]
            logger.info("   ℹ️  Truncated to %d leads", self.target_leads)

        # 2. 重采样到目标长度
        if signals.shape[0] != self.target_length:
            logger.info("   🔄 Resampling from %d to %d samples", signals.shape[0], self.target_length)
            signals = resample(signals, self.target_length, axis=0)

        # 3. 转置为 (leads, samples) 格式
        signals = signals.T  # (12, 1000)

        # 4. 归一化（如果需要）
        if self.normalize:
            # 对每个导联独立归一化到 [-1, 1]
            for i in range(signals.shape[0]):
                lead = signals[i, :]
                lead_min, lead_max = lead.min(), lead.max()
                if lead_max - lead_min > 1e-8:
                    signals[i, :] = 2 * (lead - lead_min) / (lead_max - lead_min) - 1

        return signals

    def validate_signal(self, signals: np.ndarray) -> bool:
        """
        验证信号格式是否正确

        Args:
            signals: 信号数组

        Returns:
            bool: 是否有效
        """
        if signals.shape != (self.target_leads, self.target_length):
            return False

        # 检查是否包含NaN或Inf
        if np.isnan(signals).any() or np.isinf(signals).any():
            return False

        return True


def create_test_ecg_signal(
    signal_length: int = 1000,
    num_leads: int = 12,
    signal_type: str = "normal"
) -> np.ndarray:
    """
    创建测试用的虚拟ECG信号

    Args:
        signal_length: 信号长度
        num_leads: 导联数
        signal_type: 信号类型 ("normal", "abnormal")

    Returns:
        测试信号 (num_leads, signal_length)
    """
    t = np.linspace(0, 2 * np.pi, signal_length)

    # 创建基本的ECG波形（简化的P-QRS-T波）
    def simple_ecg(t, hr_factor=1.0):
        """简化ECG波形"""
        # P波
        p = 0.15 * np.sin(hr_factor * t * 2)

        # QRS波群
        qrs = np.zeros_like(t)
        qrs_peak = int(len(t) * 0.1)
        qrs_width = max(1, len(t) // 50)
        for i in range(-qrs_width, qrs_width + 1):
            idx = (np.arange(len(t)) + i) % len(t)
            qrs[idx] += 1.0 * np.exp(-0.5 * (i / qrs_width) ** 2)

        # T波
        t_wave = 0.3 * np.sin(hr_factor * t * 0.5 + np.pi / 4)

        ecg = p + qrs + t_wave

        # 添加噪声
        noise = 0.05 * np.random.randn(len(t))

        return ecg + noise

    # 为每个导联创建略微不同的信号
    signals = np.zeros((num_leads, signal_length))

    for i in range(num_leads):
        # 不同导联有不同的幅度和相位
        amplitude = 1.0 - 0.1 * abs(i - 5.5)
        phase_shift = i * 0.05
        hr_factor = 1.0 + 0.05 * i

        ecg_signal = simple_ecg(t + phase_shift, hr_factor)
        signals[i, :] = amplitude * ecg_signal

    if signal_type == "abnormal":
        # 添加异常特征（例如ST段抬高）
        signals[0, 200:300] += 0.3
        signals[1, 200:300] -= 0.2

    # 归一化
    for i in range(num_leads):
        signals[i, :] = (signals[i, :] - signals[i, :].mean()) / (signals[i, :].std() + 1e-8)

    return signals


if __name__ == "__main__":
    # 测试代码
    print("Testing ECGDataLoader...")

    # 创建测试信号
    test_signal = create_test_ecg_signal()
    print(f"\n✅ Created test signal: {test_signal.shape}")

    # 验证信号
    loader = ECGDataLoader()
    is_valid = loader.validate_signal(test_signal)
    print(f"   Valid: {is_valid}")

    print("\n💡 To test with real .dat file:")
    print("   loader = ECGDataLoader()")
    print("   signals, metadata = loader.load_dat_file('path/to/record.dat')")
