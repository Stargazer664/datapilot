import { Check, Database, KeyRound, LoaderCircle, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { DatabaseConfig, ProviderConfig, ProviderName } from "./types";

const emptyDatabase: DatabaseConfig = {
  host: "localhost", port: 5432, database: "", username: "analytics_reader", password: "",
  sslmode: "prefer", allowed_schemas: ["public"], allowed_tables: [], blocked_columns: [],
  timeout_seconds: 30, max_rows: 1000, max_bytes: 5242880,
};

interface Props { open: boolean; onClose: () => void; onConfigured: (providers: ProviderConfig[]) => void }

export default function SettingsPanel({ open, onClose, onConfigured }: Props) {
  const [database, setDatabase] = useState(emptyDatabase);
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!open) return;
    api.getSettings().then((value) => {
      if (value.database) setDatabase({ ...value.database, password: "" });
      setProviders(value.providers);
    }).catch((error: Error) => setNotice(error.message));
  }, [open]);

  if (!open) return null;
  const field = (key: keyof DatabaseConfig, label: string, type = "text") => (
    <label><span>{label}</span><input type={type} value={String(database[key] ?? "")}
      onChange={(event) => setDatabase({ ...database, [key]: type === "number" ? Number(event.target.value) : event.target.value })} /></label>
  );

  async function saveDatabase() {
    setBusy("database"); setNotice("");
    try { await api.testDatabase(database); await api.saveDatabase(database); setNotice("数据库连接已验证并保存"); }
    catch (error) { setNotice((error as Error).message); } finally { setBusy(""); }
  }

  async function saveProvider(provider: ProviderConfig) {
    setBusy(provider.provider); setNotice("");
    const payload = { api_key: keys[provider.provider] || undefined, base_url: provider.base_url, model: provider.model, timeout_seconds: provider.timeout_seconds };
    try { await api.testProvider(provider.provider, payload); await api.saveProvider(provider.provider, payload); setNotice(`${provider.provider} 已连接`); const next = (await api.getSettings()).providers; setProviders(next); onConfigured(next); }
    catch (error) { setNotice((error as Error).message); } finally { setBusy(""); }
  }

  function updateProvider(name: ProviderName, patch: Partial<ProviderConfig>) {
    setProviders((items) => items.map((item) => item.provider === name ? { ...item, ...patch } : item));
  }

  return <div className="settings-backdrop" role="dialog" aria-modal="true" aria-label="连接设置">
    <aside className="settings-panel">
      <header><div><p className="eyebrow">LOCAL CONFIGURATION</p><h2>连接设置</h2></div><button className="icon-button" onClick={onClose} aria-label="关闭设置"><X /></button></header>
      <section><h3><Database size={18}/> PostgreSQL</h3><div className="form-grid">{field("host", "主机")}{field("port", "端口", "number")}{field("database", "数据库")}{field("username", "用户名")}{field("password", database.password_configured ? "密码（留空保持不变）" : "密码", "password")}{field("timeout_seconds", "超时（秒）", "number")}</div>
        <label><span>允许的 Schema（逗号分隔）</span><input value={database.allowed_schemas.join(", ")} onChange={(e) => setDatabase({ ...database, allowed_schemas: e.target.value.split(",").map(v => v.trim()).filter(Boolean) })}/></label>
        <button className="primary-button" onClick={saveDatabase} disabled={!!busy}>{busy === "database" ? <LoaderCircle className="spin"/> : <Check/>} 测试并保存</button>
      </section>
      <section><h3><KeyRound size={18}/> 模型供应商</h3>{providers.map((provider) => <div className="provider-card" key={provider.provider}>
        <div className="provider-title"><strong>{provider.provider.toUpperCase()}</strong><span className={provider.api_key_configured ? "status good" : "status"}>{provider.api_key_configured ? "已配置" : "未配置"}</span></div>
        <div className="form-grid"><label><span>模型</span><input value={provider.model} onChange={(e) => updateProvider(provider.provider, { model: e.target.value })}/></label><label><span>API Key</span><input type="password" placeholder={provider.api_key_configured ? "留空保持不变" : "sk-..."} value={keys[provider.provider] ?? ""} onChange={(e) => setKeys({ ...keys, [provider.provider]: e.target.value })}/></label></div>
        <label><span>Base URL</span><input value={provider.base_url} onChange={(e) => updateProvider(provider.provider, { base_url: e.target.value })}/></label>
        <button className="secondary-button" onClick={() => saveProvider(provider)} disabled={!!busy}>{busy === provider.provider ? <LoaderCircle className="spin"/> : <Check/>} 测试连接</button>
      </div>)}</section>
      {notice && <div className="notice">{notice}</div>}
    </aside>
  </div>;
}
