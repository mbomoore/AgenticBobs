declare module 'cmmn-js' {
  interface CmmnJSOptions {
    container?: HTMLElement | string;
    width?: string | number;
    height?: string | number;
    modules?: any[];
    additionalModules?: any[];
  }

  class CmmnJS {
    constructor(options?: CmmnJSOptions);
    importXML(xml: string): Promise<{ warnings: any[] }>;
    destroy(): void;
    attachTo(parentNode: HTMLElement): void;
    detach(): void;
    on(event: string, callback: (event?: any) => void): void;
    get(name: string): any;
  }

  export default CmmnJS;
}
