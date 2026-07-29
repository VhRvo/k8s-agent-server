import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  reactive,
  ref,
  watch,
} from "vue";

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "/backend"
).replace(/\/$/, "");

  const RESPONSE_COLLAPSE_THRESHOLD = 520;
  const RESPONSE_SUMMARY_LENGTH = 220;
  const STREAM_IDLE_RELEASE_MS = 350;

  const FALLBACK_AGENTS = [
    {
      id: "team",
      name: "总协调员",
      english_name: "K8sOps Team",
      description: "拆解任务、协调专家并汇总最终结论",
      permission: "团队协调",
      icon: "Users",
      available: true,
    },
    {
      id: "investigator",
      name: "侦察员",
      english_name: "Investigator",
      description: "只读采集 Pod、节点、事件、日志和资源数据",
      permission: "只读",
      icon: "Search",
      available: true,
    },
    {
      id: "analyst",
      name: "分析师",
      english_name: "Analyst",
      description: "根据集群证据定位根因并评估影响",
      permission: "分析",
      icon: "Activity",
      available: true,
    },
    {
      id: "operator",
      name: "操作员",
      english_name: "Operator",
      description: "生成变更、验证和回滚方案，不直接执行",
      permission: "方案模式",
      icon: "Wrench",
      available: false,
      availability_note:
        "后续版本将提供变更方案编排、人工审批、执行验证和回滚能力。",
    },
  ];

  const AGENT_SUGGESTIONS = {
    team: [
      {
        label: "HEALTH",
        title: "检查集群健康",
        detail: "协调专家完成一次综合诊断",
        prompt: "检查集群整体健康状况，并列出需要优先处理的问题。",
      },
      {
        label: "INCIDENT",
        title: "调查异常工作负载",
        detail: "采集事实、分析根因并汇总结论",
        prompt: "查找当前异常的工作负载，组织专家分析原因并给出处理建议。",
      },
      {
        label: "CAPACITY",
        title: "评估资源压力",
        detail: "检查节点与工作负载资源情况",
        prompt: "检查节点和工作负载的资源压力，找出需要扩容或优化的对象。",
      },
    ],
    investigator: [
      {
        label: "PODS",
        title: "采集异常 Pod",
        detail: "列出状态、重启次数和所属节点",
        prompt: "只读查询所有异常 Pod，汇报关键状态和关联资源。",
      },
      {
        label: "EVENTS",
        title: "查看近期事件",
        detail: "收集 Warning 事件与发生频率",
        prompt: "收集集群近期 Warning 事件，按命名空间和资源整理。",
      },
      {
        label: "USAGE",
        title: "采集资源使用",
        detail: "获取节点与 Pod 的 CPU、内存数据",
        prompt: "只读采集节点和 Pod 的资源使用情况，突出异常值。",
      },
    ],
    analyst: [
      {
        label: "ROOT CAUSE",
        title: "定位根因",
        detail: "基于共享证据形成因果判断",
        prompt: "根据共享上下文定位最可能的根因，并说明判断依据。",
      },
      {
        label: "IMPACT",
        title: "评估影响",
        detail: "梳理服务范围、严重度与风险",
        prompt: "根据现有证据评估影响范围、严重程度和继续恶化的风险。",
      },
      {
        label: "GAPS",
        title: "检查证据缺口",
        detail: "指出形成结论前还缺少的信息",
        prompt: "审查共享上下文，指出诊断结论还缺少哪些关键证据。",
      },
    ],
    operator: [
      {
        label: "PLAN",
        title: "生成修复方案",
        detail: "列出目标、步骤、影响和验证方式",
        prompt: "根据共享上下文生成保守的修复方案，不执行任何变更。",
      },
      {
        label: "ROLLOUT",
        title: "规划发布操作",
        detail: "包含前置检查和发布后验证",
        prompt: "生成安全的工作负载发布方案，包含前置检查、执行步骤和验证。",
      },
      {
        label: "ROLLBACK",
        title: "准备回滚方案",
        detail: "明确触发条件与恢复步骤",
        prompt: "根据共享上下文准备回滚方案，列出触发条件、步骤和验证方法。",
      },
    ],
  };

  const AGENT_HEADLINES = {
    team: "让团队协同处理运维问题",
    investigator: "需要采集哪些集群事实？",
    analyst: "需要分析哪些证据？",
    operator: "需要制定什么操作方案？",
  };

  const AGENT_BADGES = {
    team: "协",
    investigator: "侦",
    analyst: "析",
    operator: "策",
  };

  function createSessionId() {
    return globalThis.crypto?.randomUUID?.() || `session-${Date.now()}`;
  }

  function createThread(workspaceId, agentId) {
    return {
      sessionId: agentId === "team" ? workspaceId : `${workspaceId}-${agentId}`,
      messages: [],
      draft: "",
      isStreaming: false,
      requestActive: false,
      queuedRequest: null,
      hasUnread: false,
    };
  }

  function createThreads(workspaceId) {
    return Object.fromEntries(
      FALLBACK_AGENTS.map((agent) => [
        agent.id,
        createThread(workspaceId, agent.id),
      ])
    );
  }

  function escapeHtml(value) {
    const entities = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return String(value ?? "").replace(/[&<>"']/g, (char) => entities[char]);
  }

  function renderInlineMarkdown(value) {
    return value
      .replace(/`([^`\n]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  }

  function renderMarkdown(value) {
    const codeBlocks = [];
    let safe = escapeHtml(value);

    safe = safe.replace(/```[^\n]*\n?([\s\S]*?)```/g, (_, code) => {
      const token = `@@CODE_BLOCK_${codeBlocks.length}@@`;
      codeBlocks.push(`<pre><code>${code.replace(/\n$/, "")}</code></pre>`);
      return token;
    });

    const lines = safe.split("\n");
    const output = [];
    let listType = null;

    const closeList = () => {
      if (listType) {
        output.push(`</${listType}>`);
        listType = null;
      }
    };

    for (const line of lines) {
      const unordered = line.match(/^\s*[-*]\s+(.+)$/);
      const ordered = line.match(/^\s*\d+\.\s+(.+)$/);

      if (unordered || ordered) {
        const nextListType = unordered ? "ul" : "ol";
        if (listType !== nextListType) {
          closeList();
          listType = nextListType;
          output.push(`<${listType}>`);
        }
        output.push(`<li>${renderInlineMarkdown((unordered || ordered)[1])}</li>`);
        continue;
      }

      closeList();
      if (!line.trim()) {
        output.push("");
      } else if (line.startsWith("### ")) {
        output.push(`<h4>${renderInlineMarkdown(line.slice(4))}</h4>`);
      } else if (line.startsWith("## ")) {
        output.push(`<h3>${renderInlineMarkdown(line.slice(3))}</h3>`);
      } else if (line.startsWith("# ")) {
        output.push(`<h2>${renderInlineMarkdown(line.slice(2))}</h2>`);
      } else if (line.startsWith("&gt; ")) {
        output.push(`<blockquote>${renderInlineMarkdown(line.slice(5))}</blockquote>`);
      } else if (/^@@CODE_BLOCK_\d+@@$/.test(line)) {
        output.push(line);
      } else {
        output.push(`<p>${renderInlineMarkdown(line)}</p>`);
      }
    }
    closeList();

    let html = output.join("");
    codeBlocks.forEach((block, index) => {
      html = html.replace(`@@CODE_BLOCK_${index}@@`, block);
    });
    return html;
  }

  function responseSummary(value) {
    const content = String(value || "");
    const namedSection = content.match(
      /(?:^|\n)#{1,6}\s*(?:总结|摘要|结论|总体结论|执行摘要)\s*\n([\s\S]*?)(?=\n#{1,6}\s|\s*$)/i
    );
    const text = String(namedSection?.[1] || content)
      .replace(/```[\s\S]*?```/g, " ")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/!\[[^\]]*\]\([^)]+\)/g, " ")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/^#{1,6}\s+/gm, "")
      .replace(/^\s*(?:[-*+]|\d+[.)])\s+/gm, "")
      .replace(/[*_>#|]/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    if (text.length <= RESPONSE_SUMMARY_LENGTH) return text;

    const excerpt = text.slice(0, RESPONSE_SUMMARY_LENGTH);
    const sentenceEnd = Math.max(
      excerpt.lastIndexOf("。"),
      excerpt.lastIndexOf("！"),
      excerpt.lastIndexOf("？"),
      excerpt.lastIndexOf("；"),
      excerpt.lastIndexOf("."),
      excerpt.lastIndexOf("!"),
      excerpt.lastIndexOf("?")
    );
    const end = sentenceEnd >= 120 ? sentenceEnd + 1 : excerpt.length;
    return `${excerpt.slice(0, end).trim()}...`;
  }

  function shouldCollapseResponse(message) {
    return Boolean(
      message?.role === "assistant" &&
      !message.pending &&
      !message.error &&
      !message.stopped &&
      String(message.content || "").length > RESPONSE_COLLAPSE_THRESHOLD
    );
  }

  async function readError(response) {
    try {
      const data = await response.json();
      return data.detail || data.error || `请求失败 (${response.status})`;
    } catch {
      return `请求失败 (${response.status})`;
    }
  }

  export function useOperationsConsole() {
      const initialWorkspaceId = createSessionId();
      const activeView = ref("chat");
      const activeAgentId = ref("team");
      const hoveredAgentId = ref("");
      const agents = ref(FALLBACK_AGENTS);
      const workspaceId = ref(initialWorkspaceId);
      const threads = reactive(createThreads(initialWorkspaceId));
      const sharedContext = ref([]);
      const contextOpen = ref(false);
      const sidebarOpen = ref(false);
      const serviceStatus = ref("checking");
      const currentTitle = ref("新对话");
      const conversations = ref([]);
      const conversationQuery = ref("");
      const loadingConversations = ref(false);
      const loadingConversation = ref(false);
      const inspections = ref([]);
      const loadingInspections = ref(false);
      const startingInspection = ref(false);
      const expandedInspectionId = ref("");
      const messagesPanel = ref(null);
      const messageInput = ref(null);
      const toast = reactive({ message: "", type: "error" });

      let healthTimer = null;
      let inspectionTimer = null;
      let toastTimer = null;
      let isDisposed = false;
      const streamControllers = new Map();

      const activeAgent = computed(
        () =>
          agents.value.find((agent) => agent.id === activeAgentId.value) ||
          FALLBACK_AGENTS[0]
      );
      const activeThread = computed(() => threads[activeAgentId.value]);
      const messages = computed(() => activeThread.value?.messages || []);
      const draft = computed({
        get: () => activeThread.value?.draft || "",
        set: (value) => {
          if (activeThread.value) activeThread.value.draft = value;
        },
      });
      const currentSessionId = computed(
        () => threads.team?.sessionId || workspaceId.value
      );
      const isStreaming = computed(
        () => Boolean(activeThread.value?.isStreaming)
      );
      const isAnyStreaming = computed(
        () =>
          Object.values(threads).some(
            (thread) =>
              thread.isStreaming ||
              thread.requestActive ||
              Boolean(thread.queuedRequest)
          )
      );
      const activeSuggestions = computed(
        () => AGENT_SUGGESTIONS[activeAgentId.value] || AGENT_SUGGESTIONS.team
      );
      const activeAgentHeadline = computed(
        () => AGENT_HEADLINES[activeAgentId.value] || AGENT_HEADLINES.team
      );
      const unavailableAgentHint = computed(() => {
        const agent = agentById(hoveredAgentId.value);
        return isAgentAvailable(agent) ? null : agent;
      });
      const composerPlaceholder = computed(
        () => `向${activeAgent.value.name}提问...`
      );

      const filteredConversations = computed(() => {
        const query = conversationQuery.value.toLowerCase();
        return conversations.value.filter((item) => {
          if (String(item.id || "").startsWith("agent-")) return false;
          return (
            !query ||
            String(item.title || "").toLowerCase().includes(query)
          );
        });
      });
      const conversationCount = computed(
        () =>
          conversations.value.filter(
            (item) => !String(item.id || "").startsWith("agent-")
          ).length
      );

      const pageTitle = computed(() =>
        activeView.value === "chat" ? currentTitle.value : "集群巡检"
      );

      const canSend = computed(
        () =>
          Boolean(draft.value.trim()) &&
          !isStreaming.value &&
          isAgentAvailable(activeAgent.value)
      );

      const inspectionStats = computed(() => ({
        total: inspections.value.length,
        completed: inspections.value.filter((item) => item.status === "completed").length,
        failed: inspections.value.filter((item) => item.status === "failed").length,
        running: inspections.value.filter((item) => item.status === "running").length,
      }));

      const runningInspectionCount = computed(() => inspectionStats.value.running);

      const serviceStatusText = computed(() => {
        if (serviceStatus.value === "online") return "服务正常";
        if (serviceStatus.value === "offline") return "服务异常";
        return "检测中";
      });

      function agentById(agentId) {
        return (
          agents.value.find((agent) => agent.id === agentId) ||
          FALLBACK_AGENTS.find((agent) => agent.id === agentId) ||
          FALLBACK_AGENTS[0]
        );
      }

      function isAgentAvailable(agentOrId) {
        const agent =
          typeof agentOrId === "string" ? agentById(agentOrId) : agentOrId;
        return agent?.available !== false;
      }

      function agentAvailabilityNote(agentId) {
        const agent = agentById(agentId);
        return agent.availability_note || `${agent.name}将在后续版本开放。`;
      }

      function showAgentHint(agent) {
        if (!isAgentAvailable(agent)) hoveredAgentId.value = agent.id;
      }

      function hideAgentHint(agentId) {
        if (hoveredAgentId.value === agentId) hoveredAgentId.value = "";
      }

      function agentName(agentId) {
        return agentById(agentId).name;
      }

      function agentBadge(agentId) {
        return AGENT_BADGES[agentId] || "AI";
      }

      function threadMessageCount(agentId) {
        const thread = threads[agentId];
        if (!thread) return 0;
        return thread.messages.filter((message) => message.role === "user").length;
      }

      function isAgentStreaming(agentId) {
        return Boolean(threads[agentId]?.isStreaming);
      }

      function threadHasUnread(agentId) {
        return Boolean(threads[agentId]?.hasUnread);
      }

      function showToast(message, type = "error") {
        clearTimeout(toastTimer);
        toast.message = message;
        toast.type = type;
        toastTimer = setTimeout(() => {
          toast.message = "";
        }, 3200);
      }

      async function requestJson(url, options) {
        const response = await fetch(`${API_BASE}${url}`, options);
        if (!response.ok) throw new Error(await readError(response));
        return response.json();
      }

      async function loadAgents() {
        try {
          const data = await requestJson("/api/agents");
          if (Array.isArray(data.agents) && data.agents.length) {
            agents.value = data.agents;
          }
        } catch {
          agents.value = FALLBACK_AGENTS;
        }
        if (!isAgentAvailable(activeAgentId.value)) {
          activeAgentId.value = "team";
        }
      }

      async function checkHealth() {
        serviceStatus.value = "checking";
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 4500);
        try {
          const response = await fetch(`${API_BASE}/health`, {
            cache: "no-store",
            signal: controller.signal,
          });
          serviceStatus.value = response.ok ? "online" : "offline";
        } catch {
          serviceStatus.value = "offline";
        } finally {
          clearTimeout(timeout);
        }
      }

      function scrollToBottom() {
        nextTick(() => {
          if (messagesPanel.value) {
            messagesPanel.value.scrollTop = messagesPanel.value.scrollHeight;
          }
        });
      }

      function focusComposer() {
        nextTick(() => messageInput.value?.focus());
      }

      function resizeComposer() {
        nextTick(() => {
          const input = messageInput.value;
          if (!input) return;
          input.style.height = "auto";
          input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
        });
      }

      function resetWorkspace(id = createSessionId()) {
        workspaceId.value = id;
        for (const agent of FALLBACK_AGENTS) {
          threads[agent.id] = createThread(id, agent.id);
        }
        sharedContext.value = [];
        activeAgentId.value = "team";
        contextOpen.value = false;
      }

      function newChat() {
        if (isAnyStreaming.value) return;
        resetWorkspace();
        currentTitle.value = "新对话";
        activeView.value = "chat";
        sidebarOpen.value = false;
        focusComposer();
      }

      function switchAgent(agentId) {
        if (!threads[agentId]) return;
        if (!isAgentAvailable(agentId)) {
          showToast(agentAvailabilityNote(agentId));
          return;
        }
        activeAgentId.value = agentId;
        threads[agentId].hasUnread = false;
        activeView.value = "chat";
        sidebarOpen.value = false;
        resizeComposer();
        scrollToBottom();
        focusComposer();
      }

      async function loadConversations() {
        loadingConversations.value = true;
        try {
          const data = await requestJson("/api/conversations");
          conversations.value = Array.isArray(data.conversations)
            ? data.conversations
            : [];
        } catch (error) {
          conversations.value = [];
          if (serviceStatus.value !== "offline") showToast(error.message);
        } finally {
          loadingConversations.value = false;
        }
      }

      async function selectConversation(id) {
        if (isAnyStreaming.value || id === currentSessionId.value) {
          sidebarOpen.value = false;
          return;
        }
        loadingConversation.value = true;
        activeView.value = "chat";
        sidebarOpen.value = false;
        resetWorkspace(id);
        try {
          const data = await requestJson(`/api/conversations/${encodeURIComponent(id)}`);
          currentTitle.value = data.title || "新对话";
          threads.team.messages = (data.messages || []).map((message, index) => ({
            id: `${id}-${index}`,
            role: message.role === "user" ? "user" : "assistant",
            agentId: "team",
            content: String(message.content || ""),
            time: "",
            pending: false,
            error: false,
            stopped: false,
          }));
          scrollToBottom();
        } catch (error) {
          showToast(error.message);
          newChat();
        } finally {
          loadingConversation.value = false;
          focusComposer();
        }
      }

      async function deleteConversation(conversation) {
        if (isAnyStreaming.value) return;
        if (!window.confirm(`删除“${conversation.title || "新对话"}”？`)) return;
        try {
          await requestJson(
            `/api/conversations/${encodeURIComponent(conversation.id)}`,
            { method: "DELETE" }
          );
          if (conversation.id === currentSessionId.value) newChat();
          await loadConversations();
          showToast("对话已删除", "success");
        } catch (error) {
          showToast(error.message);
        }
      }

      function useSuggestion(prompt) {
        draft.value = prompt;
        focusComposer();
      }

      function contextExcerpt(content) {
        const normalized = String(content || "").replace(/\s+/g, " ").trim();
        return normalized.length > 220
          ? `${normalized.slice(0, 220)}...`
          : normalized;
      }

      function pinMessage(message, openPanel) {
        const existing = sharedContext.value.some(
          (item) => item.messageId === message.id
        );
        if (existing) {
          showToast("该证据已在共享上下文中");
          return false;
        }
        const sourceAgentId = message.agentId || activeAgentId.value;
        sharedContext.value.push({
          id: createSessionId(),
          messageId: message.id,
          sourceAgentId,
          sourceName: agentName(sourceAgentId),
          content: String(message.content || "").slice(0, 4000),
        });
        if (openPanel) contextOpen.value = true;
        return true;
      }

      function addToContext(message) {
        if (pinMessage(message, true)) {
          showToast("证据已加入共享上下文", "success");
        }
      }

      function handoffMessage(message, targetAgentId) {
        if (!isAgentAvailable(targetAgentId)) {
          showToast(agentAvailabilityNote(targetAgentId));
          return;
        }
        pinMessage(message, false);
        switchAgent(targetAgentId);
        const source = agentName(message.agentId);
        threads[targetAgentId].draft =
          targetAgentId === "operator"
            ? `请基于${source}提供的共享证据制定处理方案。`
            : `请基于${source}提供的共享证据进行分析。`;
        contextOpen.value = false;
        focusComposer();
      }

      function removeContext(id) {
        sharedContext.value = sharedContext.value.filter((item) => item.id !== id);
      }

      function clearContext() {
        sharedContext.value = [];
      }

      function currentTime() {
        return new Intl.DateTimeFormat("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        }).format(new Date());
      }

      function applyStreamEvent(eventText, assistantMessage, onContent) {
        const data = eventText
          .split(/\r?\n/)
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");

        if (!data) return false;
        if (data === "[DONE]") return true;

        const payload = JSON.parse(data);
        if (payload.error) throw new Error(payload.error);
        if (payload.content) {
          assistantMessage.content += payload.content;
          onContent();
          if (activeAgentId.value === assistantMessage.agentId) {
            scrollToBottom();
          }
        }
        return false;
      }

      function stopAgent(agentId = activeAgentId.value) {
        const thread = threads[agentId];
        if (!thread?.isStreaming) return;

        if (thread.queuedRequest) {
          const queuedRequest = thread.queuedRequest;
          thread.queuedRequest = null;
          queuedRequest.assistantMessage.pending = false;
          queuedRequest.assistantMessage.stopped = true;
          thread.isStreaming = false;
          focusComposer();
          return;
        }

        const controller = streamControllers.get(agentId);
        if (!controller) return;
        controller.abort();
      }

      async function executeMessage(request) {
        const {
          agentId,
          text,
          assistantMessage,
          context,
        } = request;
        const thread = threads[agentId];
        if (!thread || isDisposed) return;

        thread.requestActive = true;
        thread.isStreaming = true;
        const endpoint =
          agentId === "team"
            ? "/api/chat"
            : `/api/agents/${encodeURIComponent(agentId)}/chat`;
        const body = {
          message: text,
          session_id: thread.sessionId,
        };
        if (agentId !== "team") {
          body.context = context;
        }

        const controller = new AbortController();
        streamControllers.set(agentId, controller);
        let contentIdleTimer = null;

        const markContentActivity = () => {
          clearTimeout(contentIdleTimer);
          assistantMessage.pending = true;
          if (!thread.queuedRequest) thread.isStreaming = true;

          contentIdleTimer = setTimeout(() => {
            if (isDisposed) return;
            assistantMessage.pending = false;
            if (!thread.queuedRequest) thread.isStreaming = false;
            thread.hasUnread = activeAgentId.value !== agentId;
            if (activeAgentId.value === agentId) focusComposer();
          }, STREAM_IDLE_RELEASE_MS);
        };

        try {
          const response = await fetch(`${API_BASE}${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            signal: controller.signal,
          });
          if (!response.ok) throw new Error(await readError(response));
          if (!response.body) throw new Error("浏览器不支持流式响应");

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";
          let receivedDoneEvent = false;

          while (!receivedDoneEvent) {
            const { done, value } = await reader.read();
            buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
            const events = buffer.split(/\r?\n\r?\n/);
            buffer = events.pop() || "";

            for (const event of events) {
              receivedDoneEvent = applyStreamEvent(
                event,
                assistantMessage,
                markContentActivity
              );
              if (receivedDoneEvent) break;
            }

            if (receivedDoneEvent) {
              await reader.cancel().catch(() => {});
              break;
            }
            if (done) break;
          }

          if (!receivedDoneEvent && buffer.trim()) {
            applyStreamEvent(buffer, assistantMessage, markContentActivity);
          }
          if (!assistantMessage.content) {
            assistantMessage.content = "未收到回复内容，请稍后重试。";
            assistantMessage.error = true;
          }
        } catch (error) {
          if (error?.name === "AbortError") {
            assistantMessage.stopped = true;
          } else {
            assistantMessage.content = `请求失败：${error.message}`;
            assistantMessage.error = true;
          }
        } finally {
          clearTimeout(contentIdleTimer);
          if (streamControllers.get(agentId) === controller) {
            streamControllers.delete(agentId);
          }
          assistantMessage.pending = false;
          thread.requestActive = false;
          thread.hasUnread = activeAgentId.value !== agentId;

          const queuedRequest = thread.queuedRequest;
          thread.queuedRequest = null;
          if (queuedRequest && !isDisposed) {
            thread.isStreaming = true;
            void executeMessage(queuedRequest);
          } else {
            thread.isStreaming = false;
            if (activeAgentId.value === agentId) focusComposer();
          }
          void loadConversations();
        }
      }

      async function sendMessage() {
        const text = draft.value.trim();
        const agentId = activeAgentId.value;
        const thread = threads[agentId];
        if (
          !text ||
          !thread ||
          thread.isStreaming ||
          !isAgentAvailable(agentId)
        ) {
          return;
        }
        const sentAt = currentTime();
        const assistantMessage = reactive({
          id: `assistant-${Date.now()}`,
          role: "assistant",
          agentId,
          content: "",
          time: sentAt,
          pending: true,
          error: false,
          stopped: false,
        });

        thread.messages.push(
          {
            id: `user-${Date.now()}`,
            role: "user",
            agentId,
            content: text,
            time: sentAt,
            pending: false,
            error: false,
          },
          assistantMessage
        );
        if (currentTitle.value === "新对话") {
          currentTitle.value = text.replace(/\s+/g, " ").slice(0, 30);
        }

        thread.draft = "";
        thread.isStreaming = true;
        thread.hasUnread = false;
        resizeComposer();
        scrollToBottom();

        const request = {
          agentId,
          text,
          assistantMessage,
          context:
            agentId === "team"
              ? []
              : sharedContext.value.map((item) => item.content),
        };

        if (thread.requestActive) {
          thread.queuedRequest = request;
          return;
        }
        await executeMessage(request);
      }

      function handleComposerKeydown(event) {
        if (
          event.key === "Enter" &&
          !event.shiftKey &&
          !event.isComposing
        ) {
          event.preventDefault();
          sendMessage();
        }
      }

      function switchView(view) {
        activeView.value = view;
        sidebarOpen.value = false;
        if (view === "inspections") loadInspections();
        else focusComposer();
      }

      function ensureInspectionPolling() {
        const hasRunning = inspections.value.some((item) => item.status === "running");
        if (hasRunning && !inspectionTimer) {
          inspectionTimer = setInterval(loadInspections, 4000);
        } else if (!hasRunning && inspectionTimer) {
          clearInterval(inspectionTimer);
          inspectionTimer = null;
        }
      }

      async function loadInspections() {
        loadingInspections.value = true;
        try {
          const data = await requestJson("/api/inspections");
          inspections.value = Array.isArray(data.records) ? data.records : [];
          if (!expandedInspectionId.value && inspections.value.length) {
            expandedInspectionId.value = inspections.value[0].id;
          }
          ensureInspectionPolling();
        } catch (error) {
          showToast(error.message);
        } finally {
          loadingInspections.value = false;
        }
      }

      async function runInspection() {
        if (startingInspection.value || runningInspectionCount.value) return;
        startingInspection.value = true;
        try {
          const record = await requestJson("/api/inspect", { method: "POST" });
          expandedInspectionId.value = record.id;
          await loadInspections();
          showToast("巡检已启动", "success");
        } catch (error) {
          showToast(error.message);
        } finally {
          startingInspection.value = false;
        }
      }

      function toggleInspection(id) {
        expandedInspectionId.value =
          expandedInspectionId.value === id ? "" : id;
      }

      function inspectionStatusText(status) {
        return {
          completed: "已完成",
          failed: "执行失败",
          running: "执行中",
        }[status] || status;
      }

      function inspectionStatusClass(status) {
        return status === "completed"
          ? "completed"
          : status === "failed"
            ? "failed"
            : "running";
      }

      function formatDateTime(value) {
        if (!value) return "时间未知";
        const date = new Date(String(value).replace(" ", "T"));
        if (Number.isNaN(date.getTime())) return value;
        return new Intl.DateTimeFormat("zh-CN", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        }).format(date);
      }

      function formatConversationTime(value) {
        if (!value) return "";
        const date = new Date(String(value).replace(" ", "T"));
        if (Number.isNaN(date.getTime())) return value;
        return new Intl.DateTimeFormat("zh-CN", {
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        }).format(date);
      }

      watch(draft, resizeComposer);

      onMounted(() => {
        loadAgents();
        loadConversations();
        checkHealth();
        focusComposer();
        healthTimer = setInterval(checkHealth, 30000);
      });

      onUnmounted(() => {
        isDisposed = true;
        Object.values(threads).forEach((thread) => {
          thread.queuedRequest = null;
        });
        streamControllers.forEach((controller) => controller.abort());
        streamControllers.clear();
        clearInterval(healthTimer);
        clearInterval(inspectionTimer);
        clearTimeout(toastTimer);
      });

      return {
        activeAgent,
        activeAgentHeadline,
        activeAgentId,
        activeSuggestions,
        activeView,
        addToContext,
        agentAvailabilityNote,
        agentBadge,
        agentName,
        agents,
        canSend,
        checkHealth,
        clearContext,
        composerPlaceholder,
        contextExcerpt,
        contextOpen,
        conversationCount,
        conversationQuery,
        conversations,
        currentSessionId,
        currentTitle,
        deleteConversation,
        draft,
        expandedInspectionId,
        filteredConversations,
        formatConversationTime,
        formatDateTime,
        handleComposerKeydown,
        handoffMessage,
        hideAgentHint,
        inspectionStats,
        inspectionStatusClass,
        inspectionStatusText,
        inspections,
        isAgentAvailable,
        isAgentStreaming,
        isAnyStreaming,
        isStreaming,
        loadInspections,
        loadingConversation,
        loadingConversations,
        loadingInspections,
        messageInput,
        messages,
        messagesPanel,
        newChat,
        pageTitle,
        removeContext,
        renderMarkdown,
        runInspection,
        runningInspectionCount,
        selectConversation,
        sendMessage,
        serviceStatus,
        serviceStatusText,
        sharedContext,
        showAgentHint,
        sidebarOpen,
        startingInspection,
        stopAgent,
        switchAgent,
        switchView,
        threadHasUnread,
        threadMessageCount,
        toast,
        toggleInspection,
        unavailableAgentHint,
        useSuggestion,
        responseSummary,
        shouldCollapseResponse,
      };
  }
