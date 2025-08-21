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
          <p>Loading BPMN diagram...</p>
          <small>This may take a few moments</small>
        </div>
      </div>
      <div v-if="error" class="error-overlay">
        <div class="error-content">
          <div class="error-icon">⚠️</div>
          <h4>BPMN Loading Error</h4>
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
import { layoutProcess } from 'bpmn-auto-layout'
import { useChatStore } from '../stores/chat'

// Helper function to create horizontal layout
function createHorizontalLayout(xml: string): string {
  console.log('Creating horizontal layout...')
  
  const parser = new DOMParser()
  const doc = parser.parseFromString(xml, 'text/xml')
  
  // Find process elements and sequence flows
  const process = doc.querySelector('process')
  if (!process) return xml
  
  const startEvents = Array.from(process.querySelectorAll('startEvent'))
  const tasks = Array.from(process.querySelectorAll('task'))
  const gateways = Array.from(process.querySelectorAll('exclusiveGateway'))
  const endEvents = Array.from(process.querySelectorAll('endEvent'))
  const sequenceFlows = Array.from(process.querySelectorAll('sequenceFlow'))
  
  // Build flow graph to determine order
  const flowMap = new Map()
  sequenceFlows.forEach(flow => {
    const source = flow.getAttribute('sourceRef')
    const target = flow.getAttribute('targetRef')
    if (source && target) {
      if (!flowMap.has(source)) flowMap.set(source, [])
      flowMap.get(source).push(target)
    }
  })
  
  // Start with start events and follow the flow
  const layoutOrder: Array<{id: string, level: number}> = []
  const visited = new Set<string>()
  
  function traverse(elementId: string, level: number = 0) {
    if (visited.has(elementId)) return
    visited.add(elementId)
    
    layoutOrder.push({ id: elementId, level })
    
    const targets = flowMap.get(elementId) || []
    targets.forEach((target: string) => traverse(target, level + 1))
  }
  
  // Start traversal from start events
  startEvents.forEach(start => traverse(start.getAttribute('id')!))
  
  // Add any remaining elements
  const allElements = [...tasks, ...gateways, ...endEvents]
  allElements.forEach((el: any) => {
    const id = el.getAttribute('id')!
    if (!visited.has(id)) {
      layoutOrder.push({ id, level: layoutOrder.length })
    }
  })
  
  console.log('Layout order:', layoutOrder)
  
  // Create or update BPMNDiagram
  let bpmnDiagram = doc.querySelector('bpmndi\\:BPMNDiagram, BPMNDiagram')
  if (!bpmnDiagram) {
    const definitionsElement = doc.documentElement
    bpmnDiagram = doc.createElementNS('http://www.omg.org/spec/BPMN/20100524/DI', 'bpmndi:BPMNDiagram')
    bpmnDiagram.setAttribute('id', 'BPMNDiagram_' + process.getAttribute('id'))
    definitionsElement.appendChild(bpmnDiagram)
  }
  
  let bpmnPlane = bpmnDiagram.querySelector('bpmndi\\:BPMNPlane, BPMNPlane')
  if (!bpmnPlane) {
    bpmnPlane = doc.createElementNS('http://www.omg.org/spec/BPMN/20100524/DI', 'bpmndi:BPMNPlane')
    bpmnPlane.setAttribute('id', 'BPMNPlane_' + process.getAttribute('id'))
    bpmnPlane.setAttribute('bpmnElement', process.getAttribute('id')!)
    bpmnDiagram.appendChild(bpmnPlane)
  } else {
    // Clear existing shapes and edges
    bpmnPlane.innerHTML = ''
  }
  
  // Layout parameters
  const startX = 50
  const startY = 50  
  const horizontalSpacing = 200
  const verticalSpacing = 100
  
  // Group elements by level for better layout
  const levelGroups = new Map<number, string[]>()
  layoutOrder.forEach(item => {
    if (!levelGroups.has(item.level)) levelGroups.set(item.level, [])
    levelGroups.get(item.level)!.push(item.id)
  })
  
  const elementPositions = new Map<string, {x: number, y: number, width: number, height: number}>()
  
  // Position elements horizontally by level
  levelGroups.forEach((elementIds, level) => {
    elementIds.forEach((elementId: string, indexInLevel: number) => {
      const x = startX + (level * horizontalSpacing)
      const y = startY + (indexInLevel * verticalSpacing)
      
      // Get element type to determine dimensions
      const element = doc.getElementById(elementId)
      let width = 100, height = 80
      
      if (element?.tagName === 'startEvent' || element?.tagName === 'endEvent') {
        width = height = 36
      } else if (element?.tagName === 'exclusiveGateway') {
        width = height = 50
      }
      
      // Store position with actual dimensions for edge calculations
      elementPositions.set(elementId, { x, y, width, height })
      
      // Create BPMNShape
      const shape = doc.createElementNS('http://www.omg.org/spec/BPMN/20100524/DI', 'bpmndi:BPMNShape')
      shape.setAttribute('id', elementId + '_di')
      shape.setAttribute('bpmnElement', elementId)
      
      const bounds = doc.createElementNS('http://www.omg.org/spec/DD/20100524/DC', 'dc:Bounds')
      bounds.setAttribute('x', x.toString())
      bounds.setAttribute('y', y.toString())
      bounds.setAttribute('width', width.toString())
      bounds.setAttribute('height', height.toString())
      
      shape.appendChild(bounds)
      bpmnPlane.appendChild(shape)
    })
  })
  
  console.log('Horizontal layout positions:', Object.fromEntries(elementPositions))
  
  // Add edges
  sequenceFlows.forEach(flow => {
    const flowId = flow.getAttribute('id')!
    const sourceRef = flow.getAttribute('sourceRef')!
    const targetRef = flow.getAttribute('targetRef')!
    
    const sourcePos = elementPositions.get(sourceRef)
    const targetPos = elementPositions.get(targetRef)
    
    if (sourcePos && targetPos) {
      const edge = doc.createElementNS('http://www.omg.org/spec/BPMN/20100524/DI', 'bpmndi:BPMNEdge')
      edge.setAttribute('id', flowId + '_di')
      edge.setAttribute('bpmnElement', flowId)
      
      // Create waypoints for proper connection points
      const waypoint1 = doc.createElementNS('http://www.omg.org/spec/DD/20100524/DI', 'di:waypoint')
      const waypoint2 = doc.createElementNS('http://www.omg.org/spec/DD/20100524/DI', 'di:waypoint')
      
      // Calculate proper exit point (right edge center of source)
      const sourceExitX = sourcePos.x + sourcePos.width
      const sourceExitY = sourcePos.y + (sourcePos.height / 2)
      
      // Calculate proper entry point (left edge center of target)
      const targetEntryX = targetPos.x
      const targetEntryY = targetPos.y + (targetPos.height / 2)
      
      waypoint1.setAttribute('x', sourceExitX.toString())
      waypoint1.setAttribute('y', sourceExitY.toString())
      waypoint2.setAttribute('x', targetEntryX.toString())
      waypoint2.setAttribute('y', targetEntryY.toString())
      
      edge.appendChild(waypoint1)
      edge.appendChild(waypoint2)
      bpmnPlane.appendChild(edge)
      
      console.log(`Added edge ${flowId}: (${sourceExitX},${sourceExitY}) -> (${targetEntryX},${targetEntryY})`)
    }
  })
  
  const result = new XMLSerializer().serializeToString(doc)
  console.log('Created horizontal layout with', layoutOrder.length, 'elements')
  return result
}
function addMissingEdges(xml: string): string {
  console.log('Adding missing BPMNEdge elements...')
  
  // Parse the XML to find sequence flows and shapes
  const parser = new DOMParser()
  const doc = parser.parseFromString(xml, 'text/xml')
  
  // Find all sequence flows
  const sequenceFlows = doc.querySelectorAll('sequenceFlow')
  const shapes = doc.querySelectorAll('bpmndi\\:BPMNShape, BPMNShape')
  
  console.log(`Found ${sequenceFlows.length} sequence flows and ${shapes.length} shapes`)
  
  if (sequenceFlows.length === 0) {
    console.log('No sequence flows found, returning original XML')
    return xml
  }
  
  // Find the BPMNPlane element where we'll add edges
  const bpmnPlane = doc.querySelector('bpmndi\\:BPMNPlane, BPMNPlane')
  if (!bpmnPlane) {
    console.log('No BPMNPlane found, returning original XML')
    return xml
  }
  
  // Create a map of element positions from existing shapes
  const shapePositions = new Map()
  shapes.forEach(shape => {
    const bpmnElement = shape.getAttribute('bpmnElement')
    const bounds = shape.querySelector('dc\\:Bounds, Bounds')
    if (bpmnElement && bounds) {
      const x = parseFloat(bounds.getAttribute('x') || '0')
      const y = parseFloat(bounds.getAttribute('y') || '0')
      const width = parseFloat(bounds.getAttribute('width') || '0')
      const height = parseFloat(bounds.getAttribute('height') || '0')
      shapePositions.set(bpmnElement, { 
        x: x + width / 2, 
        y: y + height / 2,
        width,
        height
      })
    }
  })
  
  console.log('Shape positions:', Object.fromEntries(shapePositions))
  
  // Check layout direction by analyzing positions
  const positions = Array.from(shapePositions.values())
  if (positions.length > 1) {
    const xSpread = Math.max(...positions.map(p => p.x)) - Math.min(...positions.map(p => p.x))
    const ySpread = Math.max(...positions.map(p => p.y)) - Math.min(...positions.map(p => p.y))
    console.log(`Layout analysis: X-spread=${xSpread}, Y-spread=${ySpread}`)
    console.log(`Layout appears to be: ${xSpread > ySpread ? 'horizontal' : 'vertical'}`)
  }
  
  // Add BPMNEdge for each sequence flow
  sequenceFlows.forEach(flow => {
    const flowId = flow.getAttribute('id')
    const sourceRef = flow.getAttribute('sourceRef')
    const targetRef = flow.getAttribute('targetRef')
    
    if (!flowId || !sourceRef || !targetRef) return
    
    const sourcePos = shapePositions.get(sourceRef)
    const targetPos = shapePositions.get(targetRef)
    
    if (!sourcePos || !targetPos) {
      console.log(`Missing positions for flow ${flowId}: ${sourceRef} -> ${targetRef}`)
      return
    }
    
    // Create BPMNEdge element
    const edge = doc.createElementNS('http://www.omg.org/spec/BPMN/20100524/DI', 'bpmndi:BPMNEdge')
    edge.setAttribute('id', `${flowId}_di`)
    edge.setAttribute('bpmnElement', flowId)
    
    // Create waypoints for the edge (improved routing)
    const waypoint1 = doc.createElementNS('http://www.omg.org/spec/DD/20100524/DI', 'di:waypoint')
    const waypoint2 = doc.createElementNS('http://www.omg.org/spec/DD/20100524/DI', 'di:waypoint')
    
    // Calculate exit and entry points based on element positions
    let sourceX = sourcePos.x
    let sourceY = sourcePos.y
    let targetX = targetPos.x
    let targetY = targetPos.y
    
    // Adjust source exit point (right side of source element)
    if (sourcePos.width) {
      sourceX = sourcePos.x + sourcePos.width / 2
    }
    
    // Adjust target entry point (left side of target element)  
    if (targetPos.width) {
      targetX = targetPos.x - targetPos.width / 2
    }
    
    waypoint1.setAttribute('x', sourceX.toString())
    waypoint1.setAttribute('y', sourceY.toString())
    waypoint2.setAttribute('x', targetX.toString())
    waypoint2.setAttribute('y', targetY.toString())
    
    edge.appendChild(waypoint1)
    edge.appendChild(waypoint2)
    bpmnPlane.appendChild(edge)
    
    console.log(`Added edge for ${flowId}: (${sourceX},${sourceY}) -> (${targetX},${targetY})`)
  })
  
  // Serialize back to string
  const serializer = new XMLSerializer()
  const result = serializer.serializeToString(doc)
  
  console.log(`Added ${sequenceFlows.length} BPMNEdge elements`)
  return result
}

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
const viewer = ref<BpmnJS | null>(null)

const chatStore = useChatStore()

const initializeViewer = () => {
  if (!bpmnContainer.value) return

  try {
    viewer.value = new BpmnJS({
      container: bpmnContainer.value,
      width: '100%',
      height: '100%'
    })
    
    // Add error handling for BPMN.js internal errors
    viewer.value.on('import.render.complete', () => {
      console.log('BPMN diagram rendered successfully')
    })
    
    viewer.value.on('error', (event: any) => {
      console.error('BPMN.js error:', event.error)
      error.value = `BPMN.js error: ${event.error.message || 'Unknown error'}`
      errorDetails.value = event.error.stack || JSON.stringify(event.error, null, 2)
      emit('error', error.value)
    })
    
  } catch (err: any) {
    console.error('Failed to initialize BPMN viewer:', err)
    error.value = `Failed to initialize BPMN viewer: ${err.message || 'Unknown error'}`
    errorDetails.value = err.stack || JSON.stringify(err, null, 2)
    emit('error', error.value)
  }
}

const loadBpmn = async (xml: string) => {
  if (!viewer.value || !xml) return

  try {
    isLoading.value = true
    error.value = null
    errorDetails.value = null

    // Check if the BPMN has layout information (more comprehensive check)
    const hasLayout = xml.includes('bpmndi:BPMNShape') || xml.includes('bpmndi:BPMNEdge') || xml.includes('di:waypoint')
    
    let processedXml = xml
    
    console.log('BPMN Layout Check:', {
      hasShape: xml.includes('bpmndi:BPMNShape'),
      hasEdge: xml.includes('bpmndi:BPMNEdge'), 
      hasWaypoint: xml.includes('di:waypoint'),
      hasLayout: hasLayout,
      xmlLength: xml.length
    })
    
    // If no layout information, use bpmn-auto-layout to add it
    if (!hasLayout) {
      console.log('No layout information found...')
      console.log('Trying bpmn-js native import first (it might auto-layout)')
      
      // First try: Let bpmn-js handle the layout natively
      try {
        await viewer.value!.importXML(xml)
        console.log('bpmn-js handled layout natively - checking result...')
        
        // Check if bpmn-js added any layout info
        const elementRegistry = viewer.value!.get('elementRegistry') as any
        const elements = elementRegistry.getAll()
        
        console.log('Elements found after native import:', elements.length)
        console.log('Element types:', elements.map((el: any) => `${el.id}: ${el.type}`))
        
        // Check if sequence flows are visible
        const sequenceFlows = elements.filter((el: any) => el.type === 'bpmn:SequenceFlow')
        console.log('Sequence flows found:', sequenceFlows.length)
        
        if (sequenceFlows.length > 0) {
          console.log('Success! bpmn-js handled layout natively')
          isLoading.value = false
          error.value = null
          errorDetails.value = null
          return
        }
      } catch (nativeError: any) {
        console.log('bpmn-js native import failed, trying auto-layout...', nativeError.message)
      }
      
      // Second try: Use our custom horizontal layout
      console.log('Creating custom horizontal layout...')
      try {
        processedXml = createHorizontalLayout(xml)
        console.log('Custom horizontal layout applied successfully, new length:', processedXml.length)
        
        // Check layout results
        const hasShapeAfter = processedXml.includes('bpmndi:BPMNShape')
        const hasEdgeAfter = processedXml.includes('bpmndi:BPMNEdge')
        const hasWaypointAfter = processedXml.includes('di:waypoint')
        
        console.log('Custom layout check:', {
          hasShapeAfter,
          hasEdgeAfter,
          hasWaypointAfter,
          xmlLength: processedXml.length
        })
        
        const shapeCount = (processedXml.match(/bpmndi:BPMNShape/g) || []).length
        const edgeCount = (processedXml.match(/bpmndi:BPMNEdge/g) || []).length
        const waypointCount = (processedXml.match(/di:waypoint/g) || []).length
        
        console.log(`Custom layout results: ${shapeCount} shapes, ${edgeCount} edges, ${waypointCount} waypoints`)
        
      } catch (layoutError: any) {
        console.error('Custom horizontal layout failed:', layoutError)
        error.value = `Layout failed: ${layoutError.message || 'Unknown error'}`
        errorDetails.value = layoutError.stack || JSON.stringify(layoutError, null, 2)
        return
      }
    } else {
      console.log('Layout information detected, using original XML')
    }

    await viewer.value.importXML(processedXml)
    
    // Enhanced zoom and centering
    await nextTick() // Wait for DOM to update
    
    try {
      const canvas = viewer.value.get('canvas') as any
      
      // First zoom to fit viewport
      canvas.zoom('fit-viewport', 'auto')
      
      // Add some padding and center
      setTimeout(() => {
        canvas.zoom('fit-viewport', true)
        console.log('Applied enhanced zoom-to-fit with centering')
      }, 100)
      
    } catch (zoomError: any) {
      console.warn('Zoom enhancement failed:', zoomError)
      // Fallback to basic zoom
      const canvas = viewer.value.get('canvas') as any
      canvas.zoom('fit-viewport')
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
    if (newXml && viewer.value) {
      await nextTick() // Ensure DOM is updated
      loadBpmn(newXml)
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
</style>
