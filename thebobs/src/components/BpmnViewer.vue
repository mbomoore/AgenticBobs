<template>
  <div class="bpmn-viewer-container">
    <div 
      ref="bpmnContainer" 
      class="bpmn-canvas"
      :class="{ 'loading': isLoading }"
    >
      <div v-if="isLoading" class="loading-overlay">
        <div class="loading-content">
          <div class="loading-spinner"></div>
          <p>Thinking about your process...</p>
          <small>This may take a few moments</small>
        </div>
      </div>
      <div v-if="error" class="error-overlay">
        <div class="error-content">
          <div class="error-icon">⚠️</div>
          <h4>Process Loading Error</h4>
          <div class="error-details">
            <p class="error-message">{{ error }}</p>
            <details v-if="errorDetails" class="error-details-expand">
              <summary>View Details</summary>
              <pre class="error-stack">{{ errorDetails }}</pre>
            </details>
          </div>
          <div class="error-actions">
            <button @click="retryLoad" class="retry-btn">Retry</button>
            <button @click="clearError" class="clear-btn">Dismiss</button>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="!bpmnXml && !isLoading && !error" class="empty-state">
      <div class="empty-content">
        <div class="empty-icon">📊</div>
        <h3>No Process Diagram</h3>
        <p>Start a conversation with Bob to generate a process diagram</p>
        <button @click="loadSample" class="load-sample-btn">Load Sample BPMN</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import BpmnJS from 'bpmn-js'
import CmmnJS from 'cmmn-js'
import { useChatStore } from '../stores/chat'

const props = defineProps<{
  bpmnXml?: string
}>()

const emit = defineEmits<{
  error: [message: string]
  loaded: []
}>()

const bpmnContainer = ref<HTMLElement>()
const isLoading = ref(false)
const error = ref<string | null>(null)
const errorDetails = ref<string | null>(null)
const viewer = ref<BpmnJS | any | null>(null)

const chatStore = useChatStore()

const initializeViewer = () => {
  if (!bpmnContainer.value) return

  try {
    // Get the process type from the chat store
    const processType = chatStore.currentProcessType
    console.log('Initializing viewer for process type:', processType)
    
    // Choose the appropriate viewer based on process type
    if (processType === 'CMMN') {
      console.log('Creating CMMN viewer')
      try {
        viewer.value = new CmmnJS({
          container: bpmnContainer.value,
          width: '100%',
          height: '100%'
        })
        console.log('CMMN viewer created successfully')
      } catch (cmmnError: any) {
        console.warn('CMMN viewer failed, falling back to BPMN:', cmmnError)
        // Fallback to BPMN viewer if CMMN fails
        viewer.value = new BpmnJS({
          container: bpmnContainer.value,
          width: '100%',
          height: '100%'
        })
      }
    } else {
      // Default to BPMN viewer for BPMN, DMN, ArchiMate, and unknown types
      console.log('Creating BPMN viewer for process type:', processType || 'default')
      viewer.value = new BpmnJS({
        container: bpmnContainer.value,
        width: '100%',
        height: '100%'
      })
    }
    
    // Add error handling for viewer internal errors
    viewer.value.on('import.render.complete', () => {
      console.log(`${processType || 'BPMN'} diagram rendered successfully`)
    })
    
    viewer.value.on('error', (event: any) => {
      console.error(`${processType || 'BPMN'} viewer error:`, event.error)
      error.value = `${processType || 'BPMN'} viewer error: ${event.error.message || 'Unknown error'}`
      errorDetails.value = event.error.stack || JSON.stringify(event.error, null, 2)
      emit('error', error.value)
    })
    
  } catch (err: any) {
    console.error('Failed to initialize viewer:', err)
    error.value = `Failed to initialize viewer: ${err.message || 'Unknown error'}`
    errorDetails.value = err.stack || JSON.stringify(err, null, 2)
    emit('error', error.value)
  }
}

const loadBpmn = async (xml: string) => {
  if (!viewer.value || !xml) return

  try {
    console.log('🚀 loadBpmn called with XML length:', xml.length)
    console.log('🚀 XML preview:', xml.substring(0, 300) + '...')
    
    isLoading.value = true
    error.value = null
    errorDetails.value = null

    // Since layout is now handled on the backend, we can directly import the XML
    console.log('Importing XML with backend layout processing')
    await viewer.value.importXML(xml)
    console.log('✅ XML import successful')
    
    // Enhanced zoom and centering
    await nextTick() // Wait for DOM to update
    
    try {
      const canvas = viewer.value.get('canvas') as any
      
      // First zoom to fit viewport with padding
      canvas.zoom('fit-viewport', 'auto')
      
      // Add some padding and center with a slight delay to ensure layout is complete
      setTimeout(() => {
        canvas.zoom('fit-viewport', { x: 20, y: 20, width: -40, height: -40 })
        console.log('Applied enhanced zoom-to-fit with padding and centering')
      }, 150)
      
    } catch (zoomError: any) {
      console.warn('Zoom enhancement failed:', zoomError)
      // Fallback to basic zoom
      try {
        const canvas = viewer.value.get('canvas') as any
        canvas.zoom('fit-viewport')
      } catch (fallbackError: any) {
        console.warn('Fallback zoom also failed:', fallbackError)
      }
    }
    
    emit('loaded')
  } catch (err: any) {
    console.error('Failed to load BPMN:', err)
    const errorMessage = err.message || 'Failed to load BPMN diagram'
    error.value = errorMessage
    errorDetails.value = err.stack || JSON.stringify(err, null, 2)
    emit('error', errorMessage)
  } finally {
    isLoading.value = false
  }
}

const retryLoad = () => {
  if (props.bpmnXml) {
    loadBpmn(props.bpmnXml)
  }
}

const clearError = () => {
  error.value = null
  errorDetails.value = null
}

const loadSample = async () => {
  try {
    await chatStore.loadSampleBpmn()
  } catch (err) {
    error.value = 'Failed to load sample BPMN'
  }
}

// Watch for changes in bpmnXml prop
watch(
  () => props.bpmnXml,
  async (newXml) => {
    console.log('🔍 BpmnViewer - XML prop changed:', newXml ? 'XML RECEIVED' : 'NO XML')
    if (newXml) {
      console.log('🔍 BpmnViewer - XML length:', newXml.length)
      console.log('🔍 BpmnViewer - XML preview:', newXml.substring(0, 200) + '...')
    }
    
    if (newXml && viewer.value) {
      await nextTick() // Ensure DOM is updated
      loadBpmn(newXml)
    } else if (!newXml && viewer.value) {
      // Clear the diagram when bpmnXml is null/undefined
      try {
        console.log('Clearing diagram')
        await viewer.value.clear()
        error.value = null
        errorDetails.value = null
      } catch (clearError: any) {
        console.warn('Failed to clear diagram:', clearError)
      }
    }
  },
  { immediate: false }
)

// Watch for changes in process type to reinitialize viewer
watch(
  () => chatStore.currentProcessType,
  async (newProcessType, oldProcessType) => {
    if (newProcessType !== oldProcessType && newProcessType) {
      // Destroy old viewer if it exists
      if (viewer.value) {
        try {
          console.log('Destroying old viewer')
          viewer.value.destroy()
        } catch (destroyError: any) {
          console.warn('Error destroying viewer:', destroyError)
        }
        viewer.value = null
      }
      // Reinitialize with new viewer type
      await nextTick()
      initializeViewer()
      // Reload XML if we have it
      if (props.bpmnXml) {
        loadBpmn(props.bpmnXml)
      }
    }
  },
  { immediate: false }
)

// Watch for chat store loading state to show viewer loading
watch(
  () => chatStore.isLoading,
  (loading) => {
    if (loading && !props.bpmnXml) {
      // Show loading state when chat is loading and we don't have existing BPMN
      isLoading.value = true
    } else if (!loading && isLoading.value && !props.bpmnXml) {
      // Hide loading if chat stopped loading but we still don't have BPMN
      isLoading.value = false
    }
  }
)

onMounted(async () => {
  await nextTick()
  initializeViewer()
  
  if (props.bpmnXml) {
    loadBpmn(props.bpmnXml)
  }
})

onUnmounted(() => {
  if (viewer.value) {
    viewer.value.destroy()
  }
})
</script>

<style scoped>
.bpmn-viewer-container {
  width: 100%;
  height: 100%;
  position: relative;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f5f5;
}

.bpmn-canvas {
  width: 100%;
  height: 100%;
  position: relative;
}

.bpmn-canvas.loading {
  pointer-events: none;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 10;
  backdrop-filter: blur(2px);
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.loading-overlay p {
  margin: 0;
  font-size: 16px;
  color: #333;
  font-weight: 500;
}

.loading-overlay small {
  color: #666;
  font-size: 14px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.error-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: white;
  border: 2px solid #dc3545;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  z-index: 10;
  max-width: 80%;
  max-height: 80%;
  overflow-y: auto;
  box-shadow: 0 4px 12px rgba(220, 53, 69, 0.2);
}

.error-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.error-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.error-content h4 {
  color: #dc3545;
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.error-details {
  text-align: left;
  width: 100%;
}

.error-message {
  color: #721c24;
  margin: 0 0 12px 0;
  font-size: 14px;
  background: #f8d7da;
  padding: 12px;
  border-radius: 6px;
  border: 1px solid #f5c6cb;
}

.error-details-expand {
  margin-top: 12px;
}

.error-details-expand summary {
  cursor: pointer;
  color: #dc3545;
  font-weight: 500;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  border: 1px solid #dee2e6;
}

.error-details-expand summary:hover {
  background: #e9ecef;
}

.error-stack {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 4px;
  padding: 12px;
  margin: 8px 0 0 0;
  font-size: 12px;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.retry-btn {
  background: #dc3545;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.retry-btn:hover {
  background: #c82333;
}

.clear-btn {
  background: #6c757d;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.clear-btn:hover {
  background: #5a6268;
}

.empty-state {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #666;
  padding: 40px;
}

.empty-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.empty-icon {
  font-size: 64px;
  opacity: 0.5;
}

.empty-content h3 {
  margin: 0;
  font-size: 24px;
  color: #333;
  font-weight: 600;
}

.empty-content p {
  margin: 0;
  font-size: 16px;
  color: #666;
  max-width: 300px;
  line-height: 1.5;
}

.load-sample-btn {
  background: #3498db;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.load-sample-btn:hover {
  background: #2980b9;
}

/* BPMN.js specific styles */
:deep(.djs-container) {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

:deep(.djs-element) {
  cursor: pointer;
}

:deep(.djs-shape) {
  fill: #fff;
  stroke: #000;
  stroke-width: 1;
}

:deep(.djs-connection) {
  stroke: #000;
  stroke-width: 1;
  fill: none;
}

:deep(.djs-shape.highlight) {
  stroke: #3498db;
  stroke-width: 2;
}

/* Hide event labels (start/end event names) */
:deep(.djs-shape[data-element-id*="Event"] + .djs-label),
:deep(.djs-label[data-element-id*="Event"]) {
  display: none;
}

/* Improve text appearance without forcing positioning */
:deep(.djs-label) {
  font-size: 12px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Better task label styling */
:deep(.djs-shape[data-element-id*="Task"] .djs-label) {
  font-size: 11px;
  font-weight: 500;
}

/* Gateway labels */
:deep(.djs-shape[data-element-id*="Gateway"] .djs-label) {
  font-size: 10px;
  font-weight: 500;
}
</style>
