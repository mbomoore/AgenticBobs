<template>
  <div class="app">
    <header class="app-header">
      <h1>The Bobs 2.0</h1>
      <p class="subtitle">Make a real AI agent that can work for you!</p>
    </header>

    <main class="app-main">
      <div class="layout">
        <!-- Chat Panel -->
        <div class="chat-section">
          <ChatPanel />
        </div>

        <!-- BPMN Viewer Section -->
        <div class="viewer-section">
          <div class="viewer-tabs">
            <button 
              class="tab-button active" 
              @click="activeTab = 'diagram'"
            >
              Process Diagram
            </button>
            <button 
              class="tab-button disabled" 
              disabled
            >
              Process Analysis
            </button>
            <button 
              class="tab-button disabled" 
              disabled
            >
              Agent Prompts
            </button>
          </div>
          
          <div v-show="activeTab === 'diagram'" class="tab-content">
            <div class="viewer-header">
              <div class="viewer-title">
                <h2>Process Diagram</h2>
                <span v-if="chatStore.currentProcessType" class="process-type">
                  {{ chatStore.currentProcessType }}
                </span>
              </div>
              <div class="viewer-controls">
                <button 
                  v-if="chatStore.currentBpmn" 
                  @click="copyXmlToClipboard"
                  class="copy-btn"
                  title="Copy XML to clipboard"
                >
                  📋 Copy XML
                </button>
                <button 
                  v-if="chatStore.currentBpmn" 
                  @click="downloadBpmn"
                  class="download-btn"
                >
                  Download XML
                </button>
              </div>
            </div>
            
            <div class="viewer-container">
              <BpmnViewer 
                :bpmn-xml="chatStore.currentBpmn || undefined"
                @error="handleViewerError"
                @loaded="handleViewerLoaded"
              />
            </div>

            <!-- Validation Status -->
            <div v-if="validationStatus" class="validation-status">
              <div 
                class="status-indicator"
                :class="{ 
                  'valid': validationStatus.is_valid, 
                  'invalid': !validationStatus.is_valid 
                }"
              >
                {{ validationStatus.is_valid ? 'Valid' : 'Invalid' }} BPMN
              </div>
              
              <div v-if="validationStatus.errors.length > 0" class="errors">
                <h4>Errors:</h4>
                <ul>
                  <li v-for="error in validationStatus.errors" :key="error">
                    {{ error }}
                  </li>
                </ul>
              </div>
              
              <div v-if="validationStatus.warnings.length > 0" class="warnings">
                <h4>Warnings:</h4>
                <ul>
                  <li v-for="warning in validationStatus.warnings" :key="warning">
                    {{ warning }}
                  </li>
                </ul>
              </div>
            </div>
          </div>
          
          <div v-show="activeTab === 'analysis'" class="tab-content">
            <div class="coming-soon">
              <h3>Process Analysis</h3>
              <p>Coming soon...</p>
            </div>
          </div>
          
          <div v-show="activeTab === 'prompts'" class="tab-content">
            <div class="coming-soon">
              <h3>Agent Prompts</h3>
              <p>Coming soon...</p>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useChatStore } from './stores/chat'
import ChatPanel from './components/ChatPanel.vue'
import BpmnViewer from './components/BpmnViewer.vue'

const chatStore = useChatStore()
const validationStatus = ref<any>(null)
const activeTab = ref('diagram')

// Watch for BPMN changes and validate
watch(
  () => chatStore.currentBpmn,
  async (newBpmn) => {
    if (newBpmn) {
      try {
        validationStatus.value = await chatStore.validateBpmn(newBpmn)
      } catch (error) {
        console.error('Validation failed:', error)
        validationStatus.value = null
      }
    } else {
      validationStatus.value = null
    }
  }
)

const handleViewerError = (error: string) => {
  console.error('BPMN Viewer Error:', error)
}

const handleViewerLoaded = () => {
  console.log('BPMN diagram loaded successfully')
}

const copyXmlToClipboard = async () => {
  if (!chatStore.currentBpmn) return

  try {
    await navigator.clipboard.writeText(chatStore.currentBpmn)
    // You could add a toast notification here
    console.log('XML copied to clipboard')
  } catch (err) {
    console.error('Failed to copy XML:', err)
    // Fallback for older browsers
    const textArea = document.createElement('textarea')
    textArea.value = chatStore.currentBpmn
    document.body.appendChild(textArea)
    textArea.select()
    try {
      document.execCommand('copy')
      console.log('XML copied to clipboard (fallback)')
    } catch (fallbackErr) {
      console.error('Fallback copy failed:', fallbackErr)
    }
    document.body.removeChild(textArea)
  }
}

const downloadBpmn = () => {
  if (!chatStore.currentBpmn) return

  const blob = new Blob([chatStore.currentBpmn], { type: 'application/xml' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `process-${Date.now()}.bpmn`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f8f9fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-header {
  background: white;
  padding: 20px;
  border-bottom: 1px solid #e9ecef;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.app-header h1 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 28px;
  font-weight: 600;
}

.subtitle {
  margin: 0;
  color: #666;
  font-size: 16px;
  font-style: italic;
}

.app-main {
  flex: 1;
  overflow: hidden;
  padding: 20px;
}

.layout {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 20px;
  height: 100%;
  min-height: 0; /* Important for nested scrolling */
}

.chat-section {
  display: flex;
  flex-direction: column;
  min-height: 0; /* Important for flex child to shrink */
}

.viewer-section {
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.viewer-tabs {
  display: flex;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.tab-button {
  padding: 12px 20px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #666;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
}

.tab-button.active {
  color: #007bff;
  border-bottom-color: #007bff;
  background: white;
}

.tab-button:hover:not(.disabled) {
  color: #007bff;
  background: #f8f9fa;
}

.tab-button.disabled {
  color: #adb5bd;
  cursor: not-allowed;
  opacity: 0.6;
}

.tab-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.viewer-header {
  padding: 16px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.viewer-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.viewer-header h2 {
  margin: 0;
  color: #333;
  font-size: 18px;
  font-weight: 600;
}

.viewer-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.process-type {
  background: #e3f2fd;
  color: #1976d2;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.copy-btn {
  background: #6f42c1;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.copy-btn:hover {
  background: #5a2d91;
}

.download-btn {
  background: #28a745;
  color: white;
  border: none;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.download-btn:hover {
  background: #218838;
}

.coming-soon {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #666;
  text-align: center;
  padding: 40px;
}

.coming-soon h3 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 20px;
}

.coming-soon p {
  margin: 0;
  font-size: 16px;
  color: #999;
}

.viewer-container {
  flex: 1;
  min-height: 0;
}

.validation-status {
  padding: 16px 20px;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
}

.status-indicator {
  padding: 8px 12px;
  border-radius: 4px;
  font-weight: 500;
  font-size: 14px;
  margin-bottom: 12px;
  display: inline-block;
}

.status-indicator.valid {
  background: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.status-indicator.invalid {
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.errors, .warnings {
  margin-top: 12px;
}

.errors h4, .warnings h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
}

.errors h4 {
  color: #721c24;
}

.warnings h4 {
  color: #856404;
}

.errors ul, .warnings ul {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
}

.errors li {
  color: #721c24;
}

.warnings li {
  color: #856404;
}

/* Responsive design */
@media (max-width: 1024px) {
  .layout {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .app-main {
    padding: 10px;
  }
  
  .layout {
    gap: 10px;
  }
  
  .app-header {
    padding: 15px 10px;
  }
  
  .app-header h1 {
    font-size: 24px;
  }
  
  .subtitle {
    font-size: 14px;
  }
}
</style>
