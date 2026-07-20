declare module "plotly.js-dist-min";
declare module "react-plotly.js/factory" {
  import type * as React from "react";
  const createPlotlyComponent: (plotly: unknown) => React.ComponentType<{
    data: unknown[];
    layout?: Record<string, unknown>;
    config?: Record<string, unknown>;
    style?: React.CSSProperties;
    useResizeHandler?: boolean;
  }>;
  export default createPlotlyComponent;
}
