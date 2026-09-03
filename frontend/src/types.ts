export type ProviderName = "openai" | "deepseek" | "qwen";

export interface ProviderConfig {
  provider: ProviderName;
  base_url: string;
  model: string;
  timeout_seconds: number;
  api_key_configured: boolean;
}

export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  username: string;
  sslmode: string;
  allowed_schemas: string[];
  allowed_tables: string[];
  blocked_columns: string[];
  timeout_seconds: number;
  max_rows: number;
  max_bytes: number;
  password_configured?: boolean;
  password?: string;
}

export interface PlotlySpec {
  data: Plotly.Data[];
  layout: Partial<Plotly.Layout>;
}

export interface QueryResult {
  query_id: string;
  status: string;
  answer?: string;
  sql?: string;
  columns: string[];
  rows: unknown[][];
  chart?: PlotlySpec;
  truncated: boolean;
  error?: string;
}

export interface ProgressEvent {
  type: string;
  query_id: string;
  node?: string;
  message?: string;
  data: Record<string, unknown>;
}
