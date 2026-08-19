# Compression pipeline

Shrinking the 2.2 GB XLM-R large checkpoint so it can run on free hosting. Stage 0 is
lossless in intent and needs no training. Stage 1, distillation to a browser sized student,
builds on the artifacts produced here.

## Why the checkpoint is so large

XLM-R large carries a 250,002 piece vocabulary covering 100 languages. At a hidden size of
1024 that embedding table alone is 256M of the 559M parameters, about 46 percent of the model.
Indonesian is Latin script, so most of that table is dead weight.

## Stage 0

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 1. Prune the vocabulary to Latin script pieces and slice the embedding rows to match.
.venv/bin/python trim_vocab.py \
  --model 0xcynyx/ner-roberta-large-bahasa-indonesia-finetuned \
  --out artifacts/trimmed --mode latin

# 2. Export ONNX and quantize the weights to INT8.
.venv/bin/python export_onnx.py --model artifacts/trimmed --out artifacts --arch arm64

# 3. Build a labelled test set and compare every variant to the original.
.venv/bin/python make_testset.py --out artifacts/testset.jsonl --count 300
.venv/bin/python evaluate.py \
  --testset artifacts/testset.jsonl \
  --baseline 0xcynyx/ner-roberta-large-bahasa-indonesia-finetuned \
  --variant "trimmed fp32=torch=artifacts/trimmed" \
  --variant "trimmed onnx int8=onnx-int8=artifacts/onnx-int8"
```

Use `--mode corpus --corpus your_text.txt` for a more aggressive trim driven by which pieces a
real Indonesian corpus actually emits. Latin mode is the safe default because dropping a piece
that Indonesian never contains cannot change how Indonesian text is segmented.

## How the numbers are read

`trim_vocab.py` refuses to finish unless the pruned tokenizer maps probe sentences to the same
embedding rows as the original, so a passing run means tokenization is unchanged rather than
merely similar.

`evaluate.py` reports two different things:

- **F1, precision, recall** against the synthetic gold set, which answers whether the task
  still works. The set is template generated, so absolute values measure pattern coverage and
  not natural text difficulty. Treat them as a floor.
- **agree and exact** against the original model, which answers whether compression changed
  behaviour. Span agreement is the F1 of a variant scored with the original as reference, and
  exact is the share of documents where every span matched. These are the numbers that decide
  whether a variant is safe to ship.

## Where quantization loss comes from

Dynamic INT8 keeps activations in float and rounds weights per output channel, which token
classification tolerates well. Any accuracy drop shows up first as boundary jitter on long
spans, so watch `exact` more closely than `F1`.

## Measured results

Run on an M series Mac, 300 template sentences, post processing set to `production` so the
numbers reflect what the API actually returns rather than raw model output.

| Variant | Vocab | Params | Size | F1 | ms/doc | Agreement | Exact |
|---|---|---|---|---|---|---|---|
| original fp32 | 250,002 | 558.9M | 2,235 MB | 0.9098 | 49.0 | baseline | baseline |
| Latin trim | 113,048 | 418.6M | 1,674 MB | not run | | | |
| Indonesian trim fp32 | 30,549 | 334.1M | 1,337 MB | 0.9098 | 48.0 | 1.0000 | 100.00% |
| Indonesian trim ONNX fp32 | 30,549 | 334.1M | 1,337 MB | not run | | | |
| **Indonesian trim ONNX INT8** | 30,549 | 334.1M | **337 MB** | 0.8883 | **18.6** | 0.9612 | 86.33% |

Reading these:

- The vocabulary trim is free. Identical F1, perfect span agreement, every document matching,
  for 40 percent fewer parameters. Ship it unconditionally.
- INT8 costs 2.15 F1 points and gives 6.6 times smaller plus 2.6 times faster. Agreement of
  0.9612 with 86 percent of documents identical means the differences are boundary jitter on a
  minority of spans, not category errors.
- Latency was verified with `CPUExecutionProvider` pinned. An earlier measurement silently ran
  ONNX on `mps:0`, which made the comparison meaningless.

## A finding worth keeping

The checkpoint emits `B-` on every subword piece and never `I-`, so raw output fragments:
`Dewi Lestari` arrives as three spans, `budi@contoh.co.id` as nine. Any evaluation that skips
the aggregation layer scores this model at roughly 0.10 F1 rather than 0.91, and the first
version of this harness made exactly that mistake. It also proved that same type spans touching
with no separator must merge unconditionally, which the backend aggregator now does.
