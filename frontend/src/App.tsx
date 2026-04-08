import { useState, useEffect, useCallback } from 'react'

type Signal = {
  name: string; epic: string; yahoo: string; market_type: string;
  current_price: number; signal_type: string; composite_score: number;
  confidence: number; confluence: number; rsi: number; adx: number;
  regime: string; timeframe_scores: Record<string, number>;
  reasons: string[]; has_breakout: boolean; has_volume_spike: boolean;
  has_patterns: boolean; has_divergence: boolean;
  news_score: number; news_sentiment: string; session_status: string;
  sparkline: number[]; support: number; resistance: number; atr: number;
  indicators: Record<string, any>;
  candlestick_patterns: Array<{name: string; type: string; confidence: number}>;
  chart_patterns: Array<{name: string; type: string; confidence: number}>;
  news_headlines: Array<{title: string; sentiment: number; impact: string}>;
  trade_rating?: string;
}

type ScanData = {
  timestamp: string; scan_mode: string; total_instruments: number;
  signals_found: number; buy_signals: number; sell_signals: number;
  signals: Signal[];
}

type TradeRec = {
  direction: string; signal: string; trade_rating: string; rating_score: number;
  confidence: number; entry_type: string; entry_price: number; stop_loss: number;
  take_profit_1: number; take_profit_2: number; take_profit_3: number;
  stop_distance: number; position_size: number; position_value: number;
  risk_amount: number; rr_ratio: number; spread_estimate: number;
}

const S = {
  app: { minHeight: '100vh', background: '#0a0e17' } as React.CSSProperties,
  header: { background: '#111827', padding: '16px 24px', borderBottom: '1px solid #1f2937', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' as const, gap: 12 } as React.CSSProperties,
  title: { fontSize: 22, fontWeight: 700, color: '#f9fafb', margin: 0 } as React.CSSProperties,
  subtitle: { fontSize: 13, color: '#6b7280', margin: 0 } as React.CSSProperties,
  btn: (bg: string) => ({ background: bg, color: '#fff', border: 'none', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 600 } as React.CSSProperties),
  btnOutline: { background: 'transparent', color: '#9ca3af', border: '1px solid #374151', padding: '8px 16px', borderRadius: 6, cursor: 'pointer', fontSize: 13 } as React.CSSProperties,
  controls: { display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' as const } as React.CSSProperties,
  tabs: { display: 'flex', gap: 0, borderBottom: '1px solid #1f2937', padding: '0 24px' } as React.CSSProperties,
  tab: (active: boolean) => ({ padding: '12px 20px', cursor: 'pointer', borderBottom: active ? '2px solid #3b82f6' : '2px solid transparent', color: active ? '#3b82f6' : '#6b7280', fontWeight: active ? 600 : 400, fontSize: 14 } as React.CSSProperties),
  content: { padding: 24 } as React.CSSProperties,
  card: { background: '#111827', borderRadius: 8, border: '1px solid #1f2937', overflow: 'hidden' } as React.CSSProperties,
  table: { width: '100%', borderCollapse: 'collapse' as const, fontSize: 13 } as React.CSSProperties,
  th: { padding: '10px 12px', textAlign: 'left' as const, borderBottom: '1px solid #1f2937', color: '#6b7280', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' as const, letterSpacing: 0.5, cursor: 'pointer', whiteSpace: 'nowrap' as const } as React.CSSProperties,
  td: { padding: '10px 12px', borderBottom: '1px solid #111827', verticalAlign: 'middle' as const } as React.CSSProperties,
  tr: (i: number) => ({ background: i % 2 === 0 ? '#111827' : '#0f1520', cursor: 'pointer' } as React.CSSProperties),
  badge: (color: string) => ({ display: 'inline-block', padding: '2px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700, color: '#fff', background: color, whiteSpace: 'nowrap' as const } as React.CSSProperties),
  marketBadge: (t: string) => ({ display: 'inline-block', padding: '2px 6px', borderRadius: 3, fontSize: 10, fontWeight: 600, color: '#9ca3af', background: '#1f2937', textTransform: 'uppercase' as const } as React.CSSProperties),
  statsRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 20 } as React.CSSProperties,
  statCard: { background: '#111827', border: '1px solid #1f2937', borderRadius: 8, padding: 16 } as React.CSSProperties,
  statLabel: { fontSize: 11, color: '#6b7280', textTransform: 'uppercase' as const, letterSpacing: 0.5, marginBottom: 4 } as React.CSSProperties,
  statValue: (color?: string) => ({ fontSize: 24, fontWeight: 700, color: color || '#f9fafb' } as React.CSSProperties),
  modal: { position: 'fixed' as const, top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.8)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 } as React.CSSProperties,
  modalContent: { background: '#111827', borderRadius: 12, border: '1px solid #1f2937', width: '100%', maxWidth: 900, maxHeight: '90vh', overflow: 'auto', padding: 0 } as React.CSSProperties,
  modalHeader: { padding: '16px 24px', borderBottom: '1px solid #1f2937', display: 'flex', justifyContent: 'space-between', alignItems: 'center' } as React.CSSProperties,
  modalBody: { padding: 24 } as React.CSSProperties,
  closeBtn: { background: 'none', border: 'none', color: '#6b7280', fontSize: 24, cursor: 'pointer' } as React.CSSProperties,
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 } as React.CSSProperties,
  grid3: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 } as React.CSSProperties,
  indCard: { background: '#0f1520', borderRadius: 6, padding: 12 } as React.CSSProperties,
  indLabel: { fontSize: 11, color: '#6b7280', marginBottom: 2 } as React.CSSProperties,
  indValue: (color?: string) => ({ fontSize: 16, fontWeight: 600, color: color || '#e5e7eb' } as React.CSSProperties),
  filterRow: { display: 'flex', gap: 6, flexWrap: 'wrap' as const, alignItems: 'center' } as React.CSSProperties,
  filterBtn: (active: boolean) => ({ padding: '4px 10px', borderRadius: 4, border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600, background: active ? '#3b82f6' : '#1f2937', color: active ? '#fff' : '#9ca3af' } as React.CSSProperties),
  progressBar: { width: '100%', height: 4, background: '#1f2937', borderRadius: 2, overflow: 'hidden' } as React.CSSProperties,
  progressFill: (pct: number) => ({ height: '100%', width: `${pct}%`, background: '#3b82f6', transition: 'width 0.3s' } as React.CSSProperties),
  section: { marginTop: 24 } as React.CSSProperties,
  sectionTitle: { fontSize: 14, fontWeight: 600, color: '#9ca3af', marginBottom: 12, textTransform: 'uppercase' as const, letterSpacing: 0.5 } as React.CSSProperties,
}

const signalColor = (s: string) => s.includes('STRONG_BUY') ? '#16a34a' : s.includes('BUY') ? '#22c55e' : s.includes('STRONG_SELL') ? '#dc2626' : s.includes('SELL') ? '#ef4444' : '#6b7280'
const ratingColor = (r: string) => r === 'STRONG' ? '#16a34a' : r === 'GOOD' ? '#22c55e' : r === 'MARGINAL' ? '#eab308' : '#6b7280'

function Sparkline({ data, width = 100, height = 30 }: { data: number[]; width?: number; height?: number }) {
  if (!data || data.length < 2) return null
  const min = Math.min(...data), max = Math.max(...data)
  const range = max - min || 1
  const points = data.map((v, i) => `${(i / (data.length - 1)) * width},${height - ((v - min) / range) * height}`).join(' ')
  const up = data[data.length - 1] >= data[0]
  return (
    <svg width={width} height={height} style={{ display: 'block' }}>
      <polyline points={points} fill="none" stroke={up ? '#22c55e' : '#ef4444'} strokeWidth={1.5} />
      <circle cx={width} cy={height - ((data[data.length - 1] - min) / range) * height} r={2.5} fill={up ? '#22c55e' : '#ef4444'} />
    </svg>
  )
}

function App() {
  const [tab, setTab] = useState<'signals' | 'journal'>('signals')
  const [scan, setScan] = useState<ScanData | null>(null)
  const [scanning, setScanning] = useState(false)
  const [progress, setProgress] = useState({ status: 'idle', completed: 0, total: 0, current: '' })
  const [scanMode, setScanMode] = useState<'swing' | 'short'>('swing')
  const [signalFilter, setSignalFilter] = useState('ALL')
  const [marketFilter, setMarketFilter] = useState('ALL')
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [tradeRec, setTradeRec] = useState<TradeRec | null>(null)
  const [accountSize, setAccountSize] = useState(() => Number(localStorage.getItem('accountSize') || 10000))
  const [riskPct, setRiskPct] = useState(() => Number(localStorage.getItem('riskPct') || 1))
  const [sortBy, setSortBy] = useState<string>('score')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [journalTrades, setJournalTrades] = useState<any[]>([])
  const [journalStats, setJournalStats] = useState<any>(null)

  useEffect(() => { localStorage.setItem('accountSize', String(accountSize)) }, [accountSize])
  useEffect(() => { localStorage.setItem('riskPct', String(riskPct)) }, [riskPct])

  const fetchScan = useCallback(async () => {
    try {
      const r = await fetch('/api/scan/latest')
      if (r.ok) { const d = await r.json(); if (d.signals) setScan(d) }
    } catch {}
  }, [])

  useEffect(() => { fetchScan() }, [fetchScan])

  const startScan = async (fullScan = false) => {
    setScanning(true)
    setProgress({ status: 'running', completed: 0, total: fullScan ? 248 : 50, current: '' })
    try {
      const limitParam = fullScan ? '' : '&limit=50'
      const r = await fetch(`/api/scan?scan_mode=${scanMode}${limitParam}`, {
        method: 'POST',
        signal: AbortSignal.timeout(fullScan ? 900000 : 300000),
      })
      if (r.ok) {
        const data = await r.json()
        if (data.signals) setScan(data)
      }
    } catch (e: any) {
      console.error('Scan error:', e)
    }
    setScanning(false)
    setProgress({ status: 'completed', completed: 0, total: 0, current: '' })
  }

  const openDetail = async (sig: Signal) => {
    setSelectedSignal(sig)
    try {
      const r = await fetch(`/api/trade-rec?epic=${sig.epic}&account_size=${accountSize}&risk_pct=${riskPct}&mode=spread_bet`)
      if (r.ok) setTradeRec(await r.json())
    } catch {}
  }

  const filteredSignals = (scan?.signals || []).filter(s => {
    if (signalFilter !== 'ALL' && s.signal_type !== signalFilter) return false
    if (marketFilter !== 'ALL' && s.market_type !== marketFilter) return false
    return true
  }).sort((a, b) => {
    let av: number, bv: number
    switch (sortBy) {
      case 'score': av = Math.abs(a.composite_score); bv = Math.abs(b.composite_score); break
      case 'confidence': av = a.confidence; bv = b.confidence; break
      case 'rsi': av = a.rsi; bv = b.rsi; break
      case 'adx': av = a.adx; bv = b.adx; break
      case 'name': return sortDir === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name)
      default: av = Math.abs(a.composite_score); bv = Math.abs(b.composite_score)
    }
    return sortDir === 'asc' ? av - bv : bv - av
  })

  const loadJournal = async () => {
    try {
      const [t, s] = await Promise.all([
        fetch('/api/journal/history').then(r => r.json()),
        fetch('/api/journal/stats').then(r => r.json()),
      ])
      setJournalTrades(Array.isArray(t) ? t : [])
      setJournalStats(s)
    } catch {}
  }

  useEffect(() => { if (tab === 'journal') loadJournal() }, [tab])

  return (
    <div style={S.app}>
      <header style={S.header}>
        <div>
          <h1 style={S.title}>IG Trading Dashboard</h1>
          <p style={S.subtitle}>{scan ? `${scan.signals_found} signals from ${scan.total_instruments} instruments` : 'No scan data'}</p>
        </div>
        <div style={S.controls}>
          <div style={{ display: 'flex', gap: 4 }}>
            <button style={S.filterBtn(scanMode === 'swing')} onClick={() => setScanMode('swing')}>Swing</button>
            <button style={S.filterBtn(scanMode === 'short')} onClick={() => setScanMode('short')}>Short-term</button>
          </div>
          <input type="number" value={accountSize} onChange={e => setAccountSize(Number(e.target.value))} style={{ width: 90, background: '#1f2937', border: '1px solid #374151', color: '#e5e7eb', padding: '6px 8px', borderRadius: 4, fontSize: 13 }} placeholder="Account $" title="Account size" />
          <input type="number" value={riskPct} onChange={e => setRiskPct(Number(e.target.value))} step={0.5} min={0.5} max={5} style={{ width: 60, background: '#1f2937', border: '1px solid #374151', color: '#e5e7eb', padding: '6px 8px', borderRadius: 4, fontSize: 13 }} placeholder="Risk%" title="Risk %" />
          <button style={S.btn('#2563eb')} onClick={() => startScan(false)} disabled={scanning}>{scanning ? 'Scanning...' : 'Quick Scan (50)'}</button>
          <button style={S.btnOutline} onClick={() => startScan(true)} disabled={scanning}>Full Scan (248)</button>
        </div>
      </header>

      {scanning && (
        <div style={{ padding: '8px 24px', background: '#111827', borderBottom: '1px solid #1f2937' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#9ca3af', marginBottom: 4 }}>
            <span>Scanning: {progress.current}</span>
            <span>{progress.completed}/{progress.total}</span>
          </div>
          <div style={S.progressBar}><div style={S.progressFill(progress.total > 0 ? (progress.completed / progress.total) * 100 : 0)} /></div>
        </div>
      )}

      <div style={S.tabs}>
        <div style={S.tab(tab === 'signals')} onClick={() => setTab('signals')}>Signals</div>
        <div style={S.tab(tab === 'journal')} onClick={() => setTab('journal')}>Trade Journal</div>
      </div>

      <div style={S.content}>
        {tab === 'signals' && (
          <>
            {scan && (
              <div style={S.statsRow}>
                <div style={S.statCard}><div style={S.statLabel}>Total Instruments</div><div style={S.statValue()}>{scan.total_instruments}</div></div>
                <div style={S.statCard}><div style={S.statLabel}>Signals Found</div><div style={S.statValue('#3b82f6')}>{scan.signals_found}</div></div>
                <div style={S.statCard}><div style={S.statLabel}>Buy Signals</div><div style={S.statValue('#22c55e')}>{scan.buy_signals}</div></div>
                <div style={S.statCard}><div style={S.statLabel}>Sell Signals</div><div style={S.statValue('#ef4444')}>{scan.sell_signals}</div></div>
                <div style={S.statCard}><div style={S.statLabel}>Scan Mode</div><div style={S.statValue()}>{scan.scan_mode}</div></div>
              </div>
            )}

            <div style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
              <div style={S.filterRow}>
                <span style={{ fontSize: 11, color: '#6b7280' }}>Signal:</span>
                {['ALL','STRONG_BUY','BUY','NEUTRAL','SELL','STRONG_SELL'].map(f => (
                  <button key={f} style={S.filterBtn(signalFilter === f)} onClick={() => setSignalFilter(f)}>{f}</button>
                ))}
              </div>
              <div style={S.filterRow}>
                <span style={{ fontSize: 11, color: '#6b7280' }}>Market:</span>
                {['ALL','forex','index','commodity','crypto','share','bond'].map(f => (
                  <button key={f} style={S.filterBtn(marketFilter === f)} onClick={() => setMarketFilter(f)}>{f}</button>
                ))}
              </div>
            </div>

            {!scan ? (
              <div style={{ textAlign: 'center', padding: 60, color: '#6b7280' }}>
                <p style={{ fontSize: 18, marginBottom: 8 }}>Click "Full Scan" to analyze all 248 instruments</p>
                <p style={{ fontSize: 13 }}>Stocks, Forex, Indices, Commodities, Crypto, Bonds</p>
              </div>
            ) : (
              <div style={S.card}>
                <div style={{ overflowX: 'auto' }}>
                  <table style={S.table}>
                    <thead>
                      <tr>
                        <th style={S.th}>#</th>
                        <th style={S.th} onClick={() => { setSortBy('name'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Instrument</th>
                        <th style={S.th}>Price</th>
                        <th style={S.th}>Chart</th>
                        <th style={S.th} onClick={() => { setSortBy('score'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Signal</th>
                        <th style={S.th}>Rating</th>
                        <th style={S.th} onClick={() => { setSortBy('confidence'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>Confidence</th>
                        <th style={S.th}>Timeframes</th>
                        <th style={S.th}>Confluence</th>
                        <th style={S.th} onClick={() => { setSortBy('rsi'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>RSI</th>
                        <th style={S.th} onClick={() => { setSortBy('adx'); setSortDir(d => d === 'asc' ? 'desc' : 'asc') }}>ADX</th>
                        <th style={S.th}>Flags</th>
                        <th style={S.th}>News</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredSignals.map((sig, i) => (
                        <tr key={sig.epic} style={S.tr(i)} onClick={() => openDetail(sig)}>
                          <td style={{ ...S.td, color: '#6b7280', fontSize: 11 }}>{i + 1}</td>
                          <td style={S.td}>
                            <div style={{ fontWeight: 600 }}>{sig.name}</div>
                            <span style={S.marketBadge(sig.market_type)}>{sig.market_type}</span>
                          </td>
                          <td style={{ ...S.td, fontFamily: 'monospace' }}>
                            {sig.current_price < 1 ? sig.current_price.toFixed(6) : sig.current_price < 100 ? sig.current_price.toFixed(4) : sig.current_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                          </td>
                          <td style={S.td}><Sparkline data={sig.sparkline} /></td>
                          <td style={S.td}>
                            <span style={S.badge(signalColor(sig.signal_type))}>{sig.signal_type}</span>
                          </td>
                          <td style={S.td}>
                            <span style={{ color: ratingColor(sig.trade_rating || ''), fontWeight: 600 }}>
                              {sig.trade_rating || 'N/A'}
                            </span>
                          </td>
                          <td style={{ ...S.td, fontFamily: 'monospace' }}>{(sig.confidence * 100).toFixed(0)}%</td>
                          <td style={S.td}>
                            <div style={{ display: 'flex', gap: 3 }}>
                              {Object.entries(sig.timeframe_scores || {}).map(([tf, score]) => (
                                <span key={tf} style={{
                                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                  width: 28, height: 28, borderRadius: '50%', fontSize: 10, fontWeight: 700,
                                  background: score > 0 ? '#16a34a22' : score < 0 ? '#dc262622' : '#374151',
                                  color: score > 0 ? '#22c55e' : score < 0 ? '#ef4444' : '#6b7280',
                                  border: `1px solid ${score > 0 ? '#16a34a44' : score < 0 ? '#dc262644' : '#4b5563'}`,
                                }} title={`${tf}: ${score.toFixed(1)}`}>
                                  {tf === '1d' ? 'D' : tf === '4h' ? '4H' : tf === '1h' ? '1H' : '15m'}
                                </span>
                              ))}
                            </div>
                          </td>
                          <td style={{ ...S.td, fontFamily: 'monospace' }}>{(sig.confluence * 100).toFixed(0)}%</td>
                          <td style={{ ...S.td, fontFamily: 'monospace', color: sig.rsi > 70 ? '#ef4444' : sig.rsi < 30 ? '#22c55e' : '#e5e7eb' }}>
                            {sig.rsi.toFixed(0)}
                          </td>
                          <td style={{ ...S.td, fontFamily: 'monospace', color: sig.adx > 25 ? '#f59e0b' : '#6b7280' }}>
                            {sig.adx.toFixed(0)}
                          </td>
                          <td style={S.td}>
                            <div style={{ display: 'flex', gap: 3 }}>
                              {sig.has_breakout && <span style={S.badge('#8b5cf6')}>BO</span>}
                              {sig.has_volume_spike && <span style={S.badge('#f59e0b')}>VS</span>}
                              {sig.has_patterns && <span style={S.badge('#06b6d4')}>CP</span>}
                              {sig.has_divergence && <span style={S.badge('#ec4899')}>DIV</span>}
                            </div>
                          </td>
                          <td style={{ ...S.td, color: sig.news_score > 0.5 ? '#22c55e' : sig.news_score < -0.5 ? '#ef4444' : '#6b7280' }}>
                            {sig.news_score > 0 ? '+' : ''}{sig.news_score.toFixed(1)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {filteredSignals.length === 0 && (
                  <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>No signals match current filters</div>
                )}
              </div>
            )}
          </>
        )}

        {tab === 'journal' && (
          <div>
            <div style={S.statsRow}>
              <div style={S.statCard}><div style={S.statLabel}>Total Trades</div><div style={S.statValue()}>{journalStats?.total_trades || 0}</div></div>
              <div style={S.statCard}><div style={S.statLabel}>Win Rate</div><div style={S.statValue(journalStats?.win_rate > 50 ? '#22c55e' : '#ef4444')}>{journalStats?.win_rate || 0}%</div></div>
              <div style={S.statCard}><div style={S.statLabel}>Total P&L</div><div style={S.statValue(journalStats?.total_pl > 0 ? '#22c55e' : '#ef4444')}>${journalStats?.total_pl || 0}</div></div>
              <div style={S.statCard}><div style={S.statLabel}>Profit Factor</div><div style={S.statValue()}>{journalStats?.profit_factor || 0}</div></div>
              <div style={S.statCard}><div style={S.statLabel}>Avg Win</div><div style={S.statValue('#22c55e')}>${journalStats?.avg_win || 0}</div></div>
              <div style={S.statCard}><div style={S.statLabel}>Avg Loss</div><div style={S.statValue('#ef4444')}>${journalStats?.avg_loss || 0}</div></div>
            </div>
            {journalTrades.length > 0 ? (
              <div style={S.card}>
                <table style={S.table}>
                  <thead><tr>
                    <th style={S.th}>Instrument</th><th style={S.th}>Direction</th><th style={S.th}>Entry</th>
                    <th style={S.th}>Exit</th><th style={S.th}>P&L</th><th style={S.th}>Rating</th><th style={S.th}>Closed</th>
                  </tr></thead>
                  <tbody>
                    {journalTrades.map((t: any, i: number) => (
                      <tr key={t.id} style={S.tr(i)}>
                        <td style={S.td}><strong>{t.name}</strong><br/><span style={S.marketBadge(t.market_type)}>{t.market_type}</span></td>
                        <td style={S.td}><span style={S.badge(t.direction === 'BUY' ? '#22c55e' : '#ef4444')}>{t.direction}</span></td>
                        <td style={{ ...S.td, fontFamily: 'monospace' }}>{t.entry_price}</td>
                        <td style={{ ...S.td, fontFamily: 'monospace' }}>{t.exit_price || '-'}</td>
                        <td style={{ ...S.td, fontFamily: 'monospace', color: t.profit_loss > 0 ? '#22c55e' : '#ef4444', fontWeight: 700 }}>${t.profit_loss}</td>
                        <td style={S.td}>{t.trade_rating}</td>
                        <td style={{ ...S.td, fontSize: 11, color: '#6b7280' }}>{t.closed_at?.slice(0, 16)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#6b7280' }}>No trades logged yet. Open a trade from a signal detail.</div>
            )}
          </div>
        )}
      </div>

      {selectedSignal && (
        <div style={S.modal} onClick={() => { setSelectedSignal(null); setTradeRec(null) }}>
          <div style={S.modalContent} onClick={e => e.stopPropagation()}>
            <div style={S.modalHeader}>
              <div>
                <h2 style={{ margin: 0, fontSize: 20 }}>{selectedSignal.name}</h2>
                <span style={S.marketBadge(selectedSignal.market_type)}>{selectedSignal.market_type}</span>
                <span style={{ ...S.badge(signalColor(selectedSignal.signal_type)), marginLeft: 8 }}>{selectedSignal.signal_type}</span>
              </div>
              <button style={S.closeBtn} onClick={() => { setSelectedSignal(null); setTradeRec(null) }}>&times;</button>
            </div>
            <div style={S.modalBody}>
              {tradeRec && (
                <div style={{ ...S.grid3, marginBottom: 20 }}>
                  <div style={S.indCard}>
                    <div style={S.indLabel}>Trade Rating</div>
                    <div style={S.indValue(ratingColor(tradeRec.trade_rating))}>{tradeRec.trade_rating} {tradeRec.rating_score}/20</div>
                  </div>
                  <div style={S.indCard}>
                    <div style={S.indLabel}>Entry ({tradeRec.entry_type})</div>
                    <div style={S.indValue()}>{tradeRec.entry_price}</div>
                  </div>
                  <div style={S.indCard}>
                    <div style={S.indLabel}>Stop Loss</div>
                    <div style={S.indValue('#ef4444')}>{tradeRec.stop_loss}</div>
                  </div>
                  <div style={S.indCard}>
                    <div style={S.indLabel}>Take Profit 1</div>
                    <div style={S.indValue('#22c55e')}>{tradeRec.take_profit_1}</div>
                  </div>
                  <div style={S.indCard}>
                    <div style={S.indLabel}>Take Profit 2</div>
                    <div style={S.indValue('#22c55e')}>{tradeRec.take_profit_2}</div>
                  </div>
                  <div style={S.indCard}>
                    <div style={S.indLabel}>Position Size</div>
                    <div style={S.indValue()}>{tradeRec.position_size.toFixed(2)} (${tradeRec.position_value})</div>
                  </div>
                  <div style={S.indCard}>
                    <div style={S.indLabel}>Risk</div>
                    <div style={S.indValue('#f59e0b')}>${tradeRec.risk_amount} ({riskPct}%)</div>
                  </div>
                  <div style={S.indCard}>
                    <div style={S.indLabel}>R:R Ratio</div>
                    <div style={S.indValue()}>{tradeRec.rr_ratio}:1</div>
                  </div>
                  <div style={S.indCard}>
                    <div style={S.indLabel}>Spread Est.</div>
                    <div style={S.indValue('#6b7280')}>{tradeRec.spread_estimate}</div>
                  </div>
                </div>
              )}

              <div style={S.section}>
                <div style={S.sectionTitle}>Technical Indicators</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: 8 }}>
                  {selectedSignal.indicators && Object.entries(selectedSignal.indicators).map(([k, v]) => {
                    if (k === 'obv_trend') return (
                      <div key={k} style={S.indCard}>
                        <div style={S.indLabel}>OBV Trend</div>
                        <div style={S.indValue(v === 'accumulation' ? '#22c55e' : v === 'distribution' ? '#ef4444' : '#6b7280')}>{v}</div>
                      </div>
                    )
                    if (typeof v !== 'number') return null
                    const color = k === 'rsi' ? (v > 70 ? '#ef4444' : v < 30 ? '#22c55e' : '#e5e7eb') : undefined
                    return (
                      <div key={k} style={S.indCard}>
                        <div style={S.indLabel}>{k.replace(/_/g, ' ').toUpperCase()}</div>
                        <div style={S.indValue(color)}>{typeof v === 'number' ? v.toFixed(2) : v}</div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {(selectedSignal.candlestick_patterns?.length > 0 || selectedSignal.chart_patterns?.length > 0) && (
                <div style={S.section}>
                  <div style={S.sectionTitle}>Patterns Detected</div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    {[...(selectedSignal.candlestick_patterns || []), ...(selectedSignal.chart_patterns || [])].map((p, i) => (
                      <div key={i} style={{ ...S.badge(p.type === 'bullish' ? '#16a34a' : p.type === 'bearish' ? '#dc2626' : '#6b7280'), padding: '4px 10px' }}>
                        {p.name} ({(p.confidence * 100).toFixed(0)}%)
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div style={S.section}>
                <div style={S.sectionTitle}>Signal Reasons</div>
                <div style={{ maxHeight: 200, overflow: 'auto', fontSize: 12, color: '#9ca3af' }}>
                  {selectedSignal.reasons?.map((r, i) => (
                    <div key={i} style={{ padding: '3px 0', borderBottom: '1px solid #1f2937' }}>{r}</div>
                  ))}
                </div>
              </div>

              {selectedSignal.news_headlines?.length > 0 && (
                <div style={S.section}>
                  <div style={S.sectionTitle}>News Headlines</div>
                  {selectedSignal.news_headlines.map((h, i) => (
                    <div key={i} style={{ padding: '6px 0', borderBottom: '1px solid #1f2937', fontSize: 12 }}>
                      <span style={{ color: h.sentiment > 0 ? '#22c55e' : h.sentiment < 0 ? '#ef4444' : '#6b7280' }}>
                        [{h.impact?.toUpperCase()}]
                      </span>{' '}
                      <span style={{ color: '#d1d5db' }}>{h.title}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
