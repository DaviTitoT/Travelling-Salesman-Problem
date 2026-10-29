import { useEffect, useMemo, useState } from 'react';
import { Activity, ArrowDownRight, Bike, ChevronDown, CircleHelp, Play, RotateCcw, SlidersHorizontal, Sparkles } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import RouteMap from './RouteMap.jsx';

// Mesmos valores padrão de src/ktsp/pipeline.py e AnnealingParams.
// A cidade é a exceção: a interface abre no bairro real; a CLI usa a grade.
const defaults = { city: 'ibirapuita', seed: 42, saSeed: 0, size: 12, k: 10, initialTemperature: 100, coolingRate: 0.995, maxIterations: 5000, tabuTenure: 0 };
const MAX_K = 40;
const fmt = (value, digits = 0) => Number(value).toLocaleString('pt-BR', { maximumFractionDigits: digits });

function Field({ label, value, onChange, min, max, step = 1, suffix }) {
  return <label className="field"><span>{label}<b>{suffix ? `${fmt(value, 3)}${suffix}` : fmt(value)}</b></span>
    <input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    <small><i>{fmt(min, step < 1 ? 3 : 0)}</i><i>{fmt(max, step < 1 ? 3 : 0)}</i></small>
  </label>;
}

function ChartCard({ title, icon: Icon, data, dataKey, color, domain }) {
  return <section className="chart-card"><div className="chart-title"><span className="icon-chip"><Icon size={16}/></span><h3>{title}</h3></div>
    <div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
      <defs><linearGradient id={`fill-${dataKey}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={0.18}/><stop offset="95%" stopColor={color} stopOpacity={0}/></linearGradient></defs>
      <CartesianGrid stroke="#edf0f3" vertical={false}/><XAxis dataKey="iteration" tickLine={false} axisLine={false} tick={{ fill: '#8993a1', fontSize: 10 }} tickCount={5}/><YAxis domain={domain || ['auto','auto']} tickLine={false} axisLine={false} tick={{ fill: '#8993a1', fontSize: 10 }} tickFormatter={(v) => fmt(v)} width={44}/>
      <Tooltip contentStyle={{ border: '1px solid #e7ebef', borderRadius: 10, fontSize: 12 }} labelFormatter={(v) => `Iteração ${fmt(v)}`} formatter={(v) => [fmt(v, 2), title]}/>
      <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} fill={`url(#fill-${dataKey})`} dot={false}/>
    </AreaChart></ResponsiveContainer></div>
  </section>;
}

export default function App() {
  const [params, setParams] = useState(defaults);
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(0);
  const [busy, setBusy] = useState(false);
  const [animate, setAnimate] = useState(false);
  const [error, setError] = useState('');
  const set = (key) => (value) => setParams((old) => ({ ...old, [key]: value }));
  const run = async () => {
    setBusy(true); setError('');
    try { const response = await fetch('/api/solve', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(params) }); const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Falha ao executar.'); setData(result); setSelected(result.steps.length - 1); }
    catch (err) { setError(`${err.message} Confira se a API Python está em execução.`); }
    finally { setBusy(false); }
  };
  const history = data?.steps ?? [];
  const step = history[selected] ?? null;
  const chartData = useMemo(() => history.map((item) => ({ iteration: item.iteration, current: item.currentCost, best: item.bestCost, temperature: item.temperature })), [history]);
  useEffect(() => {
    if (!animate || history.length === 0) return undefined;
    const timer = window.setInterval(() => setSelected((index) => Math.min(index + 1, history.length - 1)), 35);
    return () => window.clearInterval(timer);
  }, [animate, history.length]);
  useEffect(() => {
    if (animate && history.length > 0 && selected >= history.length - 1) setAnimate(false);
  }, [animate, history.length, selected]);
  const improvement = data ? ((data.initialCost - data.bestCost) / data.initialCost) * 100 : 0;
  const move = (direction) => setSelected((index) => Math.max(0, Math.min(history.length - 1, index + direction)));
  return <div className="layout">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><Bike size={21}/></div><div><strong>RotaLab</strong><small>OTIMIZAÇÃO DE ROTAS</small></div></div>
      <div className="side-section"><div className="section-heading"><span>CONFIGURAÇÃO</span><SlidersHorizontal size={15}/></div>
        <div className="group-label">Instância da cidade</div>
        <label className="number-field">Cidade <select value={params.city} onChange={(e) => set('city')(e.target.value)}><option value="ibirapuita">Bairro Ibirapuitã</option><option value="grid">Grade sintética</option></select></label>
        <label className="number-field">Semente da cidade <input type="number" min="0" value={params.seed} onChange={(e) => set('seed')(Number(e.target.value))}/></label>
        <label className="number-field">Semente do SA <input type="number" min="0" value={params.saSeed} onChange={(e) => set('saSeed')(Number(e.target.value))}/></label>
        {params.city === 'grid' && <Field label="Tamanho da grade" value={params.size} onChange={set('size')} min={4} max={25} suffix=" × "/>}
        <Field label="Pontos de entrega (k)" value={params.k} onChange={set('k')} min={1} max={params.city === 'grid' ? Math.min(MAX_K, params.size ** 2 - 1) : MAX_K}/>
        <div className="group-label algorithm-label">Simulated Annealing</div>
        <Field label="Temperatura inicial" value={params.initialTemperature} onChange={set('initialTemperature')} min={1} max={300} step={1}/>
        <Field label="Resfriamento α" value={params.coolingRate} onChange={set('coolingRate')} min={0.9} max={0.9999} step={0.0001}/>
        <label className="number-field">Orçamento (iterações) <input type="number" min="10" max="200000" step="500" value={params.maxIterations} onChange={(e) => set('maxIterations')(Number(e.target.value))}/></label>
        <label className="number-field">Modo de busca <select value={params.tabuTenure > 0 ? 'hybrid' : 'sa'} onChange={(e) => set('tabuTenure')(e.target.value === 'hybrid' ? 10 : 0)}><option value="sa">SA puro</option><option value="hybrid">SA + Tabu</option></select></label>
        {params.tabuTenure > 0 && <Field label="Lista tabu (movimentos)" value={params.tabuTenure} onChange={set('tabuTenure')} min={1} max={100}/>}
      </div>
      <button className="run-button" onClick={run} disabled={busy}><Play size={16} fill="currentColor"/>{busy ? 'Calculando rota…' : 'Executar algoritmo'}</button>
      <div className="sidebar-foot"><span className="status-dot"/> Algoritmo pronto para executar</div>
    </aside>
    <main className="main">
      <header className="topbar"><div><div className="eyebrow">LABORATÓRIO DE ALGORITMOS <span>/</span> k-TSP</div><h1>Planejador de rotas</h1><p>Visualize como o Simulated Annealing encontra uma rota eficiente.</p></div><button className="help-button" title="Sobre o projeto"><CircleHelp size={19}/></button></header>
      {error && <div className="error-banner">{error}</div>}
      {!data ? <section className="welcome-card"><div className="welcome-icon"><Sparkles size={24}/></div><h2>Pronto para otimizar?</h2><p>Configure o tamanho da cidade e os parâmetros do algoritmo. A execução vai gerar uma instância reproduzível e buscar uma boa ordem para visitar todas as entregas.</p><button onClick={run} disabled={busy}>{busy ? 'Executando…' : 'Gerar primeira rota'} <Play size={15}/></button><div className="welcome-note"><span/> A busca é uma heurística e não garante o ótimo global.</div></section> : <>
        <div className="summary-row"><div className="summary-card"><span className="summary-icon orange"><Bike size={17}/></span><div><small>ENTREGAS</small><strong>{data.k}<em> pontos</em></strong></div></div><div className="summary-card"><span className="summary-icon blue"><Activity size={17}/></span><div><small>MELHOR DISTÂNCIA</small><strong>{fmt(data.bestCost)}<em> {data.unit}</em></strong></div></div><div className="summary-card"><span className="summary-icon green"><ArrowDownRight size={17}/></span><div><small>MELHORIA SOBRE INICIAL</small><strong>{fmt(improvement, 1)}<em>%</em></strong></div></div><div className="summary-card"><span className="summary-icon violet"><RotateCcw size={17}/></span><div><small>ORÇAMENTO NECESSÁRIO</small><strong>{fmt(data.foundAt)}<em> de {fmt(data.iterations)} iterações</em></strong></div></div></div>
        <div className="workspace"><section className="map-card"><div className="card-head"><div><div className="card-kicker">INSTÂNCIA {String(data.seed).padStart(3, '0')} · {data.tabuTenure > 0 ? `SA + TABU (${data.tabuTenure})` : 'SA PURO'}</div><h2>{data.cityName}</h2></div><span className="live-pill"><i/> {step?.temperature < 0.05 ? 'BUSCA CONCLUÍDA' : 'HISTÓRICO DA BUSCA'}</span></div>
          <div className="map-wrap">{step && <RouteMap data={data} step={step}/>}</div>
          <div className="legend"><span><i className="legend-base">B</i> Base</span><span><i className="legend-delivery">1</i> Entregas</span><span><i className="legend-line"/> Melhor rota</span><span><i className="legend-dash"/> Rota atual</span>{data.geographic && <span><i className="legend-boundary"/> Limite do bairro</span>}</div>
          <div className="timeline"><div><strong>Reprodução da busca</strong><span>Iteração {fmt(step?.iteration ?? 0)} de {fmt(data.iterations)}</span></div><input aria-label="Iteração" type="range" min="0" max={history.length - 1} value={selected} onChange={(e) => setSelected(Number(e.target.value))}/><div className="timeline-actions"><button onClick={() => move(-1)} aria-label="Passo anterior">‹</button><button className="animate-button" onClick={() => { setAnimate(!animate); if (!animate) setSelected(0); }}><Play size={13} fill="currentColor"/>{animate ? 'Pausar' : 'Reproduzir'}</button><button onClick={() => move(1)} aria-label="Próximo passo">›</button><span>Temperatura <b>{fmt(step?.temperature ?? 0, 3)}</b></span></div></div>
        </section><div className="charts-column"><ChartCard title="Custo da rota" icon={Activity} data={chartData} dataKey="current" color="#f07a46"/><ChartCard title="Melhor custo encontrado" icon={Sparkles} data={chartData} dataKey="best" color="#3d80d6"/><ChartCard title="Temperatura" icon={SlidersHorizontal} data={chartData} dataKey="temperature" color="#8b70d5"/></div></div>
        <section className="result-card"><div><div className="card-kicker">RESULTADO DA BUSCA</div><h2>Rota sugerida</h2><p>Melhor rota encontrada nesta execução do algoritmo.</p></div><div className="result-details"><div><small>Distância total</small><strong>{fmt(data.bestCost)} <em>{data.unit}</em></strong></div>{data.optimumCost !== null && <div><small>Ótimo exato (comparação)</small><strong>{fmt(data.optimumCost)} <em>{data.unit}</em></strong></div>}</div><div className="visit-order"><span>ORDEM DE VISITA</span><div>{data.bestVisits.map((visit, index) => <span className="visit-chip" key={`${visit}-${index}`}><b>{index + 1}</b>{visit}</span>)}</div></div><details className="path-details"><summary>Caminho completo por cruzamentos <ChevronDown size={15}/></summary><p>{data.bestVertexPath.join('  →  ')}</p></details></section>
      </>}
      <footer>RotaLab <span>·</span> k-TSP resolvido com Simulated Annealing <span>·</span> Unipampa</footer>
    </main>
  </div>;
}
