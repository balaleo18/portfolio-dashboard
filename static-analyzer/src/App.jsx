import React, { useState } from 'react';
import * as XLSX from 'xlsx';
import { 
  processHoldingsData, 
  SCENARIOS 
} from './services/analytics';
import { 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid,
  Legend
} from 'recharts';
import { 
  Upload, 
  AlertTriangle, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Layers, 
  Percent, 
  RefreshCw,
  Search,
  CheckCircle,
  FileText,
  Sliders
} from 'lucide-react';
import './App.css';

const CHART_COLORS = ['#6366f1', '#10b981', '#a855f7', '#f59e0b', '#ec4899', '#3b82f6'];

// Helper to format currency in INR Lakhs / Crores
const formatINR = (value) => {
  const absVal = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  if (absVal >= 10000000) {
    return `${sign}₹ ${(absVal / 10000000).toFixed(2)} Cr`;
  }
  if (absVal >= 100000) {
    return `${sign}₹ ${(absVal / 100000).toFixed(2)} L`;
  }
  return `${sign}₹ ${absVal.toLocaleString('en-IN')}`;
};

export default function App() {
  const [portfolio, setPortfolio] = useState(null);
  const [error, setError] = useState(null);
  const [fileName, setFileName] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [recFilter, setRecFilter] = useState("ALL");
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.xlsx')) {
        setFileName(file.name);
        parseExcelFile(file);
      } else {
        setError("Only Zerodha Kite Holdings exports (.xlsx) are supported.");
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setFileName(file.name);
      parseExcelFile(file);
    }
  };

  const parseExcelFile = (file) => {
    setError(null);
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        
        const sheetName = workbook.SheetNames.includes("Combined") 
          ? "Combined" 
          : workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        
        // Read sheet as nested arrays to find header row
        const rawData = XLSX.utils.sheet_to_json(worksheet, { header: 1 });
        let headerIdx = -1;
        for (let i = 0; i < rawData.length; i++) {
          const row = rawData[i].map(v => String(v || "").trim().toLowerCase());
          if (row.includes("symbol") && row.includes("isin")) {
            headerIdx = i;
            break;
          }
        }
        
        if (headerIdx === -1) {
          throw new Error("Could not find a valid holdings table header row containing Symbol and ISIN.");
        }
        
        const headers = rawData[headerIdx].map(v => String(v || "").trim());
        const rows = [];
        for (let i = headerIdx + 1; i < rawData.length; i++) {
          const rowValues = rawData[i];
          if (!rowValues || rowValues.length === 0 || rowValues.every(v => v === null || v === undefined || v === "")) {
            continue;
          }
          const rowObj = {};
          headers.forEach((h, index) => {
            if (h) {
              rowObj[h] = rowValues[index];
            }
          });
          rows.push(rowObj);
        }
        
        if (rows.length === 0) {
          throw new Error("No holdings rows found in the spreadsheet.");
        }
        
        const results = processHoldingsData(rows);
        setPortfolio(results);
      } catch (err) {
        console.error(err);
        setError(err.message || "Failed to parse the Excel file. Make sure it is a valid Zerodha holdings sheet.");
      }
    };
    reader.onerror = () => setError("File reading error.");
    reader.readAsArrayBuffer(file);
  };

  const handleReset = () => {
    setPortfolio(null);
    setError(null);
    setFileName("");
    setSearchTerm("");
    setRecFilter("ALL");
  };

  // Filter holdings based on search and recommendation filter
  const getFilteredHoldings = () => {
    if (!portfolio) return [];
    return portfolio.holdings.filter(h => {
      const matchSearch = h.symbol.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          h.sector.toLowerCase().includes(searchTerm.toLowerCase());
      const matchFilter = recFilter === "ALL" || h.recommendation === recFilter;
      return matchSearch && matchFilter;
    });
  };

  // Top 5 / Top 10 weights
  const top10Weight = portfolio 
    ? [...portfolio.holdings].sort((a, b) => b.weight - a.weight).slice(0, 10).reduce((sum, h) => sum + h.weight, 0)
    : 0;

  const top5Weight = portfolio 
    ? [...portfolio.holdings].sort((a, b) => b.weight - a.weight).slice(0, 5).reduce((sum, h) => sum + h.weight, 0)
    : 0;

  // Defensive exposure
  const defensiveWeight = portfolio
    ? portfolio.riskBucketSummary
        .filter(g => ["Low-vol hybrid/arbitrage", "Debt / liquidity"].includes(g.name))
        .reduce((sum, g) => sum + g.weight, 0)
    : 0;

  const equityGrowthWeight = 100 - defensiveWeight;

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <h1>Kite Portfolio Static Analyzer</h1>
          <p className="subtitle">Secure Client-Side Risk Analytics & Action Recommendations</p>
        </div>
        {portfolio && (
          <button className="reset-btn" onClick={handleReset}>
            <RefreshCw size={16} />
            <span>Load New File</span>
          </button>
        )}
      </header>

      <main className="app-main">
        {!portfolio ? (
          /* File Upload Screen */
          <div className="upload-section">
            <div className="card glass upload-card">
              <h2>Secure Drag-and-Drop Ingestion</h2>
              <p className="privacy-badge">
                🔒 Private Serverless Environment: No database, no accounts, and no data leaves your browser.
              </p>
              
              <div 
                className={`dropzone ${dragActive ? 'active' : ''} ${error ? 'error' : ''}`}
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
              >
                <div className="dropzone-content">
                  <Upload size={48} className="upload-icon" />
                  <p className="primary-text">Drag and drop your <strong>holdings-*.xlsx</strong> file here</p>
                  <p className="secondary-text">or click the button below to browse</p>
                  
                  <label className="file-input-label">
                    Browse File
                    <input 
                      type="file" 
                      accept=".xlsx" 
                      onChange={handleFileChange} 
                      className="hidden-file-input"
                    />
                  </label>
                  <p className="disclaimer">Only Zerodha Kite holdings export files are accepted.</p>
                </div>
              </div>

              {error && <div className="alert-message error-alert">{error}</div>}

              <div className="instructions">
                <h3>How to download your Zerodha holdings export:</h3>
                <ol>
                  <li>Login to Zerodha Console (<a href="https://console.zerodha.com" target="_blank" rel="noreferrer">console.zerodha.com</a>)</li>
                  <li>Navigate to <strong>Portfolio</strong> &gt; <strong>Holdings</strong></li>
                  <li>Click the <strong>Download XLSX</strong> button in the top right corner</li>
                  <li>Drag the downloaded spreadsheet into the dropzone above!</li>
                </ol>
              </div>
            </div>
          </div>
        ) : (
          /* Dashboard Content Screen */
          <div className="dashboard-content">
            
            {/* KPI Cards */}
            <section className="grid-kpis">
              <div className="card glass kpi-card">
                <div className="kpi-label">Present Value</div>
                <div className="kpi-value">{formatINR(portfolio.totalValue)}</div>
                <div className="kpi-note text-muted">Current Portfolio sleeve</div>
              </div>
              <div className="card glass kpi-card">
                <div className="kpi-label">Invested Value</div>
                <div className="kpi-value">{formatINR(portfolio.totalInvested)}</div>
                <div className="kpi-note text-muted">Total capital purchase price</div>
              </div>
              <div className="card glass kpi-card">
                <div className="kpi-label">Unrealized P&L</div>
                <div className={`kpi-value ${portfolio.totalPnL >= 0 ? 'pos' : 'neg'}`}>
                  {formatINR(portfolio.totalPnL)}
                </div>
                <div className={`kpi-note ${portfolio.totalPnL >= 0 ? 'pos' : 'neg'} font-medium`}>
                  {portfolio.totalPnLPct >= 0 ? <TrendingUp size={14} style={{display:'inline', marginRight:4}} /> : <TrendingDown size={14} style={{display:'inline', marginRight:4}} />}
                  {portfolio.totalPnLPct.toFixed(2)}%
                </div>
              </div>
              <div className="card glass kpi-card">
                <div className="kpi-label">Holdings Count</div>
                <div className="kpi-value">{portfolio.holdings.length}</div>
                <div className="kpi-note text-muted">Unique assets tracked</div>
              </div>
              <div className="card glass kpi-card">
                <div className="kpi-label">Top 10 Weight</div>
                <div className="kpi-value">{top10Weight.toFixed(1)}%</div>
                <div className="kpi-note text-muted">Top 5: {top5Weight.toFixed(1)}%</div>
              </div>
              <div className="card glass kpi-card">
                <div className="kpi-label">Growth Exposure</div>
                <div className="kpi-value">{equityGrowthWeight.toFixed(1)}%</div>
                <div className="kpi-note text-muted">Defensive: {defensiveWeight.toFixed(1)}%</div>
              </div>
            </section>

            {/* Diagnostics and Stress-Test */}
            <section className="grid-two-cols">
              <div className="card glass diagnosis-card border-blue">
                <div className="card-header">
                  <Sliders size={20} className="text-blue" />
                  <h2>Professional Diagnosis</h2>
                </div>
                <p>
                  This portfolio is configured with a <strong>{equityGrowthWeight.toFixed(1)}% Growth / {defensiveWeight.toFixed(1)}% Defensive</strong> allocation. 
                  {defensiveWeight > 40 ? (
                    " Your holdings are currently over-weighted in defensive and liquid sleeves. While this preserves capital during drawdowns, it incurs a high opportunity cost for a medium-to-long term wealth generation goal."
                  ) : (
                    " This profile provides a solid growth tilt suitable for capital compounding. Keep monitoring sector overlap and individual stock concentration ratios."
                  )}
                </p>
                <p>
                  <strong>Key Strategic Advice:</strong> Avoid accumulating small, low-conviction positions below 0.5% weight. Consolidate them into core mutual funds or high-conviction direct equities where you can allocate at least 1.5% to 3% to make a meaningful difference.
                </p>
              </div>

              <div className="card glass">
                <h2>Asset Allocation Overview</h2>
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie
                        data={portfolio.assetClassSummary}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={85}
                        paddingAngle={4}
                        dataKey="value"
                      >
                        {portfolio.assetClassSummary.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatINR(value)} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </section>

            {/* Risk Buckets & Stress Tests */}
            <section className="grid-two-cols">
              <div className="card glass">
                <h2>Risk Bucket Allocations</h2>
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={portfolio.riskBucketSummary} layout="vertical" margin={{ left: 30, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" tickFormatter={(v) => `${v}%`} />
                      <YAxis dataKey="name" type="category" width={140} tick={{fontSize: 12}} />
                      <Tooltip formatter={(value) => `${parseFloat(value).toFixed(1)}%`} />
                      <Bar dataKey="weight" fill="#6366f1" radius={[0, 4, 4, 0]}>
                        {portfolio.riskBucketSummary.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="card glass">
                <h2>Stress Test Scenarios</h2>
                <div className="table-wrapper">
                  <table className="dense-table">
                    <thead>
                      <tr>
                        <th>Scenario</th>
                        <th>Estimated Shock Impact</th>
                        <th>Post-Shock Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {portfolio.stressTests.map((st, i) => (
                        <tr key={i}>
                          <td className="font-semibold">{st.scenario}</td>
                          <td className={`font-semibold ${st.loss >= 0 ? 'pos' : 'neg'}`}>
                            {formatINR(st.loss)} ({st.lossPct.toFixed(2)}%)
                          </td>
                          <td>{formatINR(st.endingValue)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            {/* Risk Warnings & Suggested Allocations */}
            <section className="grid-two-cols">
              <div className="card glass">
                <h2>Risk Warning Flags</h2>
                {portfolio.flags.length === 0 ? (
                  <div className="empty-message">
                    <CheckCircle size={32} className="pos" style={{marginBottom: 12}} />
                    <p>No high or medium severity warning flags triggered. Your allocation is well balanced.</p>
                  </div>
                ) : (
                  <div className="flags-list">
                    {portfolio.flags.map((flag, idx) => (
                      <div key={idx} className={`flag-alert border-${flag.severity.toLowerCase()}`}>
                        <div className="flag-alert-header">
                          <span className={`badge badge-${flag.severity.toLowerCase()}`}>{flag.severity} Risk</span>
                          <h4>{flag.title}</h4>
                        </div>
                        <p>{flag.detail}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card glass">
                <h2>Suggested Sleeve Allocations</h2>
                <div className="table-wrapper">
                  <table className="dense-table">
                    <thead>
                      <tr>
                        <th>Asset Type</th>
                        <th>Suggested Target</th>
                        <th>Operational Guidance</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="font-semibold">Core India Equity</td>
                        <td>35 - 45%</td>
                        <td className="text-muted">Compound via Nifty 50/100, active Flexi-Caps, and primary holdings.</td>
                      </tr>
                      <tr>
                        <td className="font-semibold">Mid/Small/Factor Equity</td>
                        <td>15 - 20%</td>
                        <td className="text-muted">Accumulate incrementally on corrections; small caps are valued aggressively.</td>
                      </tr>
                      <tr>
                        <td className="font-semibold">Direct Concentrated Stocks</td>
                        <td>15 - 20%</td>
                        <td className="text-muted">Consolidate fractional holdings into core positions worth 1.5% - 3% each.</td>
                      </tr>
                      <tr>
                        <td className="font-semibold">Global Equities</td>
                        <td>8 - 12%</td>
                        <td className="text-muted">Hedge against local inflation and INR depreciation via global index FoFs.</td>
                      </tr>
                      <tr>
                        <td className="font-semibold">Debt & Liquidity</td>
                        <td>15 - 25%</td>
                        <td className="text-muted">Keep dry powder ready for corrections; trim excess arbitrage overlap.</td>
                      </tr>
                      <tr>
                        <td className="font-semibold">Gold Hedges</td>
                        <td>3 - 6%</td>
                        <td className="text-muted">Maintain SGBs/physical gold as macro currency hedges.</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </section>

            {/* Recommendations & Holdings Table */}
            <section className="card glass full-width-card">
              <div className="holdings-table-header">
                <h2>Detailed Holdings Actions</h2>
                <div className="filter-controls">
                  <div className="search-box">
                    <Search size={16} />
                    <input 
                      type="text" 
                      placeholder="Search symbol or sector..." 
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />
                  </div>
                  
                  <div className="filter-tabs">
                    {["ALL", "Buy/Add", "Hold", "Trim", "Exit/Review"].map((tab) => (
                      <button 
                        key={tab} 
                        className={`filter-tab-btn ${recFilter === tab ? 'active' : ''}`}
                        onClick={() => setRecFilter(tab)}
                      >
                        {tab} {portfolio.actionCounts[tab] !== undefined && `(${portfolio.actionCounts[tab]})`}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="table-wrapper">
                <table className="analysis-table">
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Sector</th>
                      <th>Risk Bucket</th>
                      <th>Weight</th>
                      <th>Unrealized P&L</th>
                      <th>Recommendation</th>
                      <th>Value Thesis</th>
                      <th>Trade Recommendation</th>
                      <th>Pros / Cons</th>
                    </tr>
                  </thead>
                  <tbody>
                    {getFilteredHoldings().map((h, i) => (
                      <tr key={i} className={`row-rec-${h.recommendation.toLowerCase().replace('/', '-')}`}>
                        <td className="font-bold">{h.symbol}</td>
                        <td className="font-semibold text-muted">{h.sector}</td>
                        <td>
                          <span className="risk-bucket-badge">{h.riskBucket}</span>
                        </td>
                        <td className="font-semibold">{h.weight.toFixed(2)}%</td>
                        <td className={`font-semibold ${h.pnl >= 0 ? 'pos' : 'neg'}`}>
                          {formatINR(h.pnl)} ({h.pnlPct.toFixed(2)}%)
                        </td>
                        <td>
                          <span className={`badge-rec badge-rec-${h.recommendation.toLowerCase().replace('/', '-')}`}>
                            {h.recommendation}
                          </span>
                        </td>
                        <td className="text-small">{h.valueCase}</td>
                        <td className="text-small">{h.tradeCase}</td>
                        <td className="text-small">
                          <div className="pros-cons">
                            <span className="pos-bullet">✓ {h.pros}</span>
                            <span className="neg-bullet">✗ {h.cons}</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {getFilteredHoldings().length === 0 && (
                      <tr>
                        <td colSpan={9} className="empty-row">
                          No holdings match your search criteria.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        )}

        {/* System Diagnostics, Tech Stack, & Security Audit Center */}
        <div className="card glass full-width-card" style={{ marginTop: '3rem', padding: '1.75rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', textAlign: 'left' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.25rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.75rem' }}>
            <AlertTriangle size={20} style={{ color: 'var(--amber)' }} />
            <h2 style={{ margin: 0, fontSize: '1.2rem', fontFamily: 'Outfit, sans-serif' }}>System Status, Tech Stack & Security Protocol</h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', fontSize: '0.8rem', lineHeight: '1.5' }}>
            
            {/* Tech Stack & Progress Section */}
            <div>
              <h3 style={{ margin: '0 0 0.75rem 0', color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: '600' }}>Implementation Status & Tech Stack</h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div style={{ background: 'rgba(255,255,255,0.01)', padding: '0.75rem', borderRadius: '6px', borderLeft: '3px solid #10b981' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: '700' }}>Phase 1: Static Analyzer (Statically Hosted)</span>
                    <span style={{ color: '#10b981', fontWeight: '600' }}>Active & Deployed</span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                    <strong>Tech Stack:</strong> React 18, Vite, SheetJS (XLSX), Recharts, Lucide Icons, Vanilla CSS.<br/>
                    <strong>Built:</strong> Client-side parsing, Risk bucketing, Stress-testing shock calculations, Action recommendations, Cloudflare Pages hosting.<br/>
                    <strong>Pending:</strong> Multi-portfolio comparison, Offline browser database index cache.
                  </div>
                </div>

                <div style={{ background: 'rgba(255,255,255,0.01)', padding: '0.75rem', borderRadius: '6px', borderLeft: '3px solid #6366f1' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: '700' }}>Phase 2: Live Analyzer (Kite Connect API)</span>
                    <span style={{ color: '#6366f1', fontWeight: '600' }}>Active & Running</span>
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                    <strong>Tech Stack:</strong> FastAPI, SQLite (SQLAlchemy), APScheduler, Uvicorn, Python, React, Recharts, Caddy Server.<br/>
                    <strong>Built:</strong> SQLite database snapshots, live holdings sync, manual assets (FD, Gold), daily snapshot scheduler, Caddy multi-port local proxy.<br/>
                    <strong>Pending:</strong> Live Zerodha websocket streaming, daily automated backup exports.
                  </div>
                </div>
              </div>
            </div>

            {/* Security & Personal Information Protocol */}
            <div>
              <h3 style={{ margin: '0 0 0.75rem 0', color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: '600' }}>Security & Privacy Protocols</h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div style={{ background: 'rgba(16, 185, 129, 0.03)', padding: '0.75rem', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.15)' }}>
                  <strong style={{ color: '#10b981' }}>🔒 Personal Information Security Protocol</strong>
                  <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    <strong>Static Analyzer:</strong> 100% Secure. No personal financial values or share quantities are ever transmitted or stored on any server. All processing is memory-only in the browser.<br/>
                    <strong>Live Analyzer:</strong> SQLite database stores holdings, share counts, and encrypted Zerodha login tokens locally on the host machine. These files are restricted to local/Tailscale access and excluded from the git repo.
                  </p>
                </div>

                <div style={{ background: 'rgba(244, 63, 94, 0.03)', padding: '0.75rem', borderRadius: '6px', border: '1px solid rgba(244, 63, 94, 0.15)' }}>
                  <strong style={{ color: 'var(--rose)' }}>🛡️ Technical Security Protocol & Vulnerabilities</strong>
                  <ul style={{ margin: '0.25rem 0 0 0', paddingLeft: '1rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    <li><strong>Secrets Management:</strong> API keys, database URLs, and session secrets are loaded via <code>.env</code> and excluded from Git repository history.</li>
                    <li><strong>Interface Exposure:</strong> The application does not expose ports publicly. All backend interfaces are bound to <code>127.0.0.1</code> and served over Tailscale via Caddy.</li>
                    <li><strong>Session Tokens:</strong> PyJWT tokens authorize requests using HMAC HS256 encryption. Keep the <code>ENCRYPTION_KEY</code> secret.</li>
                  </ul>
                </div>
              </div>
            </div>

          </div>
        </div>
      </main>
    </div>
  );
}
