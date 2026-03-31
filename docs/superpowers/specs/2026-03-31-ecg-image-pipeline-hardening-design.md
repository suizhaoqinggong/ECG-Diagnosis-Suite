# ECG Image Pipeline Hardening Design

Date: 2026-03-31

## Problem

The image-to-diagnosis pipeline has three categories of vulnerabilities:

1. **No input validation gate**: Non-ECG images are silently converted to plausible signals and classified with high confidence. Codex confirmed a random RGB image was classified as "传导障碍" at 78% confidence.
2. **Fragile image-to-signal conversion**: Layout detection, trace extraction, and normalization break on real-world inputs (rotated photos, cropped ECGs, non-standard layouts, stamps/labels).
3. **No observability**: When extraction fails or falls back to naive heuristics, there is no structured metadata to indicate this. Users receive plausible-looking results with no quality indicators.

## Approach

Incremental hardening of the existing heuristic converter (no neural network replacement). Three layers, executed sequentially with test-first development and code review gates between each.

## Layer 1: Input Validation Gate

### Goal

Reject non-ECG and severely degraded images before they reach the model, returning clear 4xx HTTP errors.

### Changes

#### New file: `backend/ml/image_validator.py`

`validate_ecg_image(image: np.ndarray) -> ValidationResult`

Checks:
- **Dimensions**: minimum 200x200 pixels, maximum 8000x8000 pixels
- **EXIF orientation**: correct using PIL's `ImageOps.exif_transpose` before numpy conversion
- **Content density**: dark-pixel ratio must be within ECG-typical range (1%-60% after binary threshold)
- **Row structure**: horizontal projection must show at least 4 distinct content bands (otherwise it's likely not an ECG)
- **Aspect ratio**: reject extreme aspect ratios (< 0.3 or > 5.0) that can't be standard ECG printouts

Returns `ValidationResult(passed: bool, reason: str | None)`.

On failure, raises `ValueError` with a user-facing message.

#### Modify: `backend/app/api/diagnosis.py`

In `_diagnose_image_file()`:
- Call `validate_ecg_image()` before conversion
- Catch `ValueError` and return HTTP 400 with the validation reason
- Catch shape mismatches from converter and return HTTP 400 (not 500)

#### Modify: `backend/ml/ecg_image_converter.py`

In `_detect_layout()`:
- If layout detection returns fewer regions than `num_leads`, return the `naive_strips` fallback but set a flag indicating degraded quality

### Test Cases

| Test | Input | Expected |
|------|-------|----------|
| random RGB image | `np.random.randint(0,255,(800,600,3))` | 400, "does not appear to be an ECG" |
| pure white image | `np.full((800,600,3), 255)` | 400, validation failure |
| pure black image | `np.full((800,600,3), 0)` | 400, validation failure |
| tiny image | `np.random.randint(0,255,(50,50,3))` | 400, dimension check |
| cropped ECG (triggers <12 regions) | synthetic: strip with only 8 content rows | 400 or low_confidence flag, not 500 |
| valid ECG image | real ECG sample | passes validation, 200 |

## Layer 2: Conversion Accuracy

### Goal

Make the image-to-signal converter robust to real-world inputs: rotated photos, glare, non-standard layouts, stamps/labels.

### Changes

#### Modify: `backend/ml/ecg_image_converter.py`

**EXIF orientation correction** (in `diagnosis.py`, before calling validator):
- Apply `PIL.ImageOps.exif_transpose` when opening the image, before converting to numpy
- This ensures all downstream processing works with correctly oriented images

**Enhanced layout detection** in `_detect_layout()`:
- Add explicit support for common ECG layouts:
  - 12x1 horizontal strips (most common)
  - 6x2 grid
  - 4x3 + 1 rhythm strip (3x4+1)
  - 3x4 grid
- After projection-based detection, validate: detected regions count must match `num_leads`. If not, try the next layout template.
- Record which layout method was used in the result

**Improved trace extraction** in `_extract_traces()`:
- After selecting the best run per column, add a continuity filter: if the selected y-position jumps more than 20% of strip height from the previous column, prefer the next-best run instead
- Filter out runs that are shorter than 2 pixels or longer than 40% of strip height (grid lines)
- Track the number of interpolated (missing) columns per lead

**Improved normalization** in `_postprocess()`:
- Replace per-lead min-max normalization with a shared scale factor derived from the global signal range across all leads
- Preserve inter-lead amplitude relationships
- Use percentile-based clipping (1st and 99th) instead of min/max to reduce sensitivity to outliers

**Rotation/skew detection**:
- Add `_detect_skew()` using Hough line transform on the binary image
- If skew angle > 2 degrees, apply affine correction before layout detection
- Skip correction if angle is too large (> 30 degrees) and flag as potentially invalid

### Test Cases

| Test | Input | Expected |
|------|-------|----------|
| rotated ECG (90 deg) | ECG image rotated 90 deg | layout detection still finds leads |
| skewed ECG (5 deg) | ECG image with slight skew | skew corrected, extraction succeeds |
| image with stamp/label overlay | ECG with text annotations | trace extraction ignores annotations |
| non-standard layout (3x4+1) | 13-row ECG | correctly maps to 12 leads |
| different background colors | ECG on colored paper | Otsu still separates trace |
| high-contrast vs low-contrast | two versions of same ECG | both produce similar signals |

## Layer 3: Observability

### Goal

Return structured QC metadata so users and developers can assess result reliability.

### Changes

#### New file: `backend/ml/extraction_result.py`

```python
@dataclass
class ExtractionResult:
    signals: np.ndarray                              # [num_leads, signal_length]
    layout_method: str                               # "projection" | "grid" | "fallback"
    per_lead_qc: list[LeadQC]                        # one per lead
    warnings: list[str]                              # human-readable warnings
    fallback_used: bool                              # whether any fallback was triggered
    interpolated_columns: list[int]                  # count per lead

@dataclass
class LeadQC:
    flatness: float       # std of signal (0 = flat, higher = more content)
    coverage: float       # fraction of non-near-zero samples
    snr_estimate: float   # signal variance / noise floor estimate
    quality: str          # "good" | "degraded" | "failed"
```

#### Modify: `backend/ml/ecg_image_converter.py`

- `extract_lead_signals()` returns `ExtractionResult` instead of `np.ndarray`
- `__call__()` unwraps the signals for backward compatibility
- Each step populates its portion of the metadata

#### Modify: `backend/app/api/diagnosis.py`

- Include QC metadata in the API response
- Add `quality_warning` field to `DiagnosisResponse`
- When QC indicates degraded quality, add a prominent note in the report

#### Modify: `frontend/src/api/index.ts` and relevant components

- Parse `quality_warning` from API response
- Display QC warnings alongside diagnosis results

### Test Cases

| Test | Input | Expected |
|------|-------|----------|
| normal ECG | real sample | `fallback_used=False`, no warnings |
| degraded image | noisy/blurred ECG | specific warnings, `quality="degraded"` |
| fallback-triggered | image forcing naive strips | `fallback_used=True`, `layout_method="fallback"` |
| frontend QC display | response with warnings | warning banner visible in UI |

## Execution Order

```
Layer 1 (Input Validation)
  -> write tests -> implement -> tests pass -> code review
  -> proceed

Layer 2 (Conversion Accuracy)
  -> write tests -> implement -> tests pass -> code review
  -> proceed

Layer 3 (Observability)
  -> write tests -> implement -> tests pass -> code review
  -> done
```

## Constraints

- All changes use the existing heuristic approach (no neural network replacements)
- Backend formatting: `black` + `isort`
- Frontend formatting: project ESLint config
- Tests: `pytest` for backend, `vitest` for frontend
- Each layer must not break existing tests
- Error messages should be user-facing (Chinese-first, matching existing style)
