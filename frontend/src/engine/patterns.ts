// Indonesian PII surface formats, mirroring backend/app/domain/patterns.py.
export const PATTERNS: Record<string, RegExp> = {
  EMAIL: /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g,
  PHONE: /(?:\+62|\b62|\b0)[\s.-]?8\d{1,3}(?:[\s.-]?\d{2,4}){2,3}\b/g,
  SSN: /\b\d{4}[\s.]?\d{4}[\s.]?\d{4}[\s.]?\d{4}\b/g,
};

// Gender is a closed lexical set, so a list beats a model for splitting it out of names.
export const GENDER_WORDS = new Set(["pria", "wanita", "perempuan", "laki-laki", "lakilaki", "male", "female"]);
