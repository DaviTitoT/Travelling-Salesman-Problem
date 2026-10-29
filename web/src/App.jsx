import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, ArrowDownRight, Bike, ChevronDown, CircleHelp, Clock3, Pause, Play, RotateCcw, SkipForward, SlidersHorizontal, Sparkles } from 'lucide-react';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { usePlayback } from './usePlayback';
import './playback.css';
import RouteMap from './RouteMap.jsx';

// Mesmos valores padrão de src/ktsp/pipeline.py e AnnealingParams.
const MAX_K = 40;
const defaults = { city: 'ibirapuita', routeBase: 'selected', seed: 42, saSeed: 0, size: 12, k: 10, initialTemperature: 100, coolingRate: 0.995, maxIterations: 5000, tabuTenure: 0 };
const fmt = (value, digits = 0) => Number(value).toLocaleString('pt-BR', { maximumFractionDigits: digits });

function ComparisonCard({ result, bestCost, selected, unit }) {
  const label = result.strategy === 'random' ? 'Base aleatória' : 'Base escolhida';
  return <article className={`comparison-card${result.bestCost === bestCost ? ' comparison-best' : ''}`}>
    <div className="comparison-title"><strong>{label}</strong><span>Base [{result.base}]</span>{result.strategy === selected && <span>MAPA</span>}</div>
    <div className="comparison-metrics">
      <div><small>Custo inicial</small><strong>{fmt(result.initialCost)} <em>{unit}</em></strong></div>
      <div><small>Melhor custo final</small><strong>{fmt(result.bestCost)} <em>{unit}</em></strong></div>
      <div><small>Melhoria</small><strong>{fmt(result.improvementPct, 1)}<em>%</em></strong></div>
    </div>
  </article>;
}

function Field({ label, value, onChange, min, max, step = 1, suffix }) {
  const digits = step < 1 ? String(step).split('.')[1]?.length ?? 0 : 0;
  return <label className="field"><span>{label}<b>{suffix ? `${fmt(value, 3)}${suffix}` : fmt(value, digits)}</b></span>
    <input type="range" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} />
    <small><i>{fmt(min, digits)}</i><i>{fmt(max, digits)}</i></small>
  </label>;
}

function ChartCard({ title, icon: Icon, data, dataKey, color, domain }) {
  return <section className="chart-card"><div className="chart-title"><span className="icon-chip"><Icon size={16}/></span><h3>{title}</h3></div>
    <div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
      <defs><linearGradient id={`fill-${dataKey}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={0.18}/><stop offset="95%" stopColor={color} stopOpacity={0}/></linearGradient></defs>
      <CartesianGrid stroke="#edf0f3" vertical={false}/><XAxis dataKey="iteration" tickLine={false} axisLine={false} tick={{ fill: '#8993a1', fontSize: 10 }} tickCount={5}/><YAxis domain={domain || ['auto','auto']} tickLine={false} axisLine={false} tick={{ fill: '#8993a1', fontSize: 10 }} tickFormatter={(v) => fmt(v)} width={44}/>
      <Tooltip contentStyle={{ border: '1px solid #e7ebef', borderRadius: 10, fontSize: 12 }} labelFormatter={(v) => `Iteração ${fmt(v)}`} formatter={(v) => [fmt(v, 2), title]}/>
      <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} fill={`url(#fill-${dataKey})`} dot={false} isAnimationActive={false}/>
    </AreaChart></ResponsiveContainer></div>
  </section>;
}

export default function App() {
  const [params, setParams] = useState(defaults);
  const [data, setData] = useState(null);
  const [selectedBase, setSelectedBase] = useState(null);
  const [busy, setBusy] = useState(false);
  const [requestSeconds, setRequestSeconds] = useState(0);
  const [error, setError] = useState('');
  const history = useMemo(() => data?.steps ?? [], [data]);
  const playback = usePlayback(history);
  const { selected, playing, finished } = playback;
  const { pause } = playback;
  const selectBase = useCallback((vertex) => { pause(); setSelectedBase(vertex); }, [pause]);
  const set = (key) => (value) => {
    if (['city', 'size', 'seed'].includes(key)) setSelectedBase(null);
    setParams((old) => {
      const next = { ...old, [key]: value };
      next.k = Math.min(next.k, next.city === 'grid' ? Math.min(MAX_K, next.size ** 2 - 2) : MAX_K);
      return next;
    });
  };
  useEffect(() => {
    if (!busy) return undefined;
    const started = performance.now();
    const timer = window.setInterval(() => setRequestSeconds((performance.now() - started) / 1000), 100);
    return () => window.clearInterval(timer);
  }, [busy]);
  const run = async () => {
    playback.pause();
    setBusy(true); setError(''); setRequestSeconds(0);
    const started = performance.now();
    try {
      const response = await fetch('/api/solve', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(selectedBase !== null ? { ...params, base: selectedBase } : params) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Falha ao executar.');
      setData(result);
      setSelectedBase(result.base);
      playback.restart(result.steps.length > 1);
    }
    catch (err) { setError(`${err.message} Confira se a API Python está em execução.`); }
    finally { setRequestSeconds((performance.now() - started) / 1000); setBusy(false); }
  };
  const step = history[selected] ?? null;
  const chartData = useMemo(() => history.slice(0, selected + 1).map((item) => ({ iteration: item.iteration, current: item.currentCost, best: item.bestCost, temperature: item.temperature })), [history, selected]);
  const improvement = data && step ? ((data.initialCost - step.bestCost) / data.initialCost) * 100 : 0;
  const move = (direction) => playback.seek(selected + direction);
  const baseChanged = data && selectedBase !== null && selectedBase !== data.base;
  const canSelectBase = !busy && data && params.city === data.city && params.seed === data.seed && (data.geographic || params.size === data.size);
  const bestComparisonCost = data ? Math.min(...data.comparisons.map((item) => item.bestCost)) : 0;
  return <div className="layout">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><Bike size={21}/></div><div><strong>RotaLab</strong><small>OTIMIZAÇÃO DE ROTAS</small></div></div>
      <fieldset className="side-section" disabled={busy}><div className="section-heading"><span>CONFIGURAÇÃO</span><SlidersHorizontal size={15}/></div>
        <div className="group-label">Instância da cidade</div>
        <label className="number-field">Cidade <select value={params.city} onChange={(e) => set("city")(e.target.value)}><option value="ibirapuita">Bairro Ibirapuitã</option><option value="grid">Grade sintética</option></select></label>
        <label className="number-field">Semente da cidade <input type="number" min="0" value={params.seed} onChange={(e) => set('seed')(Number(e.target.value))}/></label>
        <label className="number-field">Semente do SA <input type="number" min="0" value={params.saSeed} onChange={(e) => set('saSeed')(Number(e.target.value))}/></label>
        {params.city === 'grid' && <Field label="Tamanho da grade" value={params.size} onChange={set('size')} min={4} max={25} suffix=" × "/>}
        <Field label="Pontos de entrega (k)" value={params.k} onChange={set('k')} min={1} max={params.city === 'grid' ? Math.min(MAX_K, params.size ** 2 - 2) : MAX_K}/>
        <div className="group-label algorithm-label">Simulated Annealing</div>
        <label className="number-field">Base exibida no mapa <select value={params.routeBase ?? 'selected'} onChange={(event) => set('routeBase')(event.target.value)}><option value="selected">Base escolhida</option><option value="random">Base aleatória</option></select></label>
        <small className="comparison-hint">Compara a base escolhida com outra sorteada. Clique em um cruzamento para escolher a primeira.</small>
        {canSelectBase && <label className="number-field">Vértice da base <select value={selectedBase ?? data.base} onChange={(e) => selectBase(Number(e.target.value))}>{data.positions.map((_, vertex) => <option key={vertex} value={vertex}>{vertex}</option>)}</select></label>}
        <Field label="Temperatura inicial" value={params.initialTemperature} onChange={set('initialTemperature')} min={1} max={300} step={1}/>
        <Field label="Resfriamento α" value={params.coolingRate} onChange={set('coolingRate')} min={0.9} max={0.9999} step={0.0001}/>
        <label className="number-field">Orçamento (iterações) <input type="number" min="10" max="200000" step="500" value={params.maxIterations} onChange={(e) => set('maxIterations')(Number(e.target.value))}/></label>
        <label className="number-field">Modo de busca <select value={params.tabuTenure > 0 ? 'hybrid' : 'sa'} onChange={(e) => set('tabuTenure')(e.target.value === 'hybrid' ? 10 : 0)}><option value="sa">SA puro</option><option value="hybrid">SA + Tabu</option></select></label>
        {params.tabuTenure > 0 && <Field label="Lista tabu (movimentos)" value={params.tabuTenure} onChange={set('tabuTenure')} min={1} max={100}/>}
      </fieldset>
      <button className="run-button" onClick={run} disabled={busy}><Play size={16} fill="currentColor"/>{busy ? 'Calculando rota…' : baseChanged ? 'Recalcular com nova base' : 'Executar algoritmo'}</button>
      <div className="sidebar-foot"><span className="status-dot"/> {busy ? `Calculando · ${fmt(requestSeconds, 1)} s` : playing ? 'Reproduzindo a evolução da rota' : 'Algoritmo pronto para executar'}</div>
    </aside>
    <main className="main">
      <header className="topbar"><div><div className="eyebrow">LABORATÓRIO DE ALGORITMOS <span>/</span> k-TSP</div><h1>Planejador de rotas</h1><p>Visualize como o Simulated Annealing encontra uma rota eficiente.</p></div><button className="help-button" title="Sobre o projeto"><CircleHelp size={19}/></button></header>
      {error && <div className="error-banner" role="alert">{error}</div>}
      {busy && <div className="execution-banner" role="status"><Clock3 size={18}/><div><strong>Calculando a rota…</strong><span>A reprodução começa assim que o resultado estiver pronto.</span></div><b>{fmt(requestSeconds, 1)} s</b></div>}
      {!data ? <section className="welcome-card"><div className="welcome-icon"><Sparkles size={24}/></div><h2>Pronto para otimizar?</h2><p>Configure o tamanho da cidade e os parâmetros do algoritmo. A execução vai gerar uma instância reproduzível e buscar uma boa ordem para visitar todas as entregas.</p><button onClick={run} disabled={busy}>{busy ? 'Executando…' : 'Gerar primeira rota'} <Play size={15}/></button><div className="welcome-note"><span/> A busca é uma heurística e não garante o ótimo global.</div></section> : <>
        <div className="summary-row"><div className="summary-card"><span className="summary-icon orange"><Bike size={17}/></span><div><small>ENTREGAS</small><strong>{data.k}<em> pontos</em></strong></div></div><div className="summary-card"><span className="summary-icon blue"><Activity size={17}/></span><div><small>MELHOR DISTÂNCIA</small><strong>{fmt(step?.bestCost ?? data.bestCost)}<em> {data.unit}</em></strong></div></div><div className="summary-card"><span className="summary-icon green"><ArrowDownRight size={17}/></span><div><small>MELHORIA SOBRE INICIAL</small><strong>{fmt(improvement, 1)}<em>%</em></strong></div></div><div className="summary-card"><span className="summary-icon violet"><RotateCcw size={17}/></span><div><small>ORÇAMENTO NECESSÁRIO</small><strong>{fmt(data.foundAt)}<em> de {fmt(data.iterations)} iterações</em></strong></div></div></div>
        <section className="comparison-section"><div className="comparison-heading"><div><div className="card-kicker">MESMA CIDADE, ENTREGAS E PARÂMETROS</div><h2>Comparação das bases</h2></div><p>A base aleatória usa a semente {data.randomSeed}; ambas as rotas começam pelo vizinho mais próximo.</p></div><div className="comparison-grid">{data.comparisons.map((result) => <ComparisonCard key={result.strategy} result={result} bestCost={bestComparisonCost} selected={data.routeBase} unit={data.unit}/>)}</div></section>
        <div className="workspace"><section className="map-card"><div className="card-head"><div><div className="card-kicker">INSTÂNCIA {String(data.seed).padStart(3, '0')} · {data.tabuTenure > 0 ? `SA + TABU (${data.tabuTenure})` : 'SA PURO'}</div><h2>{data.cityName}</h2></div><span className="live-pill"><i/> {busy ? 'CALCULANDO' : playing ? 'REPRODUZINDO' : finished ? 'REPRODUÇÃO CONCLUÍDA' : 'PAUSADO'}</span></div>
          <div className="map-wrap">{step && <RouteMap data={data} step={step} selectedBase={selectedBase} onSelectBase={canSelectBase ? selectBase : undefined}/>}</div>
          {baseChanged && <p className="base-selection-status">Nova base selecionada: vértice {selectedBase}. Execute novamente para recalcular as rotas.</p>}
          <div className="legend"><span><i className="legend-base">B</i> Base exibida</span><span><i className="legend-selected-base">E</i> Base escolhida</span><span><i className="legend-delivery">1</i> Entregas</span><span><i className="legend-line"/> Melhor rota</span><span><i className="legend-dash"/> Rota atual</span>{data.geographic && <span><i className="legend-boundary"/> Limite do bairro</span>}</div>
          <div className="timeline">
            <div><strong>Reprodução da busca</strong><span>Iteração {fmt(step?.iteration ?? 0)} de {fmt(data.iterations)}</span></div>
            <input aria-label="Iteração" aria-valuetext={`Iteração ${step?.iteration ?? 0}`} type="range" min="0" max={Math.max(0, history.length - 1)} value={selected} disabled={busy || history.length < 2} onChange={(e) => playback.seek(Number(e.target.value))}/>
            <div className="playback-meta"><span><Clock3 size={13}/> {fmt(playback.seconds, 1)} / {playback.duration} s</span><span>Temperatura <b>{fmt(step?.temperature ?? 0, 3)}</b></span></div>
            <div className="timeline-actions">
              <button onClick={() => playback.restart(false)} disabled={busy || history.length < 2} aria-label="Voltar ao início" title="Voltar ao início"><RotateCcw size={14}/></button>
              <button onClick={() => move(-1)} disabled={busy || selected === 0} aria-label="Passo anterior">‹</button>
              <button className="animate-button" onClick={playback.toggle} disabled={busy || history.length < 2}>{playing ? <Pause size={13}/> : <Play size={13} fill="currentColor"/>}{playing ? 'Pausar' : finished ? 'Rever' : selected > 0 ? 'Continuar' : 'Reproduzir'}</button>
              <button onClick={() => move(1)} disabled={busy || finished} aria-label="Próximo passo">›</button>
              <button onClick={() => playback.seek(history.length - 1)} disabled={busy || finished} aria-label="Ver resultado final" title="Ver resultado final"><SkipForward size={14}/></button>
              <label className="speed-control">Velocidade<select aria-label="Velocidade de reprodução" value={playback.speed} onChange={(e) => playback.setSpeed(Number(e.target.value))}>{[0.25, 0.5, 1, 2, 4].map((speed) => <option key={speed} value={speed}>{fmt(speed, 2)}×</option>)}</select></label>
            </div>
            <p className="playback-note">Reprodução visual do histórico. A velocidade não altera o algoritmo. Última requisição: {fmt(requestSeconds, 2)} s (API e transferência).</p>
          </div>
        </section><div className="charts-column"><ChartCard title="Custo da rota" icon={Activity} data={chartData} dataKey="current" color="#f07a46"/><ChartCard title="Melhor custo encontrado" icon={Sparkles} data={chartData} dataKey="best" color="#3d80d6"/><ChartCard title="Temperatura" icon={SlidersHorizontal} data={chartData} dataKey="temperature" color="#8b70d5"/></div></div>
        <section className="result-card" aria-label="Resultado final"><div><div className="card-kicker">RESULTADO FINAL DA BUSCA</div><h2>Rota sugerida</h2><p>Melhor rota encontrada nesta execução do algoritmo.</p></div><div className="result-details"><div><small>Distância total</small><strong>{fmt(data.bestCost)} <em>{data.unit}</em></strong></div>{data.optimumCost !== null && <div><small>Ótimo exato (comparação)</small><strong>{fmt(data.optimumCost)} <em>{data.unit}</em></strong></div>}</div><div className="visit-order"><span>ORDEM DE VISITA</span><div>{data.bestVisits.map((visit, index) => <span className="visit-chip" key={`${visit}-${index}`}><b>{index + 1}</b>{visit}</span>)}</div></div><details className="path-details"><summary>Caminho completo por cruzamentos <ChevronDown size={15}/></summary><p>{data.bestVertexPath.join('  →  ')}</p></details></section>
      </>}
      <footer>RotaLab <span>·</span> k-TSP resolvido com Simulated Annealing <span>·</span> Unipampa</footer>
    </main>
  </div>;
}
