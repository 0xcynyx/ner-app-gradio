// Minimal WordPiece tokenizer, so the bundle needs no transformers.js just for tokenization.

export interface Word {
  start: number;
  end: number;
  text: string;
}

export interface Encoded {
  ids: number[];
  owners: (Word | null)[];
}

// Words own the character offsets, punctuation splits off as its own token like BERT does.
const WORD = /[\p{L}\p{N}]+(?:[.@+_'-][\p{L}\p{N}]+)*|[^\s\p{L}\p{N}]/gu;

export class WordPiece {
  private vocab: Map<string, number>;
  private unk: number;
  private cls: number;
  private sep: number;
  private lowercase: boolean;

  constructor(vocabText: string, lowercase = true) {
    this.vocab = new Map();
    vocabText.split("\n").forEach((token, index) => {
      const clean = token.replace(/\r$/, "");
      if (clean.length) this.vocab.set(clean, index);
    });
    this.unk = this.vocab.get("[UNK]") ?? 1;
    this.cls = this.vocab.get("[CLS]") ?? 2;
    this.sep = this.vocab.get("[SEP]") ?? 3;
    this.lowercase = lowercase;
  }

  static async load(repo: string, lowercase = true): Promise<WordPiece> {
    const response = await fetch(`https://huggingface.co/${repo}/resolve/main/vocab.txt`);
    if (!response.ok) throw new Error(`vocab download failed: ${response.status}`);
    return new WordPiece(await response.text(), lowercase);
  }

  private normalise(value: string): string {
    const lowered = this.lowercase ? value.toLowerCase() : value;
    // Uncased BERT strips accents, and NFD plus mark removal is how that is done.
    return lowered.normalize("NFD").replace(/\p{Mn}/gu, "");
  }

  // Greedy longest match first, the standard WordPiece rule.
  private pieces(word: string): number[] {
    const normalised = this.normalise(word);
    if (!normalised) return [];
    const out: number[] = [];
    let start = 0;
    while (start < normalised.length) {
      let end = normalised.length;
      let found = -1;
      while (start < end) {
        const candidate = start === 0 ? normalised.slice(start, end) : `##${normalised.slice(start, end)}`;
        const id = this.vocab.get(candidate);
        if (id !== undefined) {
          found = id;
          break;
        }
        end -= 1;
      }
      if (found < 0) return [this.unk];
      out.push(found);
      start = end;
    }
    return out;
  }

  encode(text: string): Encoded {
    const words: Word[] = Array.from(text.matchAll(WORD)).map((match) => ({
      start: match.index ?? 0,
      end: (match.index ?? 0) + match[0].length,
      text: match[0],
    }));
    const ids: number[] = [this.cls];
    const owners: (Word | null)[] = [null];
    for (const word of words) {
      for (const id of this.pieces(word.text)) {
        ids.push(id);
        owners.push(word);
      }
    }
    ids.push(this.sep);
    owners.push(null);
    return { ids, owners };
  }
}
