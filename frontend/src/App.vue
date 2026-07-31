<script setup>
import AppIcon from "./components/AppIcon.vue";
import { useOperationsConsole } from "./composables/useOperationsConsole";

const {
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
  conciseMode,
  composerPlaceholder,
  contextExcerpt,
  contextOpen,
  copyMessage,
  conversationCount,
  conversationQuery,
  currentSessionId,
  currentTitle,
  deleteConversation,
  draft,
  draftMaxLength,
  editMessage,
  expandedInspectionId,
  filteredConversations,
  formatConversationTime,
  formatDateTime,
  handleComposerKeydown,
  handleMessagesScroll,
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
  showScrollToLatest,
  sidebarOpen,
  startingInspection,
  stopAgent,
  scrollToLatest,
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
} = useOperationsConsole();
</script>

<template>
  <div>
    <div class="app-shell">
      <button
        v-if="sidebarOpen"
        class="sidebar-backdrop"
        type="button"
        aria-label="关闭导航"
        @click="sidebarOpen = false"
      ></button>

      <aside class="sidebar" :class="{ open: sidebarOpen }">
        <div class="brand">
          <div class="brand-mark" aria-hidden="true">K8s</div>
          <div>
            <strong>智能运维</strong>
            <span>Operations Console</span>
          </div>
        </div>

        <button class="new-chat-button" type="button" :disabled="isAnyStreaming" @click="newChat">
          <app-icon name="Plus"></app-icon>
          新建对话
        </button>

        <nav class="primary-nav" aria-label="主导航">
          <button
            type="button"
            :class="{ active: activeView === 'chat' }"
            @click="switchView('chat')"
          >
            <span class="nav-icon" aria-hidden="true">
              <app-icon name="MessageSquareText"></app-icon>
            </span>
            对话诊断
          </button>
          <button
            type="button"
            :class="{ active: activeView === 'inspections' }"
            @click="switchView('inspections')"
          >
            <span class="nav-icon" aria-hidden="true">
              <app-icon name="ClipboardCheck"></app-icon>
            </span>
            集群巡检
            <span v-if="runningInspectionCount" class="nav-count">
              {{ runningInspectionCount }}
            </span>
          </button>
        </nav>

        <section class="conversation-section" aria-labelledby="conversation-title">
          <div class="section-heading">
            <span id="conversation-title">最近对话</span>
            <span>{{ conversationCount }}</span>
          </div>

          <label class="conversation-search">
            <span class="sr-only">搜索对话</span>
            <input v-model.trim="conversationQuery" type="search" placeholder="搜索对话">
          </label>

          <div class="conversation-list">
            <div v-if="loadingConversations" class="sidebar-state">正在加载...</div>
            <div
              v-else-if="!filteredConversations.length"
              class="sidebar-state"
            >
              {{ conversationQuery ? '没有匹配的对话' : '暂无历史对话' }}
            </div>
            <div
              v-for="conversation in filteredConversations"
              :key="conversation.id"
              class="conversation-item"
              :class="{ active: conversation.id === currentSessionId }"
            >
              <button
                class="conversation-open"
                type="button"
                :disabled="isAnyStreaming"
                @click="selectConversation(conversation.id)"
              >
                <span class="conversation-copy">
                  <strong>{{ conversation.title || '新对话' }}</strong>
                  <small>{{ formatConversationTime(conversation.updated_at || conversation.created_at) }}</small>
                </span>
              </button>
              <button
                class="delete-conversation"
                type="button"
                title="删除对话"
                aria-label="删除对话"
                :disabled="isAnyStreaming"
                @click="deleteConversation(conversation)"
              ><app-icon name="Trash2"></app-icon></button>
            </div>
          </div>
        </section>

        <div class="sidebar-footer">
          <span class="status-dot" :class="serviceStatus"></span>
          <span>{{ serviceStatusText }}</span>
          <button type="button" title="重新检测" aria-label="重新检测" @click="checkHealth">
            <app-icon name="RefreshCw"></app-icon>
          </button>
        </div>
      </aside>

      <main class="workspace">
        <header class="workspace-header">
          <div class="header-leading">
            <button
              class="menu-button"
              type="button"
              aria-label="打开导航"
              title="打开导航"
              @click="sidebarOpen = true"
            ><app-icon name="Menu"></app-icon></button>
            <div>
              <span class="header-kicker">
                {{ activeView === 'chat' ? activeAgent.name : '集群巡检' }}
              </span>
              <h1>{{ pageTitle }}</h1>
            </div>
          </div>
          <div class="header-status" :class="serviceStatus">
            <span class="status-dot" :class="serviceStatus"></span>
            {{ serviceStatusText }}
          </div>
        </header>

        <section v-if="activeView === 'chat'" class="chat-view">
          <div class="agent-workspace-bar">
            <div class="agent-tabs" role="tablist" aria-label="Agent 工作区">
              <button
                v-for="agent in agents"
                :key="agent.id"
                class="agent-tab"
                :class="[
                  agent.id,
                  {
                    active: activeAgentId === agent.id,
                    streaming: isAgentStreaming(agent.id),
                    unread: threadHasUnread(agent.id),
                    unavailable: !isAgentAvailable(agent),
                  },
                ]"
                type="button"
                role="tab"
                :aria-selected="activeAgentId === agent.id"
                :aria-disabled="!isAgentAvailable(agent)"
                :aria-describedby="
                  !isAgentAvailable(agent) ? 'agent-availability-hint' : null
                "
                :title="
                  !isAgentAvailable(agent)
                    ? agentAvailabilityNote(agent.id)
                    : null
                "
                @mouseenter="showAgentHint(agent)"
                @mouseleave="hideAgentHint(agent.id)"
                @focus="showAgentHint(agent)"
                @blur="hideAgentHint(agent.id)"
                @click="switchAgent(agent.id)"
              >
                <span class="agent-tab-icon" aria-hidden="true">
                  <app-icon :name="agent.icon"></app-icon>
                </span>
                <span class="agent-tab-copy">
                  <strong>{{ agent.name }}</strong>
                  <small>
                    {{
                      isAgentStreaming(agent.id)
                        ? '处理中'
                        : isAgentAvailable(agent)
                          ? agent.permission
                          : '规划中'
                    }}
                  </small>
                </span>
                <span class="agent-tab-status">
                  <app-icon
                    v-if="isAgentStreaming(agent.id)"
                    name="LoaderCircle"
                  ></app-icon>
                  <span
                    v-else-if="threadHasUnread(agent.id)"
                    class="agent-unread"
                    aria-label="有新回复"
                    title="有新回复"
                  ></span>
                  <app-icon
                    v-else-if="!isAgentAvailable(agent)"
                    name="Clock3"
                  ></app-icon>
                  <span v-if="threadMessageCount(agent.id)" class="thread-count">
                    {{ threadMessageCount(agent.id) }}
                  </span>
                </span>
              </button>
            </div>
            <button
              class="context-toggle"
              type="button"
              :class="{ active: contextOpen }"
              @click="contextOpen = !contextOpen"
            >
              <app-icon name="PanelRight"></app-icon>
              共享上下文
              <span>{{ sharedContext.length }}</span>
            </button>
            <transition name="agent-hint">
              <div
                v-if="unavailableAgentHint"
                id="agent-availability-hint"
                class="agent-availability-tooltip"
                role="tooltip"
              >
                <span>功能规划中</span>
                <strong>
                  {{ unavailableAgentHint.name }}
                  · {{ unavailableAgentHint.english_name }}
                </strong>
                <p>{{ unavailableAgentHint.description }}</p>
                <small>{{ unavailableAgentHint.availability_note }}</small>
              </div>
            </transition>
          </div>

          <div class="chat-stage">
            <div class="chat-column">
              <div
                ref="messagesPanel"
                class="messages-panel"
                @scroll.passive="handleMessagesScroll"
              >
                <div class="messages-content">
                  <div v-if="loadingConversation" class="conversation-loading">
                    <span></span><span></span><span></span>
                  </div>

                  <div v-else-if="!messages.length" class="empty-chat">
                    <div class="empty-mark" :class="activeAgentId" aria-hidden="true">
                      <span></span><span></span><span></span>
                      <strong>{{ agentBadge(activeAgentId) }}</strong>
                    </div>
                    <p class="empty-label">{{ activeAgent.english_name }}</p>
                    <h2>{{ activeAgentHeadline }}</h2>
                    <p class="agent-description">{{ activeAgent.description }}</p>
                    <div class="suggestion-grid">
                      <button
                        v-for="suggestion in activeSuggestions"
                        :key="suggestion.title"
                        type="button"
                        @click="useSuggestion(suggestion.prompt)"
                      >
                        <span>{{ suggestion.label }}</span>
                        <strong>{{ suggestion.title }}</strong>
                        <small>{{ suggestion.detail }}</small>
                      </button>
                    </div>
                  </div>

                  <div v-else class="message-list" aria-live="polite">
                    <article
                      v-for="message in messages"
                      :key="message.id"
                      class="message-row"
                      :class="[message.role, `agent-${message.agentId || activeAgentId}`]"
                    >
                      <div class="message-avatar" aria-hidden="true">
                        {{ message.role === 'user' ? '你' : agentBadge(message.agentId) }}
                      </div>
                      <div class="message-body">
                        <div class="message-meta">
                          <strong>
                            {{ message.role === 'user' ? '你' : agentName(message.agentId) }}
                          </strong>
                          <span>{{ message.time }}</span>
                        </div>
                        <div
                          v-if="message.role === 'user'"
                          class="message-text"
                          v-text="message.content"
                        ></div>
                        <div
                          v-else-if="message.pending && !message.content"
                          class="thinking"
                          :aria-label="`${agentName(message.agentId)}正在生成回复`"
                        >
                          <span></span><span></span><span></span>
                        </div>
                        <div
                          v-else-if="message.pending"
                          class="streaming-text"
                          v-text="message.content"
                        ></div>
                        <template v-else-if="shouldCollapseResponse(message)">
                          <section class="response-summary">
                            <span>总结</span>
                            <p v-text="responseSummary(message.content)"></p>
                          </section>
                          <details class="response-details">
                            <summary>
                              <span>完整信息</span>
                              <small>{{ message.content.length }} 字</small>
                              <app-icon name="ChevronDown"></app-icon>
                            </summary>
                            <div
                              class="markdown"
                              v-html="renderMarkdown(message.content)"
                            ></div>
                          </details>
                        </template>
                        <div
                          v-else
                          class="markdown"
                          :class="{ error: message.error }"
                          v-html="renderMarkdown(message.content)"
                        ></div>
                        <div v-if="message.stopped" class="message-state stopped">
                          <app-icon name="Square"></app-icon>
                          已停止生成
                        </div>
                        <div
                          v-if="
                            message.content &&
                            (message.role === 'user' || !message.pending)
                          "
                          class="message-actions"
                        >
                          <button
                            type="button"
                            :title="
                              message.role === 'user'
                                ? '复制输入'
                                : '复制完整回复'
                            "
                            @click="copyMessage(message)"
                          >
                            <app-icon name="Copy"></app-icon>
                            复制
                          </button>
                          <button
                            v-if="message.role === 'user'"
                            type="button"
                            title="放回输入框继续编辑"
                            @click="editMessage(message)"
                          >
                            <app-icon name="Pencil"></app-icon>
                            重新编辑
                          </button>
                          <template
                            v-if="
                              message.role === 'assistant' &&
                              !message.pending &&
                              !message.error
                            "
                          >
                            <button type="button" @click="addToContext(message)">
                              <app-icon name="Pin"></app-icon>
                              固定证据
                            </button>
                            <button
                              v-if="message.agentId !== 'analyst'"
                              type="button"
                              @click="handoffMessage(message, 'analyst')"
                            >
                              <app-icon name="ArrowRight"></app-icon>
                              交给分析师
                            </button>
                            <button
                              v-if="message.agentId !== 'operator'"
                              type="button"
                              :disabled="!isAgentAvailable('operator')"
                              :title="agentAvailabilityNote('operator')"
                              @click="handoffMessage(message, 'operator')"
                            >
                              <app-icon name="ListChecks"></app-icon>
                              操作员规划中
                            </button>
                          </template>
                        </div>
                      </div>
                    </article>
                  </div>
                </div>
              </div>

              <div class="composer-area">
                <transition name="scroll-latest">
                  <button
                    v-if="showScrollToLatest"
                    class="scroll-to-latest"
                    type="button"
                    title="回到最新消息"
                    aria-label="回到最新消息并继续跟随输出"
                    @click="scrollToLatest"
                  >
                    <app-icon name="ChevronDown"></app-icon>
                    <span>回到最新</span>
                  </button>
                </transition>
                <div v-if="activeAgentId === 'operator'" class="operator-safety">
                  <app-icon name="ShieldCheck"></app-icon>
                  <span><strong>方案模式</strong> 不会执行任何集群变更</span>
                </div>
                <div class="composer-options">
                  <label class="concise-switch" :class="{ active: conciseMode }">
                    <input
                      v-model="conciseMode"
                      type="checkbox"
                      role="switch"
                      :aria-checked="conciseMode"
                      aria-label="简洁模式"
                    >
                    <span class="switch-track" aria-hidden="true">
                      <span></span>
                    </span>
                    <span class="switch-copy">
                      <strong>简洁模式</strong>
                      <small>
                        {{ conciseMode ? '已开启 · 优先简短回答' : '已关闭' }}
                      </small>
                    </span>
                  </label>
                </div>
                <form class="composer" @submit.prevent="sendMessage">
                  <textarea
                    ref="messageInput"
                    v-model="draft"
                    rows="1"
                    :maxlength="draftMaxLength"
                    :placeholder="composerPlaceholder"
                    aria-label="消息"
                    :aria-busy="isStreaming"
                    @keydown="handleComposerKeydown"
                  ></textarea>
                  <div class="composer-actions">
                    <button
                      v-if="isStreaming"
                      class="send-button stop-button"
                      type="button"
                      :title="`停止${activeAgent.name}生成`"
                      :aria-label="`停止${activeAgent.name}生成`"
                      @click="stopAgent(activeAgentId)"
                    >
                      <app-icon name="Square"></app-icon>
                    </button>
                    <button
                      class="send-button"
                      type="submit"
                      :disabled="!canSend"
                      :title="isStreaming ? '排队发送下一条' : '发送'"
                      :aria-label="isStreaming ? '排队发送消息' : '发送消息'"
                    >
                      <app-icon name="ArrowUp"></app-icon>
                    </button>
                  </div>
                </form>
                <div class="composer-footer">
                  <span>
                    {{ isStreaming ? `${activeAgent.name}正在处理` : activeAgent.permission }}
                  </span>
                  <span>{{ draft.length }} / {{ draftMaxLength }}</span>
                </div>
              </div>
            </div>

            <button
              v-if="contextOpen"
              class="context-backdrop"
              type="button"
              aria-label="关闭共享上下文"
              @click="contextOpen = false"
            ></button>
            <aside class="context-panel" :class="{ open: contextOpen }">
              <header>
                <div>
                  <span>当前事件</span>
                  <strong>共享上下文</strong>
                </div>
                <div class="context-header-actions">
                  <button
                    v-if="sharedContext.length"
                    type="button"
                    title="清空共享上下文"
                    aria-label="清空共享上下文"
                    @click="clearContext"
                  ><app-icon name="Trash2"></app-icon></button>
                  <button
                    class="context-close"
                    type="button"
                    title="关闭"
                    aria-label="关闭"
                    @click="contextOpen = false"
                  ><app-icon name="X"></app-icon></button>
                </div>
              </header>
              <div v-if="!sharedContext.length" class="context-empty">
                <app-icon name="Pin"></app-icon>
                <strong>暂无共享证据</strong>
              </div>
              <div v-else class="context-list">
                <article v-for="item in sharedContext" :key="item.id">
                  <div class="context-source">
                    <span :class="item.sourceAgentId">
                      {{ agentBadge(item.sourceAgentId) }}
                    </span>
                    <strong>{{ item.sourceName }}</strong>
                    <button
                      type="button"
                      title="移除"
                      aria-label="移除"
                      @click="removeContext(item.id)"
                    ><app-icon name="X"></app-icon></button>
                  </div>
                  <p>{{ contextExcerpt(item.content) }}</p>
                </article>
              </div>
            </aside>
          </div>
        </section>

        <section v-else class="inspection-view">
          <div class="inspection-toolbar">
            <div class="inspection-summary">
              <div>
                <span>巡检总数</span>
                <strong>{{ inspectionStats.total }}</strong>
              </div>
              <div>
                <span>正常完成</span>
                <strong class="success-text">{{ inspectionStats.completed }}</strong>
              </div>
              <div>
                <span>执行失败</span>
                <strong class="danger-text">{{ inspectionStats.failed }}</strong>
              </div>
              <div>
                <span>执行中</span>
                <strong class="info-text">{{ inspectionStats.running }}</strong>
              </div>
            </div>
            <div class="inspection-actions">
              <button
                class="secondary-button icon-button"
                type="button"
                title="刷新巡检记录"
                aria-label="刷新巡检记录"
                :disabled="loadingInspections"
                @click="loadInspections"
              ><app-icon name="RefreshCw"></app-icon></button>
              <button
                class="primary-button"
                type="button"
                :disabled="startingInspection || runningInspectionCount > 0"
                @click="runInspection"
              >
                <app-icon name="Play"></app-icon>
                {{ startingInspection ? '正在启动' : '立即巡检' }}
              </button>
            </div>
          </div>

          <div class="inspection-content">
            <div v-if="loadingInspections && !inspections.length" class="inspection-empty">
              正在加载巡检记录...
            </div>
            <div v-else-if="!inspections.length" class="inspection-empty">
              <strong>暂无巡检记录</strong>
              <span>启动首次巡检后，结果会显示在这里。</span>
            </div>
            <div v-else class="inspection-list">
              <article
                v-for="record in inspections"
                :key="record.id"
                class="inspection-record"
                :class="{ expanded: expandedInspectionId === record.id }"
              >
                <button
                  class="inspection-record-header"
                  type="button"
                  :aria-expanded="expandedInspectionId === record.id"
                  @click="toggleInspection(record.id)"
                >
                  <span class="inspection-status" :class="record.status">
                    <span class="status-dot" :class="inspectionStatusClass(record.status)"></span>
                    {{ inspectionStatusText(record.status) }}
                  </span>
                  <span class="inspection-title">
                    <strong>集群健康巡检</strong>
                    <small>{{ formatDateTime(record.timestamp) }}</small>
                  </span>
                  <span class="inspection-trigger">
                    {{ record.trigger === 'manual' ? '手动触发' : '定时任务' }}
                  </span>
                  <span class="inspection-toggle" aria-hidden="true">
                    <app-icon
                      :name="expandedInspectionId === record.id ? 'ChevronUp' : 'ChevronDown'"
                    ></app-icon>
                  </span>
                </button>
                <div v-if="expandedInspectionId === record.id" class="inspection-result">
                  <div v-if="record.status === 'running'" class="inspection-running">
                    <span class="button-spinner"></span>
                    Agent 正在执行集群巡检
                  </div>
                  <div
                    v-else
                    class="markdown"
                    :class="{ error: record.status === 'failed' }"
                    v-html="renderMarkdown(record.status === 'failed' ? record.error : record.response)"
                  ></div>
                </div>
              </article>
            </div>
          </div>
        </section>
      </main>
    </div>

    <div v-if="toast.message" class="toast" :class="toast.type" role="status">
      {{ toast.message }}
    </div>
  </div>

</template>
