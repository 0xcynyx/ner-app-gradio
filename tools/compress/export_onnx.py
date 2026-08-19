"""ONNX export plus dynamic INT8 quantization for a token classification checkpoint.

Dynamic quantization is the right choice here because it needs no calibration data and token
classification weights tolerate it well. Weights become INT8 while activations stay float,
which cuts size close to fourfold and speeds up CPU matmuls.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from optimum.onnxruntime import ORTModelForTokenClassification, ORTQuantizer
from optimum.onnxruntime.configuration import AutoQuantizationConfig
from transformers import AutoTokenizer


def directory_size(path: Path) -> float:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1e6


def main() -> int:
    parser = argparse.ArgumentParser(description="Export ONNX and quantize to INT8")
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--arch", choices=("arm64", "avx512_vnni", "avx2"), default="arm64")
    args = parser.parse_args()

    out = Path(args.out)
    fp32_dir = out / "onnx-fp32"
    int8_dir = out / "onnx-int8"

    model = ORTModelForTokenClassification.from_pretrained(args.model, export=True)
    model.save_pretrained(fp32_dir)
    AutoTokenizer.from_pretrained(args.model).save_pretrained(fp32_dir)
    print(f"onnx fp32: {directory_size(fp32_dir):.0f} MB")

    # Per channel weights keep more accuracy at the same size.
    config = getattr(AutoQuantizationConfig, args.arch)(is_static=False, per_channel=True)
    quantizer = ORTQuantizer.from_pretrained(fp32_dir)
    quantizer.quantize(save_dir=int8_dir, quantization_config=config)
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"):
        source = fp32_dir / name
        if source.exists():
            shutil.copy(source, int8_dir / name)
    print(f"onnx int8: {directory_size(int8_dir):.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
