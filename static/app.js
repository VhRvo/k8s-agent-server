(() => {
  "use strict";

  const {
    computed,
    createApp,
    h,
    nextTick,
    onMounted,
    onUnmounted,
    reactive,
    ref,
    watch,
  } = Vue;

  const API_BASE = "/backend";

  const LucideIcon = {
    props: {
      name: {
        type: String,
        required: true,
      },
    },
    setup(props) {
      return () => {
        const icon =
          globalThis.lucide?.icons?.[props.name] ||
          globalThis.lucide?.icons?.Circle;
        if (!icon) return h("span", { class: "lucide", "aria-hidden": "true" });

        const [tag, attributes, children] = icon;
        return h(
          tag,
          {
            ...attributes,
            class: "lucide",
            "aria-hidden": "true",
          },
          children.map(([childTag, childAttributes]) =>
            h(childTag, childAttributes)
          )
        );
      };
    },
  };

  const suggestions = [
    {
      label: "HEALTH",
      title: "检查集群健康",
      detail: "查看节点、工作负载与关键组件状态",
      prompt: "检查集群整体健康状况，并列出需要优先处理的问题。",
    },
    {
      label: "PODS",
      title: "分析异常 Pod",
      detail: "定位重启、Pending 与运行失败原因",
      prompt: "查找当前异常的 Pod，分析原因并给出处理建议。",
    },
    {
      label: "RESOURCES",
      title: "查看资源压力",
      detail: "检查节点与工作负载的资源使用情况",
      prompt: "查看节点资源使用情况，找出 CPU 或内存压力较高的对象。",
    },
  ];

  function createSessionId() {
    return globalThis.crypto?.randomUUID?.() || `session-${Date.now()}`;
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

  async function readError(response) {
    try {
      const data = await response.json();
      return data.detail || data.error || `请求失败 (${response.status})`;
    } catch {
      return `请求失败 (${response.status})`;
    }
  }

  const app = createApp({
    setup() {
      const activeView = ref("chat");
      const sidebarOpen = ref(false);
      const serviceStatus = ref("checking");
      const currentSessionId = ref("");
      const currentTitle = ref("新对话");
      const conversations = ref([]);
      const conversationQuery = ref("");
      const loadingConversations = ref(false);
      const loadingConversation = ref(false);
      const messages = ref([]);
      const draft = ref("");
      const isStreaming = ref(false);
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

      const filteredConversations = computed(() => {
        const query = conversationQuery.value.toLowerCase();
        if (!query) return conversations.value;
        return conversations.value.filter((item) =>
          String(item.title || "").toLowerCase().includes(query)
        );
      });

      const pageTitle = computed(() =>
        activeView.value === "chat" ? currentTitle.value : "集群巡检"
      );

      const canSend = computed(
        () => Boolean(draft.value.trim()) && !isStreaming.value
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

      function newChat() {
        if (isStreaming.value) return;
        currentSessionId.value = createSessionId();
        currentTitle.value = "新对话";
        messages.value = [];
        draft.value = "";
        activeView.value = "chat";
        sidebarOpen.value = false;
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
        if (isStreaming.value || id === currentSessionId.value) {
          sidebarOpen.value = false;
          return;
        }
        loadingConversation.value = true;
        activeView.value = "chat";
        sidebarOpen.value = false;
        currentSessionId.value = id;
        messages.value = [];
        try {
          const data = await requestJson(`/api/conversations/${encodeURIComponent(id)}`);
          currentTitle.value = data.title || "新对话";
          messages.value = (data.messages || []).map((message, index) => ({
            id: `${id}-${index}`,
            role: message.role === "user" ? "user" : "assistant",
            content: String(message.content || ""),
            time: "",
            pending: false,
            error: false,
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
        if (isStreaming.value) return;
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

      function currentTime() {
        return new Intl.DateTimeFormat("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        }).format(new Date());
      }

      function applyStreamEvent(eventText, assistantMessage) {
        const data = eventText
          .split(/\r?\n/)
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart())
          .join("\n");

        if (!data || data === "[DONE]") return;
        const payload = JSON.parse(data);
        if (payload.error) throw new Error(payload.error);
        if (payload.content) {
          assistantMessage.content += payload.content;
          scrollToBottom();
        }
      }

      async function sendMessage() {
        const text = draft.value.trim();
        if (!text || isStreaming.value) return;
        if (!currentSessionId.value) currentSessionId.value = createSessionId();

        const sentAt = currentTime();
        const assistantMessage = reactive({
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: "",
          time: sentAt,
          pending: true,
          error: false,
        });

        messages.value.push(
          {
            id: `user-${Date.now()}`,
            role: "user",
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

        draft.value = "";
        isStreaming.value = true;
        resizeComposer();
        scrollToBottom();

        try {
          const response = await fetch(`${API_BASE}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              message: text,
              session_id: currentSessionId.value,
            }),
          });
          if (!response.ok) throw new Error(await readError(response));
          if (!response.body) throw new Error("浏览器不支持流式响应");

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          while (true) {
            const { done, value } = await reader.read();
            buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
            const events = buffer.split(/\r?\n\r?\n/);
            buffer = events.pop() || "";
            events.forEach((event) => applyStreamEvent(event, assistantMessage));
            if (done) break;
          }

          if (buffer.trim()) applyStreamEvent(buffer, assistantMessage);
          if (!assistantMessage.content) {
            assistantMessage.content = "未收到回复内容，请稍后重试。";
            assistantMessage.error = true;
          }
        } catch (error) {
          assistantMessage.content = `请求失败：${error.message}`;
          assistantMessage.error = true;
        } finally {
          assistantMessage.pending = false;
          isStreaming.value = false;
          await loadConversations();
          focusComposer();
        }
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
          if (
            !expandedInspectionId.value &&
            inspections.value.length
          ) {
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
        newChat();
        loadConversations();
        checkHealth();
        healthTimer = setInterval(checkHealth, 30000);
      });

      onUnmounted(() => {
        clearInterval(healthTimer);
        clearInterval(inspectionTimer);
        clearTimeout(toastTimer);
      });

      return {
        activeView,
        canSend,
        checkHealth,
        conversationQuery,
        conversations,
        currentSessionId,
        deleteConversation,
        draft,
        expandedInspectionId,
        filteredConversations,
        formatConversationTime,
        formatDateTime,
        handleComposerKeydown,
        inspectionStats,
        inspectionStatusClass,
        inspectionStatusText,
        inspections,
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
        renderMarkdown,
        runInspection,
        runningInspectionCount,
        selectConversation,
        serviceStatus,
        serviceStatusText,
        sidebarOpen,
        startingInspection,
        suggestions,
        switchView,
        toast,
        toggleInspection,
        useSuggestion,
        sendMessage,
      };
    },
  });

  app.component("AppIcon", LucideIcon);
  app.mount("#app");
})();
