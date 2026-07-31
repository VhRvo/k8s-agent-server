import test from "node:test";
import assert from "node:assert/strict";

import {
  CONCISE_PROMPT_MARKER,
  CONCISE_PROMPT_SUFFIX,
  MAX_AGENT_PROMPT_LENGTH,
  buildOutgoingPrompt,
  normalizeConversationMessages,
  visibleConversationTitle,
  visibleMessageLimit,
  visibleUserMessage,
} from "../src/utils/messages.js";

test("concise mode appends its instruction exactly once", () => {
  const outgoing = buildOutgoingPrompt("检查异常 Pod", true);

  assert.equal(outgoing, `检查异常 Pod${CONCISE_PROMPT_SUFFIX}`);
  assert.equal(buildOutgoingPrompt(outgoing, true), outgoing);
});

test("normal mode leaves the prompt unchanged", () => {
  assert.equal(buildOutgoingPrompt("检查异常 Pod", false), "检查异常 Pod");
});

test("a marker typed by the user is not mistaken for the hidden instruction", () => {
  const message = `解释这段文字：${CONCISE_PROMPT_MARKER}不是隐藏指令`;
  const outgoing = buildOutgoingPrompt(message, true);

  assert.equal(visibleUserMessage(outgoing), message);
  assert.equal(outgoing, `${message}${CONCISE_PROMPT_SUFFIX}`);
});

test("visible content hides the concise instruction", () => {
  const outgoing = buildOutgoingPrompt("检查异常 Pod", true);

  assert.equal(visibleUserMessage(outgoing), "检查异常 Pod");
  assert.equal(
    visibleConversationTitle("检查异常 Pod  [简洁模式] 请只输出"),
    "检查异常 Pod"
  );
});

test("visible content also hides instructions saved by an older version", () => {
  const legacyMessage =
    `检查异常 Pod${CONCISE_PROMPT_MARKER}请保持简洁，只输出必要信息。`;

  assert.equal(visibleUserMessage(legacyMessage), "检查异常 Pod");
});

test("truncated conversation titles do not expose the concise marker", () => {
  for (let length = 1; length <= 30; length += 1) {
    const message = "a".repeat(length);
    const storedTitle = buildOutgoingPrompt(message, true)
      .trim()
      .replaceAll("\n", " ")
      .slice(0, 30);

    assert.equal(visibleConversationTitle(storedTitle), message);
  }
});

test("concise input limit keeps the final prompt within the API limit", () => {
  const limit = visibleMessageLimit(true);
  const outgoing = buildOutgoingPrompt("a".repeat(limit), true);

  assert.equal(outgoing.length, MAX_AGENT_PROMPT_LENGTH);
  assert.equal(visibleMessageLimit(false), MAX_AGENT_PROMPT_LENGTH);
});

test("history keeps only the full final assistant reply for a concise turn", () => {
  const messages = normalizeConversationMessages([
    { role: "user", content: "普通问题" },
    { role: "assistant", content: "普".repeat(400) },
    {
      role: "user",
      content: buildOutgoingPrompt("简洁问题", true),
    },
    { role: "assistant", content: "正在协调成员" },
    { role: "assistant", content: "结".repeat(500) },
    { role: "user", content: "下一个普通问题" },
    { role: "assistant", content: "普通回答" },
  ]);

  assert.equal(messages.length, 6);
  assert.equal(messages[1].content.length, 400);
  assert.equal(messages[2].content, "简洁问题");
  assert.equal(messages[3].conciseMode, true);
  assert.equal(messages[3].content.length, 500);
  assert.equal(messages[3].content.includes("正在协调成员"), false);
  assert.equal(messages[5].content, "普通回答");
});
