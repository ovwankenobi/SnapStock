import en from "./en.json";
import tl from "./tl.json";

const DICTIONARIES = { en, tl };

export const SUPPORTED_LANGUAGES = Object.keys(DICTIONARIES);

function lookup(dict, key) {
  return key
    .split(".")
    .reduce((acc, part) => (acc && acc[part] !== undefined ? acc[part] : undefined), dict);
}

export function translate(language, key) {
  const value = lookup(DICTIONARIES[language], key);
  if (value !== undefined) return value;
  const fallback = lookup(DICTIONARIES.en, key);
  return fallback !== undefined ? fallback : key;
}
