import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
  questions?: string[]  // Follow-up questions associated with this message
}

export interface ChatResponse {
  message: string
  session_id: string
  bpmn_xml?: string
  process_type?: 'BPMN' | 'DMN' | 'CMMN' | 'ArchiMate'
  questions: string[]
}

export const useChatStore = defineStore('chat', () => {
  // State
  const messages = ref<ChatMessage[]>([])
  const sessionId = ref<string | null>(null)
  const currentBpmn = ref<string | null>(null)
  const currentProcessType = ref<string | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // API base URL
  const API_BASE = 'http://localhost:8000/api'

  // Computed
  const hasActiveBpmn = computed(() => !!currentBpmn.value)
  const lastMessage = computed(() => messages.value[messages.value.length - 1])

  // Actions
  const sendMessage = async (content: string): Promise<void> => {
    if (!content.trim()) return

    try {
      isLoading.value = true
      error.value = null

      // Add user message to local state immediately
      const userMessage: ChatMessage = {
        role: 'user',
        content: content.trim(),
        timestamp: new Date().toISOString()
      }
      messages.value.push(userMessage)

      // Send to API
      const response = await axios.post<ChatResponse>(`${API_BASE}/chat`, {
        message: content.trim(),
        session_id: sessionId.value
      })

      const data = response.data

      // Update session ID if we got a new one
      if (data.session_id) {
        sessionId.value = data.session_id
      }

      // Update BPMN if provided
      if (data.bpmn_xml) {
        console.log('🎯 Updating BPMN XML:', data.bpmn_xml.substring(0, 100) + '...')
        currentBpmn.value = data.bpmn_xml
        console.log('🎯 Current BPMN is now:', currentBpmn.value ? 'SET' : 'NULL')
      } else {
        console.log('❌ No BPMN XML in response')
      }

      // Update process type if provided
      if (data.process_type) {
        console.log('🎯 Updating process type:', data.process_type)
        currentProcessType.value = data.process_type
      }

      // Add assistant message with questions
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.message,
        timestamp: new Date().toISOString(),
        questions: data.questions || []
      }
      
      // Debug logging
      if (data.questions && data.questions.length > 0) {
        console.log(`✅ Received ${data.questions.length} questions:`, data.questions)
      } else {
        console.log('❌ No questions received in response')
      }
      
      messages.value.push(assistantMessage)

    } catch (err) {
      console.error('Error sending message:', err)
      error.value = 'Failed to send message. Please try again.'
      
      // Remove the user message if the request failed
      if (messages.value[messages.value.length - 1]?.role === 'user') {
        messages.value.pop()
      }
    } finally {
      isLoading.value = false
    }
  }

  const clearChat = (): void => {
    messages.value = []
    sessionId.value = null
    currentBpmn.value = null
    currentProcessType.value = null
    error.value = null
    isLoading.value = false
  }

  const validateBpmn = async (bpmnXml: string) => {
    try {
      const response = await axios.post(`${API_BASE}/validate-bpmn`, {
        bpmn_xml: bpmnXml
      })
      return response.data
    } catch (err) {
      console.error('Error validating BPMN:', err)
      throw err
    }
  }

  const loadSampleBpmn = async (): Promise<void> => {
    try {
      const response = await axios.get(`${API_BASE}/sample-bpmn`)
      currentBpmn.value = response.data.bpmn_xml
    } catch (err) {
      console.error('Error loading sample BPMN:', err)
      error.value = 'Failed to load sample BPMN'
    }
  }

  const deleteSession = async (): Promise<void> => {
    if (!sessionId.value) return

    try {
      await axios.delete(`${API_BASE}/sessions/${sessionId.value}`)
      clearChat()
    } catch (err) {
      console.error('Error deleting session:', err)
      // Still clear local state even if API call fails
      clearChat()
    }
  }

  // Initialize with a welcome message
  const initializeChat = (): void => {
    if (messages.value.length === 0) {
      messages.value.push({
        role: 'assistant',
        content: 'What would you say... you do here?',
        timestamp: new Date().toISOString()
      })
    }
  }

  return {
    // State
    messages,
    sessionId,
    currentBpmn,
    currentProcessType,
    isLoading,
    error,
    
    // Computed
    hasActiveBpmn,
    lastMessage,
    
    // Actions
    sendMessage,
    clearChat,
    validateBpmn,
    loadSampleBpmn,
    deleteSession,
    initializeChat
  }
})
