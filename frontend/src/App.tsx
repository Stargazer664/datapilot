import { BarChart3, ChevronDown, CircleStop, Copy, Database, Download, Play, Settings2, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import Plot from "react-plotly.js";
import { api } from "./api";
import SettingsPanel from "./SettingsPanel";
import type { ProgressEvent, ProviderConfig, ProviderName, QueryResult } from "./types";

const agentLabels: Record<string, string> = { coordinator: "理解问题", schema: "定位数据", sql: "生成 SQL", review: "安全审查", execute: "执行查询", analysis: "分析结果", visualization: "生成图表", workflow: "汇总答案" };
const examples = ["过去 12 个月每月销售额趋势", "销售额最高的 10 个产品", "各区域客户复购率对比"];

export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [provider, setProvider] = useState<ProviderName>("openai");
  const [question, setQuestion] = useState("");
  const [queryId, setQueryId] = useState("");
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState("");
  const running = Boolean(queryId && !result);
  const activeModel = providers.find((item) => item.provider === provider)?.model;

  useEffect(() => {
    Promise.all([api.createSession(), api.getSettings()]).then(([session, settings]) => {
      setSessionId(session.id); setProviders(settings.providers); setProvider(settings.default_provider);
      if (!settings.database || !settings.providers.some((item) => item.api_key_configured)) setSettingsOpen(true);
    }).catch((value: Error) => setError(value.message));
  }, []);

  async function submit(text = question) {
    if (!text.trim() || !sessionId || running) return;
    setQuestion(text); setError(""); setEvents([]); setResult(null);
    try {
      const accepted = await api.createQuery({ session_id: sessionId, question: text.trim(), provider, model: activeModel });
      setQueryId(accepted.query_id);
      const stream = new EventSource(`/api/queries/${accepted.query_id}/events`);
      stream.onmessage = () => undefined;
      const eventNames = ["agent_started", "agent_completed", "agent_failed", "waiting_for_clarification", "workflow_completed", "workflow_failed", "cancelled"];
      eventNames.forEach((name) => stream.addEventListener(name, async (raw) => {
        const progress = JSON.parse((raw as MessageEvent).data) as ProgressEvent;
        setEvents((items) => [...items, progress]);
        if (["workflow_completed", "workflow_failed", "waiting_for_clarification", "cancelled"].includes(name)) {
          stream.close(); const completed = await api.getQuery(accepted.query_id); setResult(completed);
        }
      }));
      stream.onerror = () => { stream.close(); api.getQuery(accepted.query_id).then(setResult).catch(() => setError("进度连接中断")); };
    } catch (value) { setError((value as Error).message); }
  }

  async function cancel() { if (queryId) await api.cancelQuery(queryId); }
  const progress = useMemo(() => [...new Map(events.filter(e => e.node).map(e => [e.node, e])).values()], [events]);

  return <div className="app-shell">
    <header className="topbar"><div className="brand-mark"><BarChart3/><span>DataPilot</span><em>LOCAL</em></div><div className="top-actions"><button className="connection-chip" onClick={() => setSettingsOpen(true)}><span className="live-dot"/> PostgreSQL <ChevronDown size={15}/></button><button className="icon-button" onClick={() => setSettingsOpen(true)} aria-label="打开设置"><Settings2/></button></div></header>
    <main>
      <section className="hero"><p className="eyebrow">MULTI-AGENT ANALYTICS</p><h1>把问题交给数据，<br/><span>让答案自己浮现。</span></h1><p>六个专业 Agent 协作完成理解、查询、审查、分析与可视化。数据库始终保持只读。</p></section>
      <section className="workspace-card">
        <div className="model-row"><span><Sparkles size={16}/> 当前模型</span><select value={provider} onChange={(e) => setProvider(e.target.value as ProviderName)}>{providers.map((item) => <option key={item.provider} value={item.provider}>{item.provider.toUpperCase()} · {item.model}</option>)}</select></div>
        <div className="composer"><textarea value={question} onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} placeholder="问一个关于数据的问题，例如：过去 12 个月销售额如何变化？"/><button className={running ? "stop-button" : "send-button"} onClick={running ? cancel : () => submit()}>{running ? <CircleStop/> : <Play/>}<span>{running ? "停止" : "分析"}</span></button></div>
        {!result && !running && <div className="examples">{examples.map((item) => <button key={item} onClick={() => submit(item)}>{item}</button>)}</div>}
      </section>
      {(running || progress.length > 0) && <section className="progress-strip"><div className="section-heading"><span>Agent 执行轨迹</span><small>{running ? "运行中" : "已完成"}</small></div><div className="agent-grid">{progress.map((event, index) => <div className={`agent-step ${event.type === "agent_completed" ? "done" : event.type.includes("failed") ? "failed" : "active"}`} key={`${event.node}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><div><strong>{agentLabels[event.node ?? ""] ?? event.node}</strong><small>{event.message}</small></div></div>)}</div></section>}
      {error && <div className="error-card">{error}</div>}
      {result && <section className="results-grid"><article className="answer-card"><p className="eyebrow">ANALYSIS</p><h2>分析结论</h2><p className="answer-text">{result.answer ?? result.error}</p>{result.truncated && <div className="warning">结果已按安全限制截断。</div>}</article>
        {result.chart && <article className="chart-card"><div className="section-heading"><span>可视化</span><small>Plotly</small></div><Plot data={result.chart.data} layout={{ ...result.chart.layout, autosize: true, paper_bgcolor: "transparent", plot_bgcolor: "transparent", font: { color: "#d7e0dc", family: "Manrope Variable" } }} useResizeHandler style={{ width: "100%", height: "380px" }} config={{ displaylogo: false, responsive: true }}/></article>}
        {result.sql && <article className="sql-card"><div className="section-heading"><span>执行 SQL</span><button onClick={() => navigator.clipboard.writeText(result.sql ?? "")}><Copy size={15}/> 复制</button></div><pre>{result.sql}</pre></article>}
        {result.columns.length > 0 && <article className="table-card"><div className="section-heading"><span>查询结果</span><a href={`/api/queries/${result.query_id}/export.csv`}><Download size={15}/> CSV</a></div><div className="table-scroll"><table><thead><tr>{result.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{result.rows.slice(0, 100).map((row, rowIndex) => <tr key={rowIndex}>{row.map((value, cellIndex) => <td key={cellIndex}>{String(value ?? "—")}</td>)}</tr>)}</tbody></table></div></article>}
      </section>}
    </main>
    <footer><span><Database size={14}/> READ-ONLY CONNECTION</span><span>数据不会写入目标数据库</span></footer>
    <SettingsPanel open={settingsOpen} onClose={() => setSettingsOpen(false)} onConfigured={setProviders}/>
  </div>;
}
