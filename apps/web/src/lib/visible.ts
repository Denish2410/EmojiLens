/** Render a string with every invisible or format code point spelled out as <U+XXXX>. */
const INVISIBLE = /[\p{Cf}\p{Cc}\p{Zl}\p{Zp}\u{FE00}-\u{FE0F}\u{E0100}-\u{E01EF}\u{E0000}-\u{E007F}\u{3164}\u{115F}\u{1160}\u{FFA0}]/u;

export function revealInvisible(text: string): string {
  let out = "";
  for (const ch of text) {
    if (ch === "\n") out += "↵\n";
    else if (INVISIBLE.test(ch)) out += `<U+${ch.codePointAt(0)!.toString(16).toUpperCase().padStart(4, "0")}>`;
    else out += ch;
  }
  return out;
}

export function countInvisible(text: string): number {
  let n = 0;
  for (const ch of text) if (ch !== "\n" && INVISIBLE.test(ch)) n++;
  return n;
}
