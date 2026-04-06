"""
ResNet 1D Baseline Model (Adapted from ECG-Research)

Original model for 1D ECG signal classification
Adapted for ECG image diagnosis system
"""
from __future__ import annotations

import logging
from typing import cast

import torch
from torch import Tensor, nn

logger = logging.getLogger(__name__)


class ResidualBlock1D(nn.Module):
    """1D Residual Block"""

    def __init__(
        self,
        *,
        in_channels: int,
        out_channels: int,
        stride: int,
    ) -> None:
        super().__init__()
        self._conv1 = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size=3,
            stride=stride,
            padding=1,
            bias=False,
        )
        self._bn1 = nn.BatchNorm1d(out_channels)
        self._conv2 = nn.Conv1d(
            out_channels,
            out_channels,
            kernel_size=3,
            stride=1,
            padding=1,
            bias=False,
        )
        self._bn2 = nn.BatchNorm1d(out_channels)
        self._relu = nn.ReLU(inplace=True)

        self._shortcut: nn.Module
        if stride != 1 or in_channels != out_channels:
            self._shortcut = nn.Sequential(
                nn.Conv1d(
                    in_channels,
                    out_channels,
                    kernel_size=1,
                    stride=stride,
                    bias=False,
                ),
                nn.BatchNorm1d(out_channels),
            )
        else:
            self._shortcut = nn.Identity()

    def forward(self, x: Tensor) -> Tensor:
        identity = self._shortcut(x)

        out = self._conv1(x)
        out = self._bn1(out)
        out = self._relu(out)

        out = self._conv2(out)
        out = self._bn2(out)
        out = out + identity
        out = self._relu(out)
        return cast(Tensor, out)


class ResNet1DBaseline(nn.Module):
    """
    ResNet 1D Baseline for ECG classification

    Args:
        num_classes: Number of output classes
        signal_length: Length of input signal (default 1000)
        input_channels: Number of input channels (12 for standard ECG)
        base_channels: Base number of channels
        dropout: Dropout rate
    """

    def __init__(
        self,
        *,
        num_classes: int = 5,
        signal_length: int = 1000,
        input_channels: int = 12,
        base_channels: int = 64,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        if num_classes <= 1:
            raise ValueError("num_classes must be > 1 for multilabel problems.")
        if signal_length <= 0:
            raise ValueError("signal_length must be positive.")
        if input_channels <= 0:
            raise ValueError("input_channels must be positive.")
        if base_channels <= 0:
            raise ValueError("base_channels must be positive.")

        self._num_classes = num_classes
        self._signal_length = signal_length
        self._input_channels = input_channels

        # Stem layer
        self._stem = nn.Sequential(
            nn.Conv1d(
                input_channels,
                base_channels,
                kernel_size=7,
                stride=2,
                padding=3,
                bias=False,
            ),
            nn.BatchNorm1d(base_channels),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(kernel_size=3, stride=2, padding=1),
        )

        # ResNet layers
        self._layer1 = self._make_layer(
            in_channels=base_channels,
            out_channels=base_channels,
            blocks=2,
            stride=1,
        )
        self._layer2 = self._make_layer(
            in_channels=base_channels,
            out_channels=base_channels * 2,
            blocks=2,
            stride=2,
        )
        self._layer3 = self._make_layer(
            in_channels=base_channels * 2,
            out_channels=base_channels * 4,
            blocks=2,
            stride=2,
        )

        # Classifier
        self._dropout = nn.Dropout(p=dropout)
        self._classifier = nn.Linear(base_channels * 4, num_classes)

    def _make_layer(
        self,
        *,
        in_channels: int,
        out_channels: int,
        blocks: int,
        stride: int,
    ) -> nn.Sequential:
        """Create a ResNet layer with multiple residual blocks"""
        layers: list[nn.Module] = [
            ResidualBlock1D(
                in_channels=in_channels,
                out_channels=out_channels,
                stride=stride,
            )
        ]
        for _ in range(1, blocks):
            layers.append(
                ResidualBlock1D(
                    in_channels=out_channels,
                    out_channels=out_channels,
                    stride=1,
                )
            )
        return nn.Sequential(*layers)

    def forward(self, x: Tensor) -> Tensor:
        """
        Forward pass

        Args:
            x: Input tensor of shape [B, C, T] where
               B = batch size
               C = number of channels (12 for standard ECG)
               T = signal length (1000)

        Returns:
            logits: Classification logits of shape [B, num_classes]
        """
        if x.dim() == 2:
            x = x.unsqueeze(1)
        if x.dim() != 3:
            raise ValueError("Input must have shape [B, C, T] or [B, T].")

        _, channels, timesteps = x.shape
        if timesteps != self._signal_length:
            raise ValueError(
                f"Expected signal length {self._signal_length}, received {timesteps}."
            )
        if channels != self._input_channels:
            raise ValueError(
                f"Input channels mismatch: expected {self._input_channels}, got {channels}."
            )

        # Feature extraction
        features = self._stem(x)
        features = self._layer1(features)
        features = self._layer2(features)
        features = self._layer3(features)

        # Global average pooling
        pooled = features.mean(dim=-1)

        # Classification
        logits = self._classifier(self._dropout(pooled))

        return logits


# PTB-XL superclass labels (Chinese, used by ConductionDisorderDetector)
PTBXL_SUPERCLASSES_CN = [
    "正常心电图",      # NORM
    "心肌梗死",        # MI
    "ST-T改变",        # STTC
    "传导障碍",        # CD
    "肥厚",            # HYP
]

# Keep old name for backward compatibility with test files
PTBXL_SUPERCLASSES = PTBXL_SUPERCLASSES_CN


def create_resnet1d_model(
    num_classes: int = 5,
    signal_length: int = 1000,
    input_channels: int = 12,
    pretrained: bool = False,
    checkpoint_path: str = None
) -> ResNet1DBaseline:
    """
    Create ResNet1D model

    Args:
        num_classes: Number of classes
        signal_length: Length of ECG signal
        input_channels: Number of input channels
        pretrained: Whether to load pretrained weights
        checkpoint_path: Path to checkpoint file

    Returns:
        ResNet1DBaseline model
    """
    model = ResNet1DBaseline(
        num_classes=num_classes,
        signal_length=signal_length,
        input_channels=input_channels,
    )

    if pretrained and checkpoint_path:
        logger.info("Loading ResNet1D weights from %s", checkpoint_path)
        checkpoint = torch.load(checkpoint_path, map_location='cpu')

        # Handle different checkpoint formats
        if 'state_dict' in checkpoint:
            state_dict = checkpoint['state_dict']
        elif 'model_state_dict' in checkpoint:
            state_dict = checkpoint['model_state_dict']
        else:
            state_dict = checkpoint

        # Remove 'model.' prefix if present
        new_state_dict = {}
        for k, v in state_dict.items():
            if k.startswith('model.'):
                new_state_dict[k[6:]] = v
            else:
                new_state_dict[k] = v

        model.load_state_dict(new_state_dict, strict=False)
        logger.info("ResNet1D weights loaded successfully")

    return model


if __name__ == "__main__":
    # Test the model
    model = ResNet1DBaseline(
        num_classes=5,
        signal_length=1000,
        input_channels=12,
    )

    # Test input
    x = torch.randn(2, 12, 1000)
    output = model(x)

    logger.info("Input shape: %s", x.shape)
    logger.info("Output shape: %s", output.shape)
    logger.info("Number of parameters: %s", f"{sum(p.numel() for p in model.parameters()):,}")
