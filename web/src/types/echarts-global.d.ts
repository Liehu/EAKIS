declare namespace echarts {
  interface ECharts {
    setOption(option: any, notMerge?: boolean): void;
    resize(): void;
    dispose(): void;
    on(event: string, handler: (params: any) => void): void;
    off(event: string, handler?: (params: any) => void): void;
  }

  interface EChartsOption {
    [key: string]: any;
  }
}
