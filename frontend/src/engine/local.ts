// Browser inference: transformers.js supplies the tokenizer, ONNX Runtime Web runs the graph.
import { specFor } from "./labels";
import { assemble } from "./postprocess";
import type { Analysis, Entity } from "./types";
import { WordPiece } from "./wordpiece";

const REPO = import.meta.env.VITE_MODEL_REPO ?? "0xcynyx/ner-pii-indonesian-mini";
const HUB = "https://huggingface.co";
const ORT_VERSION = "1.22.0";

const ORT_CDN = `https://cdn.jsdelivr.net/npm/onnxruntime-web@${ORT_VERSION}/dist/`;

// Loading the runtime from a CDN keeps 44 MB of WASM out of the deployed bundle.
let runtime: Promise<any> | null = null;

function loadRuntime(): Promise<any> {
  if (!runtime) {
    runtime = import(/* @vite-ignore */ `${ORT_CDN}ort.min.mjs`).then((module) => {
      const ort = module.default ?? module;
      ort.env.wasm.wasmPaths = ORT_CDN;
      return ort;
    });
  }
  return runtime;
}

interface Loaded {
  tokenizer: WordPiece;
  session: any;
  id2label: Record<string, string>;
  ort: any;
}

let loading: Promise<Loaded> | null = null;

export function modelRepo(): string {
  return REPO;
}

export function loadEngine(onProgress?: (message: string) => void): Promise<Loaded> {
  if (loading) return loading;
  loading = (async () => {
    onProgress?.("Starting runtime");
    const ort = await loadRuntime();
    onProgress?.("Loading tokenizer");
    const tokenizer = await WordPiece.load(REPO);
    onProgress?.("Downloading model, about 12 MB");
    const response = await fetch(`${HUB}/${REPO}/resolve/main/onnx/model_quantized.onnx`);
    if (!response.ok) throw new Error(`model download failed: ${response.status}`);
    const bytes = new Uint8Array(await response.arrayBuffer());
    onProgress?.("Preparing session");
    const session = await ort.InferenceSession.create(bytes, { executionProviders: ["wasm"] });
    const config = await (await fetch(`${HUB}/${REPO}/resolve/main/config.json`)).json();
    onProgress?.(null as unknown as string);
    return { tokenizer, session, id2label: config.id2label, ort };
  })();
  return loading;
}

function tensor(ort: any, values: number[], fill?: number) {
  const data = BigInt64Array.from(values.map((value) => BigInt(fill ?? value)));
  return new ort.Tensor("int64", data, [1, values.length]);
}

export async function analyzeLocal(text: string, minScore: number): Promise<Analysis> {
  const loaded = await loadEngine();
  const clipped = text.slice(0, 20000);
  if (!clipped.trim()) return assemble(clipped, [], minScore, 0);

  const { ids, owners } = loaded.tokenizer.encode(clipped);
  const output = await loaded.session.run({
    input_ids: tensor(loaded.ort, ids),
    attention_mask: tensor(loaded.ort, ids, 1),
    token_type_ids: tensor(loaded.ort, ids, 0),
  });
  const logits = output.logits;
  const classes = logits.dims[2];
  const values = logits.data as Float32Array;

  // Word level BIO decoding, which is where entity boundaries actually sit.
  const spans: Entity[] = [];
  let current: Entity | null = null;
  for (let position = 0; position < ids.length; position += 1) {
    const owner = owners[position];
    if (!owner) continue;
    let best = 0;
    let sum = 0;
    for (let index = 0; index < classes; index += 1) {
      const value = values[position * classes + index];
      sum += Math.exp(value);
      if (value > values[position * classes + best]) best = index;
    }
    const score = Math.exp(values[position * classes + best]) / (sum || 1);
    const name = loaded.id2label[String(best)] ?? "O";
    if (name === "O") {
      if (current) spans.push(current);
      current = null;
      continue;
    }
    const [prefix, code] = name.split("-");
    if (prefix === "B" || !current || current.label !== code) {
      if (current) spans.push(current);
      current = {
        start: owner.start, end: owner.end, label: code, text: owner.text,
        score, verified: false, sensitivity: specFor(code).sensitivity,
      };
    } else {
      current.end = owner.end;
      current.text = clipped.slice(current.start, current.end);
      current.score = Math.min(current.score, score);
    }
  }
  if (current) spans.push(current);
  return assemble(clipped, spans, minScore, 1);
}
