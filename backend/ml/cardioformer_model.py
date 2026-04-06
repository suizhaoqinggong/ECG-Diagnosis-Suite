"""
CardioFormer Model (Standalone Version)

Adapted from ECG-Research for ECG Diagnosis Suite
Original: Multi-granularity transformer for ECG classification
This version: Standalone implementation without framework dependencies
"""
from __future__ import annotations

import logging
import math
import random
from collections.abc import Sequence
from typing import cast

import torch
import torch.nn.functional as functional
from torch import Tensor, nn

logger = logging.getLogger(__name__)


def parse_int_list(raw: str | Sequence[int], *, name: str) -> tuple[int, ...]:
    if isinstance(raw, str):
        values = [item.strip() for item in raw.split(",")]
        if any(not item for item in values):
            raise ValueError(f"{name} contains empty items.")
        parsed = tuple(int(item) for item in values)
    else:
        parsed = tuple(int(item) for item in raw)
    if not parsed:
        raise ValueError(f"{name} cannot be empty.")
    if any(value <= 0 for value in parsed):
        raise ValueError(f"{name} values must be positive integers.")
    return parsed


def parse_string_list(raw: str | Sequence[str], *, name: str) -> tuple[str, ...]:
    if isinstance(raw, str):
        parsed = tuple(item.strip() for item in raw.split(","))
    else:
        parsed = tuple(item.strip() for item in raw)
    if not parsed:
        raise ValueError(f"{name} cannot be empty.")
    if any(not item for item in parsed):
        raise ValueError(f"{name} contains empty items.")
    return parsed


class PositionalEmbedding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 5000) -> None:
        super().__init__()
        position = torch.arange(0, max_len, dtype=torch.float32).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2, dtype=torch.float32) * (-(math.log(10000.0) / d_model))
        )
        pe = torch.zeros(max_len, d_model, dtype=torch.float32)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("_pe", pe.unsqueeze(0), persistent=False)

    def forward(self, x: Tensor) -> Tensor:
        positional = cast(Tensor, self._pe)
        return positional[:, : x.size(1)]


class Jitter(nn.Module):
    def __init__(self, scale: float = 0.1) -> None:
        super().__init__()
        self._scale = scale

    def forward(self, x: Tensor) -> Tensor:
        if not self.training:
            return x
        return x + torch.randn_like(x) * self._scale


class Scale(nn.Module):
    def __init__(self, scale: float = 0.1) -> None:
        super().__init__()
        self._scale = scale

    def forward(self, x: Tensor) -> Tensor:
        if not self.training:
            return x
        factor = 1.0 + torch.randn(x.shape[0], x.shape[1], 1, device=x.device) * self._scale
        return x * factor


class Flip(nn.Module):
    def __init__(self, prob: float = 0.5) -> None:
        super().__init__()
        self._prob = prob

    def forward(self, x: Tensor) -> Tensor:
        if self.training and torch.rand(1, device=x.device).item() < self._prob:
            return torch.flip(x, dims=[-1])
        return x


class Shuffle(nn.Module):
    def __init__(self, prob: float = 0.5) -> None:
        super().__init__()
        self._prob = prob

    def forward(self, x: Tensor) -> Tensor:
        if not self.training:
            return x
        if torch.rand(1, device=x.device).item() >= self._prob:
            return x
        permutation = torch.randperm(x.shape[1], device=x.device)
        return x[:, permutation, :]


class TemporalMask(nn.Module):
    def __init__(self, ratio: float = 0.1) -> None:
        super().__init__()
        self._ratio = ratio

    def forward(self, x: Tensor) -> Tensor:
        if not self.training:
            return x
        timesteps = x.shape[1]
        mask_size = int(timesteps * self._ratio)
        if mask_size <= 0:
            return x
        indices = torch.randperm(timesteps, device=x.device)[:mask_size]
        masked = x.clone()
        masked[:, indices, :] = 0.0
        return masked


class FrequencyMask(nn.Module):
    def __init__(self, ratio: float = 0.1) -> None:
        super().__init__()
        self._ratio = ratio

    def forward(self, x: Tensor) -> Tensor:
        if not self.training:
            return x
        frequency = torch.fft.rfft(x, dim=-1)
        keep = torch.rand_like(frequency.real) > self._ratio
        masked = frequency * keep
        return cast(Tensor, torch.fft.irfft(masked, n=x.shape[-1], dim=-1))


def build_augmentation(name: str) -> nn.Module:
    if name.startswith("jitter"):
        return Jitter(0.1 if len(name) == 6 else float(name[6:]))
    if name.startswith("scale"):
        return Scale(0.1 if len(name) == 5 else float(name[5:]))
    if name.startswith("drop"):
        return nn.Dropout(0.1 if len(name) == 4 else float(name[4:]))
    if name.startswith("flip"):
        return Flip(0.5 if len(name) == 4 else float(name[4:]))
    if name.startswith("shuffle"):
        return Shuffle(0.5 if len(name) == 7 else float(name[7:]))
    if name.startswith("frequency"):
        return FrequencyMask(0.1 if len(name) == 9 else float(name[9:]))
    if name.startswith("mask"):
        return TemporalMask(0.1 if len(name) == 4 else float(name[4:]))
    if name == "none":
        return nn.Identity()
    raise ValueError(f"Unsupported augmentation: {name}")


class CrossChannelTokenEmbedding(nn.Module):
    def __init__(self, *, channels: int, patch_len: int, d_model: int, stride: int) -> None:
        super().__init__()
        self._token_conv = nn.Conv2d(
            in_channels=1,
            out_channels=d_model,
            kernel_size=(channels, patch_len),
            stride=(1, stride),
            padding=0,
            padding_mode="circular",
            bias=False,
        )
        nn.init.kaiming_normal_(self._token_conv.weight, mode="fan_in", nonlinearity="leaky_relu")

    def forward(self, x: Tensor) -> Tensor:
        return cast(Tensor, self._token_conv(x))


class ListPatchEmbedding(nn.Module):
    def __init__(
        self,
        *,
        input_channels: int,
        d_model: int,
        patch_lengths: tuple[int, ...],
        dropout: float,
        augmentations: tuple[str, ...],
        single_channel: bool,
    ) -> None:
        super().__init__()
        self._single_channel = single_channel
        self._patch_lengths = patch_lengths
        self._paddings = nn.ModuleList(
            [nn.ReplicationPad1d((0, stride)) for stride in patch_lengths]
        )
        channels = 1 if single_channel else input_channels
        self._value_embeddings = nn.ModuleList(
            [
                CrossChannelTokenEmbedding(
                    channels=channels,
                    patch_len=patch_len,
                    d_model=d_model,
                    stride=patch_len,
                )
                for patch_len in patch_lengths
            ]
        )
        self._position_embedding = PositionalEmbedding(d_model=d_model)
        self._dropout = nn.Dropout(dropout)
        self._augmentations = nn.ModuleList([build_augmentation(name) for name in augmentations])
        self._learnable_embeddings = nn.ParameterList(
            [nn.Parameter(torch.randn(1, d_model)) for _ in patch_lengths]
        )

    def forward(self, x: Tensor) -> list[Tensor]:
        x = x.permute(0, 2, 1)
        if self._single_channel:
            batch_size, channels, timesteps = x.shape
            x = x.reshape(batch_size * channels, 1, timesteps)

        embedded: list[Tensor] = []
        for padding, value_embedding, context_embedding in zip(
            self._paddings,
            self._value_embeddings,
            self._learnable_embeddings,
            strict=True,
        ):
            patched = padding(x).unsqueeze(1)
            patched = value_embedding(patched)
            patched = patched.squeeze(2).transpose(1, 2)
            augmentation_index = random.randint(0, len(self._augmentations) - 1)
            patched = self._augmentations[augmentation_index](patched)
            positioned = patched + context_embedding + self._position_embedding(patched)
            embedded.append(self._dropout(positioned))
        return embedded


class FullAttention(nn.Module):
    def __init__(self, *, dropout: float, output_attention: bool) -> None:
        super().__init__()
        self._dropout = nn.Dropout(dropout)
        self._output_attention = output_attention

    def forward(
        self,
        queries: Tensor,
        keys: Tensor,
        values: Tensor,
    ) -> tuple[Tensor, Tensor | None]:
        _, _, _, head_dim = queries.shape
        scale = 1.0 / math.sqrt(float(head_dim))
        scores = torch.einsum("blhe,bshe->bhls", queries, keys)
        attention = torch.softmax(scale * scores, dim=-1)
        attention = self._dropout(attention)
        output = torch.einsum("bhls,bshd->blhd", attention, values).contiguous()
        if self._output_attention:
            return output, attention
        return output, None


class AttentionLayer(nn.Module):
    def __init__(
        self,
        *,
        d_model: int,
        n_heads: int,
        dropout: float,
        output_attention: bool,
    ) -> None:
        super().__init__()
        if d_model % n_heads != 0:
            raise ValueError("d_model must be divisible by n_heads.")
        self._n_heads = n_heads
        self._head_dim = d_model // n_heads
        self._attention = FullAttention(dropout=dropout, output_attention=output_attention)
        self._query_projection = nn.Linear(d_model, d_model)
        self._key_projection = nn.Linear(d_model, d_model)
        self._value_projection = nn.Linear(d_model, d_model)
        self._out_projection = nn.Linear(d_model, d_model)

    def forward(
        self,
        queries: Tensor,
        keys: Tensor,
        values: Tensor,
    ) -> tuple[Tensor, Tensor | None]:
        batch_size, query_length, _ = queries.shape
        _, key_length, _ = keys.shape
        projected_queries = self._query_projection(queries).view(
            batch_size, query_length, self._n_heads, self._head_dim
        )
        projected_keys = self._key_projection(keys).view(
            batch_size, key_length, self._n_heads, self._head_dim
        )
        projected_values = self._value_projection(values).view(
            batch_size, key_length, self._n_heads, self._head_dim
        )
        attended, attention = self._attention(projected_queries, projected_keys, projected_values)
        return self._out_projection(attended.reshape(batch_size, query_length, -1)), attention


class CardioformerLayer(nn.Module):
    def __init__(
        self,
        *,
        num_granularity: int,
        d_model: int,
        n_heads: int,
        dropout: float,
        output_attention: bool,
        no_inter_attn: bool,
    ) -> None:
        super().__init__()
        self._intra_attentions = nn.ModuleList(
            [
                AttentionLayer(
                    d_model=d_model,
                    n_heads=n_heads,
                    dropout=dropout,
                    output_attention=output_attention,
                )
                for _ in range(num_granularity)
            ]
        )
        self._inter_attention = None
        if not no_inter_attn and num_granularity > 1:
            self._inter_attention = AttentionLayer(
                d_model=d_model,
                n_heads=n_heads,
                dropout=dropout,
                output_attention=output_attention,
            )

    def forward(self, x: list[Tensor]) -> tuple[list[Tensor], list[Tensor | None]]:
        intra_outputs: list[Tensor] = []
        attentions: list[Tensor | None] = []
        for tensor, attention_layer in zip(x, self._intra_attentions, strict=True):
            updated, weights = attention_layer(tensor, tensor, tensor)
            intra_outputs.append(updated)
            attentions.append(weights)

        if self._inter_attention is None:
            return intra_outputs, attentions

        routers = torch.cat([tensor[:, -1:, :] for tensor in intra_outputs], dim=1)
        inter_out, inter_attn = self._inter_attention(routers, routers, routers)
        merged = [
            torch.cat([tensor[:, :-1, :], inter_out[:, index : index + 1, :]], dim=1)
            for index, tensor in enumerate(intra_outputs)
        ]
        attentions.append(inter_attn)
        return merged, attentions


class ResNetBlockType1(nn.Module):
    def __init__(self, *, d_model: int, d_ff: int, dropout: float, activation: str) -> None:
        super().__init__()
        self._conv1 = nn.Conv1d(in_channels=d_model, out_channels=d_ff, kernel_size=1)
        self._conv2 = nn.Conv1d(in_channels=d_ff, out_channels=d_model, kernel_size=1)
        self._norm = nn.LayerNorm(d_model)
        self._dropout = nn.Dropout(dropout)
        if activation not in {"relu", "gelu"}:
            raise ValueError("activation must be either 'relu' or 'gelu'.")
        self._activation = functional.relu if activation == "relu" else functional.gelu

    def forward(self, x: Tensor) -> Tensor:
        residual = x
        out = self._activation(self._conv1(x.transpose(1, 2)))
        out = self._dropout(out)
        out = self._conv2(out).transpose(1, 2)
        out = self._dropout(out)
        return cast(Tensor, self._norm(residual + out))


class EncoderLayer(nn.Module):
    def __init__(
        self,
        *,
        num_granularity: int,
        d_model: int,
        n_heads: int,
        d_ff: int,
        dropout: float,
        activation: str,
        output_attention: bool,
        no_inter_attn: bool,
    ) -> None:
        super().__init__()
        self._attention = CardioformerLayer(
            num_granularity=num_granularity,
            d_model=d_model,
            n_heads=n_heads,
            dropout=dropout,
            output_attention=output_attention,
            no_inter_attn=no_inter_attn,
        )
        self._norm1 = nn.LayerNorm(d_model)
        self._norm2 = nn.LayerNorm(d_model)
        self._dropout = nn.Dropout(dropout)
        self._resblock1 = ResNetBlockType1(
            d_model=d_model,
            d_ff=d_ff,
            dropout=dropout,
            activation=activation,
        )
        self._resblock2 = ResNetBlockType1(
            d_model=d_model,
            d_ff=d_ff,
            dropout=dropout,
            activation=activation,
        )
        self._resblock3 = ResNetBlockType1(
            d_model=d_model,
            d_ff=d_ff,
            dropout=dropout,
            activation=activation,
        )

    def forward(self, x: list[Tensor]) -> tuple[list[Tensor], list[Tensor | None]]:
        updated, attentions = self._attention(x)
        residual_added = [
            tensor + self._dropout(delta)
            for tensor, delta in zip(x, updated, strict=True)
        ]
        residual_norm = [self._norm1(tensor) for tensor in residual_added]
        residual_norm = [self._resblock1(tensor) for tensor in residual_norm]
        residual_norm = [self._resblock2(tensor) for tensor in residual_norm]
        residual_norm = [self._resblock3(tensor) for tensor in residual_norm]
        output = [
            self._norm2(base + enhancement)
            for base, enhancement in zip(residual_added, residual_norm, strict=True)
        ]
        return output, attentions


class Encoder(nn.Module):
    def __init__(
        self,
        *,
        layers: Sequence[EncoderLayer],
        d_model: int,
    ) -> None:
        super().__init__()
        self._layers = nn.ModuleList(layers)
        self._norm = nn.LayerNorm(d_model)

    def forward(self, x: list[Tensor]) -> tuple[Tensor, list[list[Tensor | None]]]:
        attentions: list[list[Tensor | None]] = []
        for layer in self._layers:
            x, attention = layer(x)
            attentions.append(attention)
        concatenated = torch.cat(x, dim=1)
        return self._norm(concatenated), attentions


class CardioFormer(nn.Module):
    """
    CardioFormer: Multi-granularity Transformer for ECG Classification

    This is a standalone version adapted from ECG-Research framework.
    Accepts tensor input directly without framework dependencies.

    Args:
        num_classes: Number of output classes
        signal_length: Length of input signal (default 1000)
        input_channels: Number of input channels (12 for standard ECG)
        d_model: Model dimension
        n_heads: Number of attention heads
        e_layers: Number of encoder layers
        d_ff: Feed-forward dimension
        dropout: Dropout rate
        activation: Activation function ("relu" or "gelu")
        patch_len_list: List of patch lengths for multi-granularity
        augmentations: List of augmentation names
        single_channel: Whether to process channels independently
        no_inter_attn: Whether to disable inter-granularity attention
    """

    def __init__(
        self,
        *,
        num_classes: int,
        signal_length: int = 1000,
        input_channels: int = 12,
        d_model: int = 128,
        n_heads: int = 8,
        e_layers: int = 6,
        d_ff: int = 256,
        dropout: float = 0.1,
        activation: str = "gelu",
        patch_len_list: str | Sequence[int] = (8, 16, 32),
        augmentations: str | Sequence[str] = (
            "flip",
            "shuffle",
            "jitter",
            "mask",
            "drop",
        ),
        single_channel: bool = False,
        no_inter_attn: bool = False,
    ) -> None:
        super().__init__()
        if num_classes <= 1:
            raise ValueError("num_classes must be > 1 for multilabel tasks.")
        if signal_length <= 0:
            raise ValueError("signal_length must be positive.")
        if input_channels <= 0:
            raise ValueError("input_channels must be positive.")
        if e_layers <= 0:
            raise ValueError("e_layers must be positive.")
        if d_ff <= 0:
            raise ValueError("d_ff must be positive.")
        if not 0.0 <= dropout < 1.0:
            raise ValueError("dropout must be in [0, 1).")

        patch_lengths = parse_int_list(patch_len_list, name="patch_len_list")
        if any(patch_len > signal_length for patch_len in patch_lengths):
            raise ValueError("patch_len_list values cannot exceed signal_length.")
        augmentation_names = parse_string_list(augmentations, name="augmentations")

        self._num_classes = num_classes
        self._signal_length = signal_length
        self._input_channels = input_channels
        self._single_channel = single_channel

        patch_num_list = [
            int((signal_length - patch_len) / patch_len + 2)
            for patch_len in patch_lengths
        ]
        self._patch_embedding = ListPatchEmbedding(
            input_channels=input_channels,
            d_model=d_model,
            patch_lengths=patch_lengths,
            dropout=dropout,
            augmentations=augmentation_names,
            single_channel=single_channel,
        )
        self._encoder = Encoder(
            layers=[
                EncoderLayer(
                    num_granularity=len(patch_lengths),
                    d_model=d_model,
                    n_heads=n_heads,
                    d_ff=d_ff,
                    dropout=dropout,
                    activation=activation,
                    output_attention=False,
                    no_inter_attn=no_inter_attn,
                )
                for _ in range(e_layers)
            ],
            d_model=d_model,
        )
        projection_features = d_model * sum(patch_num_list)
        if single_channel:
            projection_features *= input_channels
        self._activation = functional.gelu if activation == "gelu" else functional.relu
        self._dropout = nn.Dropout(dropout)
        self._projection = nn.Linear(projection_features, num_classes)

    def forward(self, signal: Tensor) -> Tensor:
        """
        Forward pass

        Args:
            signal: Input ECG signal tensor of shape [B, C, T] or [B, T]
                   where B=batch, C=channels, T=timesteps

        Returns:
            Logits tensor of shape [B, num_classes]
        """
        if signal.dim() == 2:
            signal = signal.unsqueeze(1)
        if signal.dim() != 3:
            raise ValueError("signal must have shape [B, C, T] or [B, T].")

        batch_size, channels, timesteps = signal.shape
        if channels != self._input_channels:
            raise ValueError(
                f"CardioFormer expected input_channels={self._input_channels}, got {channels}."
            )
        if timesteps != self._signal_length:
            raise ValueError(
                f"CardioFormer expected signal_length={self._signal_length}, got {timesteps}."
            )

        encoder_input = signal.transpose(1, 2)
        embedded = self._patch_embedding(encoder_input)
        encoded, _ = self._encoder(embedded)

        if self._single_channel:
            encoded = encoded.reshape(
                batch_size,
                self._input_channels,
                encoded.shape[1],
                encoded.shape[2],
            )

        output = self._activation(encoded)
        output = self._dropout(output)
        output = output.reshape(output.shape[0], -1)
        logits = cast(Tensor, self._projection(output))
        if logits.ndim != 2 or logits.shape[1] != self._num_classes:
            raise ValueError(
                "CardioFormer must produce logits [B, C] with C == num_classes: "
                f"received {tuple(logits.shape)} and num_classes={self._num_classes}."
            )
        return logits


def create_cardioformer_model(
    num_classes: int = 5,
    signal_length: int = 1000,
    input_channels: int = 12,
    checkpoint_path: str | None = None,
    **kwargs
) -> CardioFormer:
    """
    Create a CardioFormer model with optional checkpoint loading

    Args:
        num_classes: Number of output classes
        signal_length: Length of input signal
        input_channels: Number of input channels
        checkpoint_path: Path to checkpoint file (.ckpt or .pt)
        **kwargs: Additional model arguments

    Returns:
        CardioFormer model instance
    """
    # Create model
    model = CardioFormer(
        num_classes=num_classes,
        signal_length=signal_length,
        input_channels=input_channels,
        **kwargs
    )

    # Load checkpoint if provided
    if checkpoint_path:
        checkpoint = torch.load(checkpoint_path, map_location='cpu')

        # Handle different checkpoint formats
        if isinstance(checkpoint, dict):
            if 'model_state' in checkpoint:
                state_dict = checkpoint['model_state']
            elif 'state_dict' in checkpoint:
                state_dict = checkpoint['state_dict']
            else:
                state_dict = checkpoint
        else:
            state_dict = checkpoint

        model.load_state_dict(state_dict, strict=True)
        logger.info("Loaded CardioFormer checkpoint from %s", checkpoint_path)

    return model


# PTB-XL superclass labels
PTBXL_SUPERCLASSES = ["NORM", "MI", "STTC", "CD", "HYP"]
