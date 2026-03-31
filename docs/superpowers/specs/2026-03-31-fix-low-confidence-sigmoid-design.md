# Fix Low Confidence: Softmax → Sigmoid for Multilabel Model

**Date**: 2026-03-31
**Status**: Approved

## Problem

CardioFormer inference uses `F.softmax` to decode model output, but the model was trained as a **multilabel** classifier (BCE loss). Softmax forces probabilities to sum to 1, artificially suppressing per-class confidence. This causes all predictions to show 20-60% confidence regardless of input quality.

## Evidence

- Checkpoint config: `threshold: 0.5`, per-class binary confusion matrices
- Average 1.29 labels per sample in validation set (multilabel)
- Diagnostic test: sigmoid gives 0.80 confidence vs softmax 0.61 on same input
- Model code comment: "multilabel tasks" (cardioformer_model.py:507)

## Changes

### 1. `backend/ml/cardioformer_service.py` — Core fix

**Replace softmax with sigmoid in `predict_from_signal()`:**

```python
# Before
probabilities = F.softmax(logits, dim=1)
confidence, predicted = torch.max(probabilities, 1)

# After
probabilities = torch.sigmoid(logits)
```

**Redesign result format for multilabel:**

- `prediction`: class with highest sigmoid probability (primary diagnosis)
- `confidence`: sigmoid probability of the primary class
- `all_probabilities`: per-class sigmoid probabilities (no longer sum to 1)
- `detected_labels`: list of classes above threshold (default 0.5)
- `secondary_findings`: detected labels excluding the primary one

### 2. `backend/app/api/diagnosis.py` — API response

Add `detected_labels` and `secondary_findings` to `DiagnosisResponse`. Primary prediction + confidence remain for backward compatibility.

### 3. Normalization — No change

The double normalization (per-lead min-max → global z-score) is kept as-is because it matches the training pipeline. Verified by the comment in cardioformer_service.py:98-102 and diagnostic testing showing z-score improves logits.

## Test Plan

1. Unit test: verify sigmoid output is independent per class (not summing to 1)
2. Unit test: verify `detected_labels` returns correct classes above threshold
3. Integration test: load checkpoint, run dummy signal, assert confidence > 0.5
4. Compare test: same input, softmax vs sigmoid confidence values

## Out of Scope

- Threshold tuning (use 0.5 default, tune later with validation set)
- Normalization pipeline changes
- Frontend UI changes for multilabel display
