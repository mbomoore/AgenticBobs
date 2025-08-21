declare module 'bpmn-auto-layout' {
  export function layoutProcess(bpmnXml: string): Promise<string>
}
