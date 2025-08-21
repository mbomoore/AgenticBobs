<template>
  <div class="chat-container">
    <div class="chat-header">
      <h3>The Bobs 2.0</h3>
      <div class="header-actions">
        <span v-if="chatStore.sessionId" class="session-id">
          Session: {{ chatStore.sessionId.slice(0, 8) }}...
        </span>
        <button 
          @click="clearChat" 
          class="clear-btn"
          :disabled="chatStore.isLoading"
        >
          Clear
        </button>
      </div>
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div 
        v-for="(message, index) in chatStore.messages" 
        :key="index"
        class="message"
        :class="message.role"
      >
        <div class="message-content">
          <p>{{ message.content }}</p>
          <small v-if="message.timestamp" class="timestamp">
            {{ formatTimestamp(message.timestamp) }}
          </small>
        </div>
      </div>

      <!-- Refinement Questions -->
      <div v-if="chatStore.refinementQuestions.length > 0" class="refinement-questions">
        <h4>Follow-up questions:</h4>
        <ul>
          <li 
            v-for="(question, index) in chatStore.refinementQuestions" 
            :key="index"
            @click="selectQuestion(question)"
            class="question-item"
          >
            {{ question }}
          </li>
        </ul>
      </div>

      <!-- Loading indicator -->
      <div v-if="chatStore.isLoading" class="message assistant loading">
        <div class="message-content">
          <div class="typing-indicator">
            <div class="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span class="thinking-text">Bob is thinking...</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Error display -->
    <div v-if="chatStore.error" class="error-banner">
      <p>{{ chatStore.error }}</p>
      <button @click="chatStore.error = null" class="close-error">×</button>
    </div>

    <div class="chat-input">
      <form @submit.prevent="sendMessage">
        <div class="input-group">
          <textarea
            v-model="currentMessage"
            placeholder="Well, Bobs..."
            rows="2"
            :disabled="chatStore.isLoading"
            @keydown.enter.exact.prevent="sendMessage"
            @keydown.enter.shift.exact="insertNewline"
            ref="textareaRef"
          ></textarea>
          <button 
            type="submit" 
            :disabled="chatStore.isLoading || !currentMessage.trim()"
            class="send-btn"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
            </svg>
          </button>
        </div>
        <div class="input-hints">
          <small>Press Enter to send, Shift+Enter for new line</small>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useChatStore } from '../stores/chat'

const chatStore = useChatStore()
const currentMessage = ref('')
const messagesContainer = ref<HTMLElement>()
const textareaRef = ref<HTMLTextAreaElement>()

const sendMessage = async () => {
  if (!currentMessage.value.trim() || chatStore.isLoading) return

  const message = currentMessage.value.trim()
  currentMessage.value = ''
  
  try {
    await chatStore.sendMessage(message)
    await scrollToBottom()
  } catch (error) {
    // Error is handled in the store
    console.error('Failed to send message:', error)
  }
}

const selectQuestion = (question: string) => {
  currentMessage.value = question
  textareaRef.value?.focus()
}

const clearChat = () => {
  chatStore.clearChat()
  chatStore.initializeChat()
}

const insertNewline = () => {
  const textarea = textareaRef.value
  if (!textarea) return

  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const value = textarea.value

  currentMessage.value = value.slice(0, start) + '\n' + value.slice(end)
  
  nextTick(() => {
    textarea.selectionStart = textarea.selectionEnd = start + 1
  })
}

const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    const container = messagesContainer.value
    container.scrollTop = container.scrollHeight
  }
}

const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit' 
  })
}

// Auto-scroll when new messages are added
watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick()
    scrollToBottom()
  }
)

// Also scroll when loading state changes
watch(
  () => chatStore.isLoading,
  async () => {
    await nextTick() 
    scrollToBottom()
  }
)

onMounted(() => {
  chatStore.initializeChat()
  scrollToBottom()
})
</script>

<style scoped>
.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  min-height: 0; /* Important for flex child to shrink */
}

.chat-header {
  background: #f8f9fa;
  padding: 16px;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-header h3 {
  margin: 0;
  color: #333;
  font-size: 18px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.session-id {
  font-size: 12px;
  color: #666;
  background: #e9ecef;
  padding: 4px 8px;
  border-radius: 4px;
  font-family: monospace;
}

.clear-btn {
  background: #dc3545;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.clear-btn:hover:not(:disabled) {
  background: #c82333;
}

.clear-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-height: calc(100vh - 200px); /* Ensure scrollable area */
  scroll-behavior: smooth;
}

.message {
  display: flex;
  max-width: 80%;
}

.message.user {
  align-self: flex-end;
}

.message.assistant {
  align-self: flex-start;
}

.message-content {
  background: #f1f3f4;
  padding: 12px 16px;
  border-radius: 18px;
  position: relative;
}

.message.user .message-content {
  background: #007bff;
  color: white;
}

.message-content p {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.timestamp {
  display: block;
  margin-top: 4px;
  opacity: 0.7;
  font-size: 11px;
}

.refinement-questions {
  background: #e3f2fd;
  border: 1px solid #bbdefb;
  border-radius: 8px;
  padding: 16px;
  margin-top: 8px;
}

.refinement-questions h4 {
  margin: 0 0 12px 0;
  color: #1976d2;
  font-size: 14px;
}

.refinement-questions ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.question-item {
  padding: 8px 12px;
  margin: 4px 0;
  background: white;
  border: 1px solid #e3f2fd;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}

.question-item:hover {
  background: #f5f5f5;
  border-color: #2196f3;
}

.loading .message-content {
  background: #f1f3f4;
  padding: 16px;
  border-radius: 18px;
}

.typing-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #007bff;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

.thinking-text {
  color: #666;
  font-style: italic;
  font-size: 14px;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.7;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.error-banner {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.error-banner p {
  margin: 0;
  font-size: 14px;
}

.close-error {
  background: none;
  border: none;
  color: #721c24;
  font-size: 18px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-input {
  border-top: 1px solid #e9ecef;
  padding: 16px;
  background: white;
}

.input-group {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.input-group textarea {
  flex: 1;
  border: 1px solid #ced4da;
  border-radius: 20px;
  padding: 12px 16px;
  resize: none;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.4;
  min-height: 44px;
  max-height: 120px;
}

.input-group textarea:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.input-group textarea:disabled {
  background: #f8f9fa;
  color: #6c757d;
}

.send-btn {
  background: #007bff;
  color: white;
  border: none;
  border-radius: 50%;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: #0056b3;
}

.send-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.input-hints {
  margin-top: 4px;
  text-align: center;
}

.input-hints small {
  color: #6c757d;
  font-size: 12px;
}
</style>
