"""ONNX export plus dynamic INT8 quantization for a token classification checkpoint.

Dynamic quantization is the right choice here because it needs no calibration data and token
classification weights tolerate it well. Weights become INT8 while activations stay float,
which cuts size close to fourfold and speeds up CPU matmuls.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import onnx
from optimum.onnxruntime import ORTModelForTokenClassification, ORTQuantizer
from optimum.onnxruntime.configuration import AutoQuantizationConfig
from transformers import AutoTokenizer


def fold_identity(path: Path) -> int:
    """Collapse Identity aliases so shared weights are one initializer, not one per reuse.

    ALBERT reuses a single layer twelve times and the exporter represents each reuse as an
    Identity node over the same weight. The quantizer then quantizes the first use and leaves
    the float original alive for the aliases, which doubles the file.
    """
    model = onnx.load(str(path))
    graph = model.graph
    initializers = {init.name for init in graph.initializer}
    rename: dict = {}
    for node in list(graph.node):
        if node.op_type == "Identity" and node.input[0] in initializers:
            rename[node.output[0]] = node.input[0]
            graph.node.remove(node)
    if not rename:
        return 0
    # Resolve chains so an alias of an alias still lands on the real initializer.
    for key in list(rename):
        seen = rename[key]
        while seen in rename:
            seen = rename[seen]
        rename[key] = seen
    for node in graph.node:
        for index, name in enumerate(node.input):
            if name in rename:
                node.input[index] = rename[name]
    onnx.save(model, str(path))
    return len(rename)


def collect_used(graph, used: set) -> None:
    """Walk nodes and any subgraphs so nothing still in use is treated as dead."""
    for node in graph.node:
        used.update(node.input)
        for attribute in node.attribute:
            if attribute.g.ByteSize():
                collect_used(attribute.g, used)
            for sub in attribute.graphs:
                collect_used(sub, used)


def strip_unused_initializers(path: Path) -> int:
    """Quantization leaves the original float weights behind, unreferenced but still on disk."""
    model = onnx.load(str(path))
    used: set = set()
    collect_used(model.graph, used)
    used.update(output.name for output in model.graph.output)
    keep = [init for init in model.graph.initializer if init.name in used]
    removed = len(model.graph.initializer) - len(keep)
    if removed:
        del model.graph.initializer[:]
        model.graph.initializer.extend(keep)
        onnx.save(model, str(path))
    return removed


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
    folded = fold_identity(fp32_dir / "model.onnx")
    print(f"onnx fp32: {directory_size(fp32_dir):.0f} MB, folded {folded} shared weight aliases")

    # Per channel weights keep more accuracy at the same size.
    config = getattr(AutoQuantizationConfig, args.arch)(is_static=False, per_channel=True)
    quantizer = ORTQuantizer.from_pretrained(fp32_dir)
    quantizer.quantize(save_dir=int8_dir, quantization_config=config)
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json"):
        source = fp32_dir / name
        if source.exists():
            shutil.copy(source, int8_dir / name)
    quantized = int8_dir / "model_quantized.onnx"
    removed = strip_unused_initializers(quantized)
    print(f"pruned {removed} dead float initializers left by the quantizer")
    print(f"onnx int8: {directory_size(int8_dir):.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
