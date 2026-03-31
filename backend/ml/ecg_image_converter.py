"""
ECG Image to Signal Converter

Converts ECG images to 12-lead 1D signal format for CardioFormer model.

Robust pipeline:
  1. Preprocessing: correct grayscale, CLAHE, adaptive threshold, grid removal
  2. Layout detection: auto-detect row/column structure via projection profiles
  3. Trace extraction: center-of-mass tracking per column (not density)
  4. Quality validation: coverage and variance checks
"""

import logging

import cv2
import numpy as np
import torch
from scipy.signal import savgol_filter

logger = logging.getLogger(__name__)


class ECGImageToSignal:
    """
    Convert ECG image to 12-lead 1D signal with robust preprocessing.
    """

    def __init__(
        self,
        signal_length: int = 1000,
        num_leads: int = 12,
        sampling_rate: int = 500,
    ):
        self.signal_length = signal_length
        self.num_leads = num_leads
        self.sampling_rate = sampling_rate

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def extract_lead_signals(self, image: np.ndarray) -> np.ndarray:
        """
        Extract 1D signals from ECG image.

        Args:
            image: ECG image array [H, W, C] (RGB from PIL) or [H, W] (grayscale)

        Returns:
            signals: Extracted signals [num_leads, signal_length], float32
        """
        binary = self._preprocess(image)
        regions = self._detect_layout(binary)
        raw_signals = self._extract_traces(binary, regions)
        signals = self._postprocess(raw_signals)
        self._validate(signals)
        return signals

    def __call__(self, image: np.ndarray) -> torch.Tensor:
        """
        Convert image to tensor.

        Args:
            image: ECG image array

        Returns:
            tensor: Signal tensor [1, num_leads, signal_length]
        """
        signals = self.extract_lead_signals(image)
        tensor = torch.from_numpy(signals).float()
        tensor = tensor.unsqueeze(0)
        return tensor

    # ------------------------------------------------------------------
    # Step 1: Robust preprocessing
    # ------------------------------------------------------------------

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Grayscale -> CLAHE -> Otsu threshold -> light denoise.

        Grid line removal is intentionally skipped here: the trace extraction
        step (_extract_traces) uses a "shortest dark run" heuristic that
        naturally discriminates the trace from thicker grid lines, so upfront
        grid removal is unnecessary and risks destroying thin traces.

        Returns:
            binary: uint8 array, 255 = foreground (trace/grid), 0 = background
        """
        # Correct grayscale conversion (PIL gives RGB, not BGR)
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()

        # CLAHE contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Otsu adaptive threshold
        _, binary = cv2.threshold(
            enhanced, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )

        # Light noise cleanup (small isolated specks only)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        return binary

    # ------------------------------------------------------------------
    # Step 2: Layout detection
    # ------------------------------------------------------------------

    def _detect_layout(self, binary: np.ndarray) -> list:
        """
        Detect lead regions using projection profiles.

        Strategy:
          1. Horizontal projection → find candidate rows
          2. Filter out non-lead rows (title text, borders) by checking
             whether the row has a single wide content span vs fragmented
             text columns
          3. Determine layout type (horizontal strips vs grid) from the
             number of surviving rows
          4. Divide the lead area accordingly

        Returns:
            regions: list of (y_start, y_end, x_start, x_end) for each lead
        """
        height, width = binary.shape

        # --- Find candidate row regions via horizontal projection ---
        row_regions = self._find_projection_regions(
            np.sum(binary > 0, axis=1), height
        )

        if not row_regions:
            return self._naive_strips(binary)

        # --- Filter out non-lead rows (title text, annotations) ---
        lead_rows = []
        for ys, ye in row_regions:
            strip = binary[ys:ye, :]
            v_proj = np.sum(strip > 0, axis=0)

            # Compute the widest contiguous span of above-threshold columns
            col_regions = self._find_projection_regions(v_proj, width)
            if not col_regions:
                continue

            max_span = max(ce - cs for cs, ce in col_regions)
            # A lead trace spans most of the image width; title text
            # fragments into many small columns
            if max_span >= width * 0.4:
                lead_rows.append((ys, ye))

        # --- Determine layout from the number of lead rows ---
        n_rows = len(lead_rows)

        if n_rows >= self.num_leads - 2:
            # Horizontal strip layout (or close to it — missing 1-2 leads
            # at the image border is common).  Use equal division of the
            # lead area to guarantee exactly num_leads regions.
            return self._divide_lead_area(lead_rows, width)

        if n_rows >= 2:
            # Grid layout: N rows × M cols where N×M ≈ num_leads
            num_cols = max(1, self.num_leads // n_rows)
            return self._build_grid(lead_rows, num_cols, width)

        # Fallback: try common grid layouts on the full image
        for nr in [4, 3, 6, 2, 12]:
            if self.num_leads % nr != 0:
                continue
            nc = self.num_leads // nr
            regions = self._build_grid([(0, height)], nc, width)
            # Adjust rows
            result = []
            row_h = height // nr
            idx = 0
            for r in range(nr):
                ys = r * row_h
                ye = (r + 1) * row_h if r < nr - 1 else height
                for c_start, c_end in [(reg[2], reg[3]) for reg in regions[idx:idx + nc]]:
                    result.append((ys, ye, c_start, c_end))
                idx += nc
            if len(result) == self.num_leads:
                return result

        return self._naive_strips(binary)

    def _divide_lead_area(self, lead_rows: list, img_width: int) -> list:
        """
        Given a list of detected lead row boundaries, produce exactly
        num_leads regions by equal-division of the lead area.
        """
        # Use the span from first lead start to last lead end
        area_top = lead_rows[0][0]
        area_bot = lead_rows[-1][1]
        area_height = area_bot - area_top
        strip_h = area_height / self.num_leads

        margin_x = int(img_width * 0.02)
        return [
            (
                int(area_top + i * strip_h),
                int(area_top + (i + 1) * strip_h),
                margin_x,
                img_width - margin_x,
            )
            for i in range(self.num_leads)
        ]

    def _build_grid(
        self, row_bounds: list, num_cols: int, img_width: int
    ) -> list:
        """Build a row × col grid of regions."""
        regions = []
        col_w = img_width // num_cols
        for ys, ye in row_bounds:
            for c in range(num_cols):
                x_start = c * col_w
                x_end = (c + 1) * col_w if c < num_cols - 1 else img_width
                regions.append((ys, ye, x_start, x_end))
        return regions[: self.num_leads]

    def _find_projection_regions(
        self, projection: np.ndarray, total_length: int
    ) -> list:
        """
        Find contiguous regions from a 1D projection profile.

        Uses an adaptive threshold based on the projection's maximum value,
        then finds connected components above that threshold.

        Returns:
            list of (start, end) index pairs
        """
        if projection.max() == 0:
            return []

        # Smooth the projection
        kernel_size = max(3, total_length // 100)
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel = np.ones(kernel_size) / kernel_size
        smoothed = np.convolve(projection, kernel, mode="same")

        # Adaptive threshold: 15% of peak
        threshold = max(smoothed.max() * 0.15, 1.0)

        # Find connected regions above threshold
        above = smoothed > threshold
        regions = []
        start = None

        for i, active in enumerate(above):
            if active and start is None:
                start = i
            elif not active and start is not None:
                regions.append((start, i))
                start = None

        if start is not None:
            regions.append((start, len(above)))

        # Expand regions slightly (add margin, 2% on each side)
        margin = max(total_length // 50, 1)
        expanded = []
        for s, e in regions:
            s = max(0, s - margin)
            e = min(total_length, e + margin)
            expanded.append((s, e))

        return expanded

    def _naive_strips(self, binary: np.ndarray) -> list:
        """Fallback: simple horizontal strips."""
        height, width = binary.shape
        strip_h = height // self.num_leads
        return [
            (i * strip_h, (i + 1) * strip_h if i < self.num_leads - 1 else height, 0, width)
            for i in range(self.num_leads)
        ]

    # ------------------------------------------------------------------
    # Step 3: Trace extraction (shortest dark run per column)
    # ------------------------------------------------------------------

    def _extract_traces(self, binary: np.ndarray, regions: list) -> list:
        """
        Extract waveform trace from each lead region.

        Strategy: for each column in a lead strip, find all contiguous runs
        of dark pixels.  Grid lines produce *long* vertical/horizontal runs
        that span most of the strip height.  The ECG trace is a *short*
        run (2-6 px) that varies in y-position across columns.  We pick the
        shortest run closest to the strip centre — this reliably isolates
        the trace even when grid lines are present.

        Returns:
            list of 1D numpy arrays, one per lead
        """
        signals = []

        for y_start, y_end, x_start, x_end in regions:
            strip = binary[y_start:y_end, x_start:x_end]
            strip_h, strip_w = strip.shape
            centre_y = strip_h / 2.0

            signal = np.full(strip_w, np.nan)

            for col in range(strip_w):
                col_dark = strip[:, col] > 0
                runs = self._find_runs(col_dark)

                if not runs:
                    continue

                # Pick the best run: shortest, breaking ties by proximity to centre
                best = min(
                    runs,
                    key=lambda r: (
                        r[1] - r[0],               # primary: shortest length
                        abs((r[0] + r[1]) / 2 - centre_y),  # tie-break: closest to centre
                    ),
                )
                signal[col] = (best[0] + best[1]) / 2.0

            # Interpolate missing columns
            nan_mask = np.isnan(signal)
            if np.all(nan_mask):
                signal = np.full(strip_w, centre_y)  # flat line at centre
            elif np.any(nan_mask):
                valid_x = np.where(~nan_mask)[0]
                signal[nan_mask] = np.interp(
                    np.where(nan_mask)[0], valid_x, signal[valid_x]
                )

            # Invert y-axis (image y increases downward, ECG up = positive)
            signal = strip_h - 1 - signal

            # Normalize to [0, 1]
            sig_range = signal.max() - signal.min()
            if sig_range > 1e-8:
                signal = (signal - signal.min()) / sig_range
            else:
                signal = np.full(strip_w, 0.5)

            signals.append(signal)

        return signals

    @staticmethod
    def _find_runs(dark_mask: np.ndarray) -> list:
        """Find contiguous runs of True values in a 1D boolean array."""
        runs = []
        start = None
        for i, v in enumerate(dark_mask):
            if v and start is None:
                start = i
            elif not v and start is not None:
                runs.append((start, i))
                start = None
        if start is not None:
            runs.append((start, len(dark_mask)))
        return runs

    # ------------------------------------------------------------------
    # Step 4: Post-processing and quality validation
    # ------------------------------------------------------------------

    def _postprocess(self, raw_signals: list) -> np.ndarray:
        """
        Smooth, baseline-correct, and resize signals.

        Returns:
            signals: [num_leads, signal_length], float32
        """
        processed = []

        for signal in raw_signals:
            # Savitzky-Golay smoothing (preserve waveform shape)
            win = min(15, len(signal) // 4)
            if win % 2 == 0:
                win += 1
            if win >= 5:
                signal = savgol_filter(signal, win, 3)

            # Baseline correction: subtract moving average
            baseline_win = max(len(signal) // 10, 20)
            if baseline_win % 2 == 0:
                baseline_win += 1
            kernel = np.ones(baseline_win) / baseline_win
            baseline = np.convolve(signal, kernel, mode="same")
            signal = signal - baseline

            # Re-normalize to [0, 1] after baseline correction
            sig_range = signal.max() - signal.min()
            if sig_range > 1e-8:
                signal = (signal - signal.min()) / sig_range
            else:
                signal = np.zeros(len(signal))

            # Resize to target length via 1D interpolation
            x_old = np.linspace(0, 1, len(signal))
            x_new = np.linspace(0, 1, self.signal_length)
            signal = np.interp(x_new, x_old, signal).astype(np.float32)
            processed.append(signal)

        return np.array(processed, dtype=np.float32)

    def _validate(self, signals: np.ndarray) -> None:
        """
        Check signal quality and log warnings.
        """
        for i, lead in enumerate(signals):
            # Check flatness
            if lead.std() < 0.01:
                logger.warning("Lead %d appears flat (std=%.4f). Extraction may have failed.", i, lead.std())

            # Check coverage (non-zero proportion)
            coverage = np.count_nonzero(lead > 0.01) / len(lead)
            if coverage < 0.05:
                logger.warning("Lead %d has very low signal coverage (%.1f%%).", i, coverage * 100)


# ------------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------------

def create_dummy_ecg_signal(
    signal_length: int = 1000,
    num_leads: int = 12,
) -> torch.Tensor:
    """
    Create dummy ECG signal for testing.

    This generates realistic-looking ECG waveform.

    Args:
        signal_length: Length of signal
        num_leads: Number of leads

    Returns:
        ECG signal tensor [1, num_leads, signal_length]
    """
    signals = []

    for lead in range(num_leads):
        t = np.linspace(0, 10, signal_length)
        signal = np.zeros(signal_length)

        for beat in range(10):
            beat_start = int(beat * signal_length / 10)
            beat_end = int((beat + 0.8) * signal_length / 10)

            if beat_end > signal_length:
                beat_end = signal_length

            beat_len = beat_end - beat_start

            p_wave = 0.1 * np.sin(np.linspace(0, np.pi, beat_len // 4))

            qrs_len = beat_len // 6
            qrs = np.zeros(qrs_len)
            qrs[qrs_len // 4: qrs_len // 2] = -0.2
            qrs[qrs_len // 2: 3 * qrs_len // 4] = 1.0
            qrs[3 * qrs_len // 4:] = -0.3

            t_wave = 0.3 * np.sin(np.linspace(0, np.pi, beat_len // 3))

            beat_signal = np.zeros(beat_len)
            beat_signal[:len(p_wave)] = p_wave
            beat_signal[len(p_wave):len(p_wave) + len(qrs)] = qrs
            beat_signal[len(p_wave) + len(qrs):len(p_wave) + len(qrs) + len(t_wave)] = t_wave

            beat_signal += 0.02 * np.random.randn(beat_len)
            signal[beat_start:beat_end] = beat_signal

        baseline = 0.1 * np.sin(2 * np.pi * t / signal_length * 10)
        signal += baseline
        signals.append(signal)

    signals = np.array(signals)
    tensor = torch.from_numpy(signals).float()
    tensor = tensor.unsqueeze(0)

    return tensor


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    converter = ECGImageToSignal()

    if len(sys.argv) > 1:
        # Test with a real image
        from PIL import Image

        img_path = sys.argv[1]
        print(f"Loading image: {img_path}")
        img = np.array(Image.open(img_path).convert("RGB"))
        print(f"Image shape: {img.shape}")

        result = converter(img)
        print(f"Output tensor shape: {result.shape}")
        print(f"Value range: [{result.min():.4f}, {result.max():.4f}]")
        print(f"Mean: {result.mean():.4f}, Std: {result.std():.4f}")
    else:
        # Test with dummy
        dummy_image = np.random.randint(0, 255, (1200, 1000, 3), dtype=np.uint8)
        result = converter(dummy_image)
        print(f"Signal tensor shape: {result.shape}")

        dummy_signal = create_dummy_ecg_signal()
        print(f"Dummy signal shape: {dummy_signal.shape}")
