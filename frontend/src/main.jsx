import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, ArrowUpRight, CheckCircle2, FileCheck2, LayoutDashboard, RefreshCw, ShieldAlert, Upload, XCircle } from 'lucide-react';
import './styles.css';

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const PAGES = ['Dashboard', 'Analyze', 'Emissions', 'Records', 'Compliance'];

function pageFromHash() {
  const value = window.location.hash.replace(/^#\/?/, '').toLowerCase();
  return PAGES.find(page => page.toLowerCase() === value) || 'Dashboard';
}

function App() {
  const [view, setView] = useState(pageFromHash);
  const [analysis, setAnalysis] = useState(null);
  const [selected, setSelected] = useState(null);
  const [agentMode, setAgentMode] = useState('CHECKING');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const loadDashboard = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await fetch(`${API}/api/dashboard`);
      if (!response.ok) throw new Error(`Dashboard request failed (${response.status})`);
      const data = await response.json();
      setAnalysis(data);
      setSelected(data.records[0] || null);
    } catch (requestError) {
      setError(requestError.message || 'Unable to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
    fetch(`${API}/health`).then(response => response.json()).then(data => setAgentMode(data.agent_mode || 'UNKNOWN')).catch(() => setAgentMode('BACKEND_UNAVAILABLE'));
    const handleHashChange = () => setView(pageFromHash());
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const upload = async event => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const body = new FormData();
      body.append('file', file);
      const response = await fetch(`${API}/api/upload`, { method: 'POST', body });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || `Upload failed (${response.status})`);
      setAnalysis(data);
      setSelected(data.records[0] || null);
      setPage('Records');
    } catch (uploadError) {
      setError(uploadError.message || 'Unable to analyze this file.');
    } finally {
      setUploading(false);
      event.target.value = '';
    }
  };

  const records = analysis?.records || [];
  const verified = records.filter(record => record.status === 'VERIFIED');
  const summary = analysis?.summary || {};
  const claims = analysis?.claims || [];
  const findings = records.filter(record => record.status !== 'VERIFIED');
  const setPage = page => { window.location.hash = `/${page.toLowerCase()}`; setView(page); setError(''); };

  return <div className="app-shell">
    <Sidebar view={view} setView={setPage} agentMode={agentMode} />
    <main>
      <header><div><p className="eyebrow">SUSTAINABILITY CONTROL ROOM</p><h1>{view === 'Dashboard' ? 'Portfolio overview' : view}</h1></div><div className="header-actions"><button className="ghost" onClick={loadDashboard} disabled={loading}><RefreshCw size={16} /> Refresh</button><label className="primary"><Upload size={16} /> {uploading ? 'Analyzing...' : 'Analyze file'}<input type="file" accept=".csv,.xlsx,.xlsm,.txt,.pdf" onChange={upload} disabled={uploading} /></label></div></header>
      {error && <div className="notice error-notice"><span><XCircle size={17} /></span><div><strong>Action could not be completed</strong><p>{error}</p></div></div>}
      {loading ? <section className="panel state-panel"><RefreshCw className="spin" size={22} /><strong>Loading backend evidence...</strong><p>Retrieving the current analysis and audit records.</p></section> : !analysis ? <section className="panel state-panel"><ShieldAlert size={22} /><strong>No backend analysis available</strong><p>Check the API and refresh this workspace.</p></section> : <>
        {analysis.records.some(record => record.factor_source === 'TEST_ONLY') && <section className="notice"><span><ShieldAlert size={17} /></span><div><strong>Development evidence mode</strong><p>Factor rows are labelled TEST_ONLY and are not suitable for external reporting.</p></div></section>}
        {view === 'Dashboard' && <Dashboard summary={summary} records={records} claims={claims} setView={setPage} />}
        {view === 'Analyze' && <Analyze uploading={uploading} />}
        {view === 'Emissions' && <Emissions records={verified} summary={summary} />}
        {view === 'Records' && <Records records={records} selected={selected} setSelected={setSelected} />}
        {view === 'Compliance' && <Compliance records={findings} claims={claims} />}
        <AuditExplorer selected={selected || verified[0]} />
      </>}
    </main>
  </div>;
}

function Sidebar({ view, setView, agentMode }) { return <aside className="sidebar"><div className="brand"><span className="brand-mark"><Activity size={18} /></span><span>CarbonAudit <em>AI</em></span></div><div className="workspace-label">WORKSPACE / BACKEND DATA</div><nav>{['Dashboard', 'Analyze', 'Emissions', 'Records', 'Compliance'].map(item => <button className={view === item ? 'nav-item active' : 'nav-item'} onClick={() => setView(item)} key={item}>{item === 'Dashboard' ? <LayoutDashboard size={17} /> : item === 'Analyze' ? <Upload size={17} /> : item === 'Compliance' ? <ShieldAlert size={17} /> : <FileCheck2 size={17} />}{item}</button>)}</nav><div className="sidebar-bottom"><div className="agent-status"><span className={`pulse ${agentMode === 'LYZR_LIVE' ? '' : 'fallback'}`} />{agentMode === 'LYZR_LIVE' ? 'Lyzr agent live' : agentMode === 'CHECKING' ? 'Checking agent' : 'Local deterministic mode'}<div>{agentMode === 'LYZR_LIVE' ? 'Tool calling enabled' : 'No Lyzr execution'}</div></div><div className="profile"><span>AN</span><div>Analyst workspace<small>Backend session</small></div></div></div></aside>; }

function Dashboard({ summary, records, claims, setView }) { const scopes = [['Scope 1', summary.scope_1_kg_co2e || 0], ['Scope 2', summary.scope_2_kg_co2e || 0], ['Scope 3', summary.scope_3_kg_co2e || 0]]; const total = summary.total_kg_co2e || 0; return <><section className="metrics"><Metric label="Total CO2e" value={`${total.toLocaleString()} kg`} detail="Across verified records" accent="mint" /><Metric label="Scope 1" value={`${scopes[0][1].toLocaleString()} kg`} detail="Direct emissions" /><Metric label="Scope 2" value={`${scopes[1][1].toLocaleString()} kg`} detail="Purchased energy" /><Metric label="Scope 3" value={`${scopes[2][1].toLocaleString()} kg`} detail="Value chain" /></section><div className="content-grid"><section className="panel emissions-panel"><PanelHead eyebrow="INVENTORY MIX" title="Emissions by scope" /><div className="scope-bars">{scopes.map((item, index) => <div className="scope-row" key={item[0]}><div className="scope-label"><span className={`scope-dot d${index}`} />{item[0]}<strong>{item[1].toLocaleString()} kg</strong></div><div className="bar-track"><div className={`bar-fill b${index}`} style={{ width: `${Math.max((item[1] / Math.max(total, 1)) * 100, 3)}%` }} /></div></div>)}</div><div className="panel-foot"><span><CheckCircle2 size={15} /> {summary.verified_records || 0} verified records</span><span><XCircle size={15} /> {(summary.needs_review || 0) + (summary.missing_factors || 0)} need attention</span></div></section><ReviewQueue summary={summary} claims={claims} setView={setView} /></div><Records records={records} compact setSelected={() => {}} /></>; }
function Analyze({ uploading }) { return <section className="panel state-panel"><Upload size={22} /><strong>{uploading ? 'Analysis in progress' : 'Upload activity data'}</strong><p>Use Analyze file above to submit CSV, XLSX, or PDF activity data to the backend pipeline.</p></section>; }
function Emissions({ records, summary }) { return <section className="panel"><PanelHead eyebrow="CALCULATED INVENTORY" title="Verified emissions" /><p className="subtle">{records.length ? `${summary.total_kg_co2e.toLocaleString()} kg CO2e from deterministic calculations.` : 'No verified emission records are available.'}</p><Records records={records} compact setSelected={() => {}} /></section>; }
function Records({ records, selected, setSelected, compact = false }) { return <section className={`panel records-panel ${compact ? 'compact-panel' : ''}`}><div className="panel-head"><div><p className="eyebrow">TRACEABLE INVENTORY</p><h2>{compact ? 'Recent records' : 'Records'}</h2></div>{compact && <span className="period">Backend data</span>}</div>{records.length ? <div className="table-wrap"><table><thead><tr><th>Activity</th><th>Scope</th><th>Source</th><th>Impact</th><th>Status</th></tr></thead><tbody>{records.map(record => <tr key={record.record_id} onClick={() => setSelected(record)} className={selected?.record_id === record.record_id ? 'selected-row' : ''}><td><strong>{record.activity}</strong><small>Row {record.source_row || '—'}{record.source_page ? ` · Page ${record.source_page}` : ''} · {record.quantity} {record.unit}</small></td><td>{record.scope || 'Unclassified'}</td><td>{record.source_document}</td><td>{record.result_kg_co2e != null ? `${record.result_kg_co2e.toLocaleString()} kg` : '—'}</td><td><Status status={record.status} /></td></tr>)}</tbody></table></div> : <Empty text="No records available." />}</section>; }
function Compliance({ records, claims }) { return <section className="panel"><PanelHead eyebrow="COMPLIANCE REVIEW" title="Review queue" /><div className="review-list">{claims.map(claim => <div className="check" key={claim.claim}><span className="check-icon danger"><ShieldAlert size={16} /></span><div><strong>{claim.status}: {claim.claim}</strong><p>{claim.explanation}</p></div></div>)}{records.map(record => <div className="check" key={record.record_id}><span className="check-icon warning"><ShieldAlert size={16} /></span><div><strong>{record.status}: {record.activity}</strong><p>{record.message || 'Record requires evidence review.'}</p></div></div>)}{!claims.length && !records.length && <Empty text="No compliance findings." />}</div></section>; }
function ReviewQueue({ summary, claims, setView }) { const issues = (summary.missing_factors || 0) + (summary.needs_review || 0); return <section className="panel review-panel"><PanelHead eyebrow="CONTROL CHECKS" title="Review queue" /><div className="check"><span className="check-icon warning"><ShieldAlert size={16} /></span><div><strong>Records needing review</strong><p>{issues} record(s) require evidence</p></div><b>{issues}</b></div><div className="check"><span className="check-icon danger"><XCircle size={16} /></span><div><strong>Unsupported claims</strong><p>{claims.length ? `${claims.length} claim(s) reviewed` : 'No claims submitted'}</p></div><b>{claims.length}</b></div><div className="review-link" onClick={() => setView('Compliance')}>Open compliance review <ArrowUpRight size={15} /></div></section>; }
function AuditExplorer({ selected }) { return <section className="audit-layout"><div><p className="eyebrow">AUDIT EXPLORER</p><h2>Evidence chain</h2><p className="subtle">Select a record to inspect its calculation lineage.</p></div>{selected ? <div className="audit-chain">{[['Source', `${selected.source_document} · row ${selected.source_row}${selected.source_page ? ` · page ${selected.source_page}` : ''}`], ['Activity', selected.activity], ['Scope', selected.scope || 'Needs classification'], ['Quantity', `${selected.quantity} ${selected.unit}`], ['Factor', selected.factor != null ? `${selected.factor} kg CO2e / ${selected.normalized_unit || selected.unit}` : 'Not available'], ['Formula', selected.formula || 'Calculation blocked'], ['Result', selected.result_kg_co2e != null ? `${selected.result_kg_co2e} kg CO2e` : 'Needs review'], ['Status', selected.status]].map(([label, value], index) => <div className="audit-step" key={label}><span className="step-number">{String(index + 1).padStart(2, '0')}</span><div><small>{label}</small><strong>{value}</strong></div>{index < 7 && <span className="connector" />}</div>)}</div> : <Empty text="No audit evidence available." />}</section>; }
function PanelHead({ eyebrow, title }) { return <div className="panel-head"><div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div></div>; }
function Metric({ label, value, detail, accent }) { return <div className={`metric ${accent || ''}`}><p>{label}</p><strong>{value}</strong><span>{detail}</span></div>; }
function Status({ status }) { return <span className={`status ${status.toLowerCase()}`}>{status === 'VERIFIED' && <CheckCircle2 size={13} />}{status === 'NOT_FOUND' && <XCircle size={13} />}{status.replace('_', ' ')}</span>; }
function Empty({ text }) { return <p className="subtle empty-state">{text}</p>; }

createRoot(document.getElementById('root')).render(<App />);
