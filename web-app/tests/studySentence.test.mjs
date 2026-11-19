import test from "node:test";
import assert from "node:assert/strict";
import { sentenceAt, sentenceOffsets } from "../src/utils/studySentence.ts";

test("finds the selected occurrence using Unicode code point offsets", () => {
  const text = "😀 猫です。 猫が好き！ 犬です。";
  const chars = Array.from(text);
  const first = chars.indexOf("猫");
  const second = chars.indexOf("猫", first + 1);
  assert.equal(sentenceAt(text, first, first + 1), "😀 猫です。");
  assert.equal(sentenceAt(text, second, second + 1), "猫が好き！");
  assert.deepEqual(sentenceOffsets(text, "猫が好き！", second, second + 1), { start: second, end: second + 5 });
  assert.equal(sentenceOffsets(text, "猫です。", second, second + 1), null);
});

test("allows an edited exact substring containing the target and rejects unrelated or invented text", () => {
  const text = "  今日は猫が好きです。犬も好きです。";
  const target = Array.from(text).indexOf("猫");
  assert.deepEqual(sentenceOffsets(text, " 猫が好きです。 ", target, target + 1), { start: target, end: target + 7 });
  assert.equal(sentenceOffsets(text, "犬も好きです。", target, target + 1), null);
  assert.equal(sentenceOffsets(text, "猫が嫌いです。", target, target + 1), null);
});

test("returns untimed unpunctuated transcript as editable context", () => {
  const text = "これは猫の話です そして犬の話です";
  const target = Array.from(text).indexOf("猫");
  assert.equal(sentenceAt(text, target, target + 1), text);
  assert.deepEqual(sentenceOffsets(text, "これは猫の話です", target, target + 1), { start: 0, end: 8 });
});
