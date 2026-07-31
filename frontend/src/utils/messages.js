export const MAX_AGENT_PROMPT_LENGTH = 4000;

export const CONCISE_PROMPT_MARKER = "\n\n[简洁模式]\n";

const CONCISE_PROMPT_INSTRUCTION =
  "只输出最终答复，不输出协调、思考、工具调用过程、工具结果或原始日志；优先给出关键结论、最高风险和下一步，尽量控制在 300 字内、最多 5 点，必要时可适当展开。";

export const CONCISE_PROMPT_SUFFIX =
  `${CONCISE_PROMPT_MARKER}${CONCISE_PROMPT_INSTRUCTION}`;

const LEGACY_CONCISE_INSTRUCTIONS = [
  "仅针对本次回答：请只输出结论、关键证据和必要步骤，省略背景、复述和重复说明；除非安全性需要或我明确要求展开，否则控制在 300 字以内、最多 5 点。",
  "请保持简洁，只输出必要信息。",
];

function concisePromptOffset(message) {
  const content = String(message ?? "");
  const markerOffset = content.lastIndexOf(CONCISE_PROMPT_MARKER);
  if (markerOffset < 0) return -1;

  const instruction = content
    .slice(markerOffset + CONCISE_PROMPT_MARKER.length)
    .trim();
  return instruction === CONCISE_PROMPT_INSTRUCTION ||
    LEGACY_CONCISE_INSTRUCTIONS.includes(instruction)
    ? markerOffset
    : -1;
}

export function hasConcisePrompt(message) {
  return concisePromptOffset(message) >= 0;
}

export function buildOutgoingPrompt(message, conciseMode) {
  const content = String(message ?? "");
  if (!conciseMode || hasConcisePrompt(content)) return content;
  return `${content}${CONCISE_PROMPT_SUFFIX}`;
}

export function visibleUserMessage(message) {
  const content = String(message ?? "");
  const markerOffset = concisePromptOffset(content);
  return markerOffset >= 0 ? content.slice(0, markerOffset) : content;
}

export function normalizeConversationMessages(messages) {
  const source = Array.isArray(messages) ? messages : [];
  const normalized = [];

  for (let index = 0; index < source.length; index += 1) {
    const message = source[index] || {};
    if (message.role !== "user") {
      normalized.push({
        ...message,
        role: "assistant",
        content: String(message.content || ""),
        conciseMode: false,
      });
      continue;
    }

    const conciseMode = hasConcisePrompt(message.content);
    normalized.push({
      ...message,
      role: "user",
      content: visibleUserMessage(message.content),
      conciseMode,
    });

    if (!conciseMode) continue;

    let nextUserIndex = index + 1;
    let finalAssistant = null;
    while (
      nextUserIndex < source.length &&
      source[nextUserIndex]?.role !== "user"
    ) {
      if (String(source[nextUserIndex]?.content || "").trim()) {
        finalAssistant = source[nextUserIndex];
      }
      nextUserIndex += 1;
    }

    if (finalAssistant) {
      normalized.push({
        ...finalAssistant,
        role: "assistant",
        content: String(finalAssistant.content || ""),
        conciseMode: true,
      });
    }
    index = nextUserIndex - 1;
  }

  return normalized;
}

export function visibleConversationTitle(title) {
  const content = String(title || "新对话");
  const marker = "[简洁模式]";
  const markerOffset = content.lastIndexOf("  [");
  if (markerOffset >= 0) {
    const candidate = content.slice(markerOffset + 2);
    if (marker.startsWith(candidate) || candidate.startsWith(marker)) {
      return content.slice(0, markerOffset).trim() || "新对话";
    }
  }
  return content.trim() || "新对话";
}

export function visibleMessageLimit(conciseMode) {
  return (
    MAX_AGENT_PROMPT_LENGTH -
    (conciseMode ? CONCISE_PROMPT_SUFFIX.length : 0)
  );
}
