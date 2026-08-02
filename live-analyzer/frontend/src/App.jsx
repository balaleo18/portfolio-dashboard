import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, Legend, AreaChart, Area, BarChart, Bar 
} from 'recharts';
import { 
  TrendingUp, Wallet, ArrowUpRight, ArrowDownRight, RefreshCw, 
  Plus, Trash2, Edit3, Lock, LogOut, CheckCircle, AlertCircle, X,
  Coins, Landmark, ChevronRight, BarChart3, Search, Sliders, AlertTriangle
} from 'lucide-react';
import './App.css';

const CHART_COLORS = ['#6366f1', '#a855f7', '#10b981', '#f59e0b'];

export default function App() {
  // Authentication State
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('token'));
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [checkingPasswordConfig, setCheckingPasswordConfig] = useState(true);

  // App Data State
  const [portfolio, setPortfolio] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  
  // Analytics filters
  const [analyticsSearch, setAnalyticsSearch] = useState('');
  const [analyticsRecFilter, setAnalyticsRecFilter] = useState('ALL');

  // Modal State
  const [showAssetModal, setShowAssetModal] = useState(false);
  const [editingAsset, setEditingAsset] = useState(null);
  const [modalAssetType, setModalAssetType] = useState('FD');
  
  // FD Form state
  const [fdForm, setFdForm] = useState({
    name: '',
    principal: '',
    interest_rate: '',
    compounding_frequency: 'Quarterly',
    start_date: '',
    maturity_date: ''
  });

  // Gold Form state
  const [goldForm, setGoldForm] = useState({
    name: '',
    principal: '',
    quantity: '',
    gold_type: 'PHYSICAL',
    start_date: ''
  });

  // Notifications
  const [toast, setToast] = useState(null);

  // Helper: show toast message
  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // 1. Initial configuration check: Is password set?
  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        // If password is NOT configured, we bypass and auto-login
        if (!data.app_password_configured) {
          setIsAuthenticated(true);
        }
        setCheckingPasswordConfig(false);
      })
      .catch(err => {
        console.error("Error checking health status:", err);
        setCheckingPasswordConfig(false);
      });
  }, []);

  // 2. Fetch Portfolio data
  const fetchPortfolio = async (currentToken = token) => {
    setLoading(true);
    setError(null);
    try {
      const headers = {};
      if (currentToken) {
        headers['Authorization'] = `Bearer ${currentToken}`;
      }
      
      const res = await fetch('/api/portfolio/summary', { headers });
      if (res.status === 401) {
        // Lock out
        localStorage.removeItem('token');
        setToken('');
        setIsAuthenticated(false);
        throw new Error("Session expired. Please login again.");
      }
      if (!res.ok) {
        throw new Error("Failed to fetch portfolio data.");
      }
      const data = await res.json();
      setPortfolio(data);

      // Fetch portfolio analytics
      try {
        const analyticsRes = await fetch('/api/analytics', { headers });
        if (analyticsRes.ok) {
          const analyticsData = await analyticsRes.json();
          if (analyticsData.success) {
            setAnalytics(analyticsData);
          }
        }
      } catch (ae) {
        console.error("Error fetching analytics:", ae);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch portfolio when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      fetchPortfolio(token);
      
      // Parse query params for Kite oauth redirects
      const params = new URLSearchParams(window.location.search);
      if (params.get('connected') === 'true') {
        showToast("Successfully connected to Zerodha Kite!");
        // Clear params
        window.history.replaceState({}, document.title, window.location.pathname);
      } else if (params.get('error') === 'auth_failed') {
        showToast("Failed to connect to Zerodha Kite. Check secrets or try again.", "error");
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }
  }, [isAuthenticated]);

  // 3. Handle login submit
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      if (!res.ok) {
        throw new Error("Invalid password");
      }
      const data = await res.json();
      localStorage.setItem('token', data.token);
      setToken(data.token);
      setIsAuthenticated(true);
      showToast("Log in successful!");
    } catch (err) {
      setLoginError(err.message);
    }
  };

  // 4. Handle logout
  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken('');
    setIsAuthenticated(false);
    setPortfolio(null);
  };

  // 5. Reconnect to Zerodha Kite Connect
  const handleKiteConnect = async () => {
    try {
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      const res = await fetch('/api/auth/login-url', { headers });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      showToast("Error getting Kite login URL", "error");
    }
  };

  // 6. Delete manual asset
  const handleDeleteAsset = async (assetId) => {
    if (!window.confirm("Are you sure you want to delete this asset?")) return;
    try {
      const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
      const res = await fetch(`/api/manual/${assetId}`, {
        method: 'DELETE',
        headers
      });
      if (res.ok) {
        showToast("Asset deleted successfully!");
        fetchPortfolio();
      } else {
        throw new Error();
      }
    } catch (err) {
      showToast("Failed to delete asset.", "error");
    }
  };

  // 7. Open Edit modal
  const handleEditAsset = (asset) => {
    setEditingAsset(asset);
    setModalAssetType(asset.asset_type);
    if (asset.asset_type === 'FD') {
      setFdForm({
        name: asset.name,
        principal: asset.principal,
        interest_rate: asset.interest_rate,
        compounding_frequency: asset.compounding_frequency || 'Quarterly',
        start_date: asset.start_date,
        maturity_date: asset.maturity_date || ''
      });
    } else {
      setGoldForm({
        name: asset.name,
        principal: asset.principal,
        quantity: asset.quantity,
        gold_type: asset.gold_type || 'PHYSICAL',
        start_date: asset.start_date
      });
    }
    setShowAssetModal(true);
  };

  // 8. Submit Add/Edit manual asset
  const handleSaveAsset = async (e) => {
    e.preventDefault();
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const body = modalAssetType === 'FD' 
        ? {
            asset_type: 'FD',
            name: fdForm.name,
            principal: parseFloat(fdForm.principal),
            interest_rate: parseFloat(fdForm.interest_rate),
            compounding_frequency: fdForm.compounding_frequency,
            start_date: fdForm.start_date,
            maturity_date: fdForm.maturity_date
          }
        : {
            asset_type: 'GOLD',
            name: goldForm.name,
            principal: parseFloat(goldForm.principal),
            quantity: parseFloat(goldForm.quantity),
            gold_type: goldForm.gold_type,
            start_date: goldForm.start_date
          };

      const url = editingAsset ? `/api/manual/${editingAsset.id}` : '/api/manual';
      const method = editingAsset ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers,
        body: JSON.stringify(body)
      });

      if (res.ok) {
        showToast(editingAsset ? "Asset updated successfully!" : "Asset added successfully!");
        setShowAssetModal(false);
        setEditingAsset(null);
        // Reset forms
        setFdForm({ name: '', principal: '', interest_rate: '', compounding_frequency: 'Quarterly', start_date: '', maturity_date: '' });
        setGoldForm({ name: '', principal: '', quantity: '', gold_type: 'PHYSICAL', start_date: '' });
        fetchPortfolio();
      } else {
        const data = await res.json();
        throw new Error(data.detail || "Error saving asset.");
      }
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  // Format currency in INR (Lakhs / Crores / Thousands)
  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val);
  };

  if (checkingPasswordConfig) {
    return (
      <div className="login-overlay">
        <div className="glass login-card">
          <RefreshCw className="animate-spin text-indigo-500" size={32} style={{ margin: '0 auto' }} />
          <h2>Initializing...</h2>
        </div>
      </div>
    );
  }

  // Password Login Screen (Defense in Depth)
  if (!isAuthenticated) {
    return (
      <div className="login-overlay">
        <form onSubmit={handleLogin} className="glass login-card fade-in">
          <div className="login-icon">
            <Lock size={30} />
          </div>
          <div>
            <h2>Secure Gateway</h2>
            <p>Accessing personal investment portfolio</p>
          </div>
          {loginError && (
            <div style={{ color: 'var(--rose)', fontSize: '0.85rem', fontWeight: 600 }}>
              {loginError}
            </div>
          )}
          <div className="form-group" style={{ textAlign: 'left' }}>
            <label htmlFor="pass">Enter Password</label>
            <input 
              id="pass" 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••" 
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" style={{ justifyContent: 'center' }}>
            Verify Identity
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="dashboard-container fade-in">
      
      {/* Toast Alert */}
      {toast && (
        <div className={`glass status-badge ${toast.type === 'error' ? 'status-disconnected' : 'status-connected'}`} 
             style={{ 
               position: 'fixed', top: '1.5rem', right: '1.5rem', zIndex: 1100, 
               padding: '0.8rem 1.2rem', boxShadow: '0 8px 30px rgba(0,0,0,0.5)',
               animation: 'fadeIn 0.2s ease'
             }}>
          {toast.type === 'error' ? <AlertCircle size={18} /> : <CheckCircle size={18} />}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Header */}
      <header className="dashboard-header">
        <div className="header-title">
          <h1>Portfolio Hub</h1>
          <p>Unified Personal Net-Worth Tracker</p>
        </div>
        <div className="header-actions">
          {portfolio && (
            <div className={`status-badge ${portfolio.kite_connected ? 'status-connected' : 'status-disconnected'}`}>
              <span style={{ 
                width: 8, height: 8, borderRadius: '50%', 
                background: portfolio.kite_connected ? 'var(--emerald)' : 'var(--rose)'
              }}></span>
              <span>Zerodha: {portfolio.kite_connected ? 'Connected' : 'Disconnected'}</span>
            </div>
          )}
          
          {!portfolio?.kite_connected && (
            <button className="btn btn-primary" onClick={handleKiteConnect}>
              <RefreshCw size={16} /> Reconnect Zerodha
            </button>
          )}

          <button className="btn btn-secondary" onClick={handleLogout} title="Logout">
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {loading && !portfolio ? (
        <div className="glass chart-card" style={{ justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
          <RefreshCw className="animate-spin text-indigo-500" size={32} />
          <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Gathering portfolio intelligence...</p>
        </div>
      ) : error ? (
        <div className="glass chart-card" style={{ justifyContent: 'center', alignItems: 'center', borderColor: 'var(--rose)' }}>
          <AlertCircle size={40} className="text-red-500" style={{ color: 'var(--rose)', marginBottom: '1rem' }} />
          <h3>Retrieval Error</h3>
          <p style={{ color: 'var(--text-secondary)', margin: '0.5rem 0' }}>{error}</p>
          <button className="btn btn-primary" onClick={() => fetchPortfolio()}>Retry Fetch</button>
        </div>
      ) : (
        <>
          {/* Metrics Grid */}
          <div className="metrics-grid">
            <div className="glass metric-card networth">
              <div className="metric-label">Total Net Worth</div>
              <div className="metric-value">{formatCurrency(portfolio.net_worth)}</div>
              <div className="metric-change" style={{ color: 'var(--text-secondary)' }}>
                Across stocks, funds, FDs & gold
              </div>
            </div>

            <div className="glass metric-card invested">
              <div className="metric-label">Invested Capital</div>
              <div className="metric-value">{formatCurrency(portfolio.total_invested)}</div>
              <div className="metric-change" style={{ color: 'var(--text-secondary)' }}>
                Manual deposits & purchase averages
              </div>
            </div>

            <div className="glass metric-card pnl-pos">
              <div className="metric-label">Total Returns (P&L)</div>
              <div className="metric-value" style={{ color: portfolio.total_pnl >= 0 ? 'var(--emerald)' : 'var(--rose)' }}>
                {formatCurrency(portfolio.total_pnl)}
              </div>
              <div className={`metric-change ${portfolio.total_pnl >= 0 ? 'positive' : 'negative'}`}>
                {portfolio.total_pnl >= 0 ? <ArrowUpRight size={16} /> : <ArrowDownRight size={16} />}
                <span>{portfolio.total_pnl_percentage}% Unrealized Gain</span>
              </div>
            </div>
          </div>

          {/* Allocation & Trends Section */}
          <div className="main-layout">
            {/* Trend Chart */}
            <div className="glass chart-card">
              <div className="chart-header">
                <h3>Portfolio Net-Worth Valuation Trend</h3>
                <BarChart3 size={18} className="text-muted" style={{ color: 'var(--text-muted)' }} />
              </div>
              <div style={{ flexGrow: 1, minHeight: 300 }}>
                {portfolio.trend && portfolio.trend.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={portfolio.trend}>
                      <defs>
                        <linearGradient id="networthColor" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="rgba(255,255,255,0.03)" vertical={false} />
                      <XAxis 
                        dataKey="date" 
                        stroke="var(--text-muted)" 
                        fontSize={11} 
                        tickLine={false}
                        tickFormatter={(tick) => {
                          const d = new Date(tick);
                          return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
                        }}
                      />
                      <YAxis 
                        stroke="var(--text-muted)" 
                        fontSize={11} 
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(val) => {
                          if (val >= 10000000) return `₹${(val / 10000000).toFixed(1)}Cr`;
                          if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
                          if (val >= 1000) return `₹${(val / 1000).toFixed(0)}k`;
                          return `₹${val}`;
                        }}
                      />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: 'var(--bg-secondary)', 
                          borderColor: 'var(--border-color)',
                          borderRadius: '12px',
                          color: 'var(--text-primary)'
                        }}
                        labelFormatter={(label) => new Date(label).toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' })}
                        formatter={(val) => [formatCurrency(val), 'Net Worth']}
                      />
                      <Area type="monotone" dataKey="total_value" stroke="var(--primary)" strokeWidth={2} fillOpacity={1} fill="url(#networthColor)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', color: 'var(--text-muted)' }}>
                    Valuation data trends will start generating tonight after snapshot trigger.
                  </div>
                )}
              </div>
            </div>

            {/* Asset Allocation Chart */}
            <div className="glass chart-card">
              <div className="chart-header">
                <h3>Asset Allocation</h3>
                <Wallet size={18} style={{ color: 'var(--text-muted)' }} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'space-around' }}>
                <div style={{ height: 180 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={[
                          { name: 'Stocks', value: portfolio.allocation.stocks },
                          { name: 'Mutual Funds', value: portfolio.allocation.mutual_funds },
                          { name: 'Fixed Deposits', value: portfolio.allocation.fixed_deposits },
                          { name: 'Gold', value: portfolio.allocation.gold }
                        ].filter(item => item.value > 0)}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={4}
                        dataKey="value"
                      >
                        {[
                          { name: 'Stocks', value: portfolio.allocation.stocks },
                          { name: 'Mutual Funds', value: portfolio.allocation.mutual_funds },
                          { name: 'Fixed Deposits', value: portfolio.allocation.fixed_deposits },
                          { name: 'Gold', value: portfolio.allocation.gold }
                        ].filter(item => item.value > 0).map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(val) => formatCurrency(val)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="allocation-list">
                  {[
                    { name: 'Stocks', value: portfolio.allocation.stocks, icon: <Coins size={14} />, pct: portfolio.allocation_percentage.stocks, color: CHART_COLORS[0] },
                    { name: 'Mutual Funds', value: portfolio.allocation.mutual_funds, icon: <TrendingUp size={14} />, pct: portfolio.allocation_percentage.mutual_funds, color: CHART_COLORS[1] },
                    { name: 'Fixed Deposits', value: portfolio.allocation.fixed_deposits, icon: <Landmark size={14} />, pct: portfolio.allocation_percentage.fixed_deposits, color: CHART_COLORS[2] },
                    { name: 'Gold', value: portfolio.allocation.gold, icon: <Coins size={14} />, pct: portfolio.allocation_percentage.gold, color: CHART_COLORS[3] }
                  ].map((item, idx) => (
                    <div className="allocation-item" key={item.name}>
                      <div className="alloc-icon" style={{ backgroundColor: item.color }}></div>
                      <div className="alloc-details">
                        <div className="alloc-name">{item.name}</div>
                        <div className="alloc-bar-bg">
                          <div className="alloc-bar-fill" style={{ width: `${item.pct}%`, backgroundColor: item.color }}></div>
                        </div>
                      </div>
                      <div className="alloc-values">
                        <div className="alloc-value">{formatCurrency(item.value)}</div>
                        <div className="alloc-pct">{item.pct}%</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Details Tables */}
          <div className="glass table-card">
            <div className="table-header">
              <div className="tabs-container">
                <button 
                  className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
                  onClick={() => setActiveTab('overview')}
                >
                  Holdings Overview
                </button>
                <button 
                  className={`tab-btn ${activeTab === 'stocks' ? 'active' : ''}`}
                  onClick={() => setActiveTab('stocks')}
                >
                  Stocks ({portfolio.assets.stocks.length})
                </button>
                <button 
                  className={`tab-btn ${activeTab === 'mfs' ? 'active' : ''}`}
                  onClick={() => setActiveTab('mfs')}
                >
                  Mutual Funds ({portfolio.assets.mutual_funds.length})
                </button>
                <button 
                  className={`tab-btn ${activeTab === 'manual' ? 'active' : ''}`}
                  onClick={() => setActiveTab('manual')}
                >
                  FD & Gold ({portfolio.assets.fixed_deposits.length + portfolio.assets.gold.length})
                </button>
                <button 
                  className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
                  onClick={() => setActiveTab('analytics')}
                >
                  Risk & Analytics
                </button>
              </div>
              
              {activeTab === 'manual' && (
                <button className="btn btn-primary" onClick={() => { setEditingAsset(null); setShowAssetModal(true); }}>
                  <Plus size={16} /> Add Asset
                </button>
              )}
            </div>

            {/* TAB: Overview */}
            {activeTab === 'overview' && (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Asset</th>
                      <th>Class</th>
                      <th className="text-right">Invested Value</th>
                      <th className="text-right">Current Value</th>
                      <th className="text-right">Gain / Loss</th>
                      <th className="text-right">Returns</th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Combine top assets from each category to show on overview */}
                    {[
                      ...portfolio.assets.stocks.slice(0, 3).map(x => ({ ...x, type: 'Stock', key: x.symbol })),
                      ...portfolio.assets.mutual_funds.slice(0, 3).map(x => ({ ...x, type: 'Mutual Fund', key: x.isin })),
                      ...portfolio.assets.fixed_deposits.slice(0, 2).map(x => ({ ...x, type: 'Fixed Deposit', key: x.id, symbol: 'FD', average_price: x.principal, invested_value: x.principal })),
                      ...portfolio.assets.gold.slice(0, 2).map(x => ({ ...x, type: 'Gold', key: x.id, symbol: 'Gold', average_price: x.principal, invested_value: x.principal }))
                    ].map((item) => {
                      const gain = item.current_value - item.invested_value;
                      const pct = item.pnl_percentage !== undefined ? item.pnl_percentage : (gain / item.invested_value * 100);
                      return (
                        <tr key={item.key}>
                          <td>
                            <div className="symbol-name">
                              <span className="sym">{item.name}</span>
                              <span className="name">{item.symbol || item.isin}</span>
                            </div>
                          </td>
                          <td><span className="status-badge" style={{ padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}>{item.type}</span></td>
                          <td className="text-right">{formatCurrency(item.invested_value)}</td>
                          <td className="text-right">{formatCurrency(item.current_value)}</td>
                          <td className={`text-right ${gain >= 0 ? 'positive' : 'negative'}`}>
                            {gain >= 0 ? '+' : ''}{formatCurrency(gain)}
                          </td>
                          <td className={`text-right ${gain >= 0 ? 'positive' : 'negative'}`} style={{ fontWeight: 600 }}>
                            {gain >= 0 ? '+' : ''}{pct.toFixed(2)}%
                          </td>
                        </tr>
                      );
                    })}
                    {portfolio.assets.stocks.length === 0 && portfolio.assets.fixed_deposits.length === 0 && (
                      <tr>
                        <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem 0' }}>
                          No holdings data to display. Add manual assets or connect Zerodha Kite.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* TAB: Stocks */}
            {activeTab === 'stocks' && (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th className="text-right">Qty</th>
                      <th className="text-right">Avg Cost</th>
                      <th className="text-right">NSE Price</th>
                      <th className="text-right">Invested</th>
                      <th className="text-right">Current Value</th>
                      <th className="text-right">Returns (P&L)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolio.assets.stocks.map((stock) => (
                      <tr key={stock.symbol}>
                        <td>
                          <div className="symbol-name">
                            <span className="sym">{stock.symbol}</span>
                            <span className="name">{stock.name}</span>
                          </div>
                        </td>
                        <td className="text-right">{stock.quantity}</td>
                        <td className="text-right">{formatCurrency(stock.average_price)}</td>
                        <td className="text-right">{formatCurrency(stock.current_price)}</td>
                        <td className="text-right">{formatCurrency(stock.invested_value)}</td>
                        <td className="text-right">{formatCurrency(stock.current_value)}</td>
                        <td className={`text-right ${stock.pnl >= 0 ? 'positive' : 'negative'}`}>
                          <div style={{ fontWeight: 600 }}>{stock.pnl >= 0 ? '+' : ''}{formatCurrency(stock.pnl)}</div>
                          <div style={{ fontSize: '0.8rem' }}>{stock.pnl >= 0 ? '+' : ''}{stock.pnl_percentage}%</div>
                        </td>
                      </tr>
                    ))}
                    {portfolio.assets.stocks.length === 0 && (
                      <tr>
                        <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem 0' }}>
                          No equity stocks found in your Zerodha portfolio.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* TAB: Mutual Funds */}
            {activeTab === 'mfs' && (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Scheme / ISIN</th>
                      <th className="text-right">Units</th>
                      <th className="text-right">Avg Nav</th>
                      <th className="text-right">AMFI NAV</th>
                      <th className="text-right">Invested</th>
                      <th className="text-right">Current Value</th>
                      <th className="text-right">Returns (P&L)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolio.assets.mutual_funds.map((mf) => (
                      <tr key={mf.isin}>
                        <td>
                          <div className="symbol-name">
                            <span className="sym">{mf.name}</span>
                            <span className="name">{mf.isin}</span>
                          </div>
                        </td>
                        <td className="text-right">{mf.quantity.toFixed(3)}</td>
                        <td className="text-right">{formatCurrency(mf.average_price)}</td>
                        <td className="text-right">{formatCurrency(mf.current_price)}</td>
                        <td className="text-right">{formatCurrency(mf.invested_value)}</td>
                        <td className="text-right">{formatCurrency(mf.current_value)}</td>
                        <td className={`text-right ${mf.pnl >= 0 ? 'positive' : 'negative'}`}>
                          <div style={{ fontWeight: 600 }}>{mf.pnl >= 0 ? '+' : ''}{formatCurrency(mf.pnl)}</div>
                          <div style={{ fontSize: '0.8rem' }}>{mf.pnl >= 0 ? '+' : ''}{mf.pnl_percentage}%</div>
                        </td>
                      </tr>
                    ))}
                    {portfolio.assets.mutual_funds.length === 0 && (
                      <tr>
                        <td colSpan="7" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '3rem 0' }}>
                          No mutual fund holdings found in your Zerodha portfolio.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* TAB: Manual Assets */}
            {activeTab === 'manual' && (
              <div className="table-wrapper">
                {/* FD Sub-table */}
                <h4 style={{ margin: '1rem 0', fontFamily: 'Outfit, sans-serif' }}>Fixed Deposits</h4>
                <table style={{ marginBottom: '2.5rem' }}>
                  <thead>
                    <tr>
                      <th>Bank / Institution</th>
                      <th>Term Dates</th>
                      <th className="text-right">Rate</th>
                      <th className="text-right">Principal</th>
                      <th className="text-right">Accrued Value</th>
                      <th className="text-right">Accrued P&L</th>
                      <th className="text-right">Comp. XIRR</th>
                      <th style={{ width: 100 }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolio.assets.fixed_deposits.map((fd) => {
                      const gain = fd.current_value - fd.principal;
                      return (
                        <tr key={fd.id}>
                          <td><span className="sym">{fd.name}</span></td>
                          <td>
                            <div style={{ fontSize: '0.85rem' }}>Start: {new Date(fd.start_date).toLocaleDateString('en-IN')}</div>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Maturity: {new Date(fd.maturity_date).toLocaleDateString('en-IN')}</div>
                          </td>
                          <td className="text-right" style={{ fontWeight: 500 }}>{fd.interest_rate}% ({fd.compounding_frequency})</td>
                          <td className="text-right">{formatCurrency(fd.principal)}</td>
                          <td className="text-right" style={{ fontWeight: 600 }}>{formatCurrency(fd.current_value)}</td>
                          <td className="text-right positive">+{formatCurrency(gain)}</td>
                          <td className="text-right positive" style={{ fontWeight: 600 }}>{fd.xirr}%</td>
                          <td>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                              <button className="btn btn-secondary" style={{ padding: '0.4rem' }} onClick={() => handleEditAsset(fd)}>
                                <Edit3 size={14} />
                              </button>
                              <button className="btn btn-danger" style={{ padding: '0.4rem' }} onClick={() => handleDeleteAsset(fd.id)}>
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {portfolio.assets.fixed_deposits.length === 0 && (
                      <tr>
                        <td colSpan="8" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem 0' }}>
                          No Fixed Deposits recorded. Click "Add Asset" to record one.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>

                {/* Gold Sub-table */}
                <h4 style={{ margin: '1rem 0', fontFamily: 'Outfit, sans-serif' }}>Gold Portfolio</h4>
                <table>
                  <thead>
                    <tr>
                      <th>Asset Description</th>
                      <th>Form Factor</th>
                      <th className="text-right">Weight (grams)</th>
                      <th className="text-right">Investment Date</th>
                      <th className="text-right">Purchase Price</th>
                      <th className="text-right">Current Valuation</th>
                      <th className="text-right">Gain / Loss</th>
                      <th className="text-right">Comp. XIRR</th>
                      <th style={{ width: 100 }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {portfolio.assets.gold.map((gold) => {
                      const gain = gold.current_value - gold.principal;
                      const isGain = gain >= 0;
                      return (
                        <tr key={gold.id}>
                          <td><span className="sym">{gold.name}</span></td>
                          <td><span className="status-badge" style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}>{gold.gold_type}</span></td>
                          <td className="text-right">{gold.quantity}g</td>
                          <td>{new Date(gold.start_date).toLocaleDateString('en-IN')}</td>
                          <td className="text-right">{formatCurrency(gold.principal)}</td>
                          <td className="text-right" style={{ fontWeight: 600 }}>{formatCurrency(gold.current_value)}</td>
                          <td className={`text-right ${isGain ? 'positive' : 'negative'}`}>
                            {isGain ? '+' : ''}{formatCurrency(gain)}
                          </td>
                          <td className={`text-right ${isGain ? 'positive' : 'negative'}`} style={{ fontWeight: 600 }}>
                            {isGain ? '+' : ''}{gold.xirr}%
                          </td>
                          <td>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                              <button className="btn btn-secondary" style={{ padding: '0.4rem' }} onClick={() => handleEditAsset(gold)}>
                                <Edit3 size={14} />
                              </button>
                              <button className="btn btn-danger" style={{ padding: '0.4rem' }} onClick={() => handleDeleteAsset(gold.id)}>
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                    {portfolio.assets.gold.length === 0 && (
                      <tr>
                        <td colSpan="9" style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem 0' }}>
                          No Gold holdings recorded. Click "Add Asset" to record one.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}

            {/* TAB: Analytics */}
            {activeTab === 'analytics' && (
              <div className="table-wrapper" style={{ border: 'none', background: 'transparent', padding: '1rem' }}>
                {!analytics ? (
                  <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
                    Loading analytics data...
                  </div>
                ) : (
                  <div className="analytics-tab-content" style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                    
                    {/* Diagnostic Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                      <div className="card glass border-blue" style={{ padding: '1.5rem', borderRadius: '12px' }}>
                        <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                          <Sliders size={20} className="text-blue" />
                          <h4 style={{ margin: 0 }}>Professional Diagnosis</h4>
                        </div>
                        <p style={{ fontSize: '0.85rem', lineHeight: '1.45', color: 'var(--text-muted)', margin: 0 }}>
                          Your portfolio contains structured classifications mapping direct stocks, mutual funds, and manual assets. 
                          Check the warning alerts below for concentration risks and leverage corrections to accumulate cleaner index and mutual fund compounding sleeves.
                        </p>
                      </div>

                      <div className="card glass" style={{ padding: '1.5rem', borderRadius: '12px' }}>
                        <h4 style={{ margin: '0 0 1rem 0' }}>Risk Warnings & Flags</h4>
                        {analytics.flags.length === 0 ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#10b981', fontSize: '0.85rem' }}>
                            <CheckCircle size={16} />
                            <span>No high or medium severity warning flags triggered.</span>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '200px', overflowY: 'auto' }}>
                            {analytics.flags.map((flag, idx) => (
                              <div key={idx} style={{ 
                                background: 'rgba(255,255,255,0.02)', 
                                padding: '0.75rem', 
                                borderRadius: '6px', 
                                borderLeft: `4px solid ${flag.severity === 'High' ? 'var(--rose)' : 'var(--amber)'}`
                              }}>
                                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.25rem' }}>
                                  <span className={`badge badge-${flag.severity.toLowerCase()}`} style={{ fontSize: '0.65rem' }}>{flag.severity}</span>
                                  <span style={{ fontSize: '0.8rem', fontWeight: '700' }}>{flag.title}</span>
                                </div>
                                <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>{flag.detail}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Chart & Tables Grid */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                      <div className="card glass" style={{ padding: '1.5rem', borderRadius: '12px' }}>
                        <h4 style={{ margin: '0 0 1rem 0' }}>Risk Bucket Allocations</h4>
                        <div style={{ minHeight: '220px' }}>
                          <ResponsiveContainer width="100%" height={220}>
                            <BarChart data={analytics.risk_buckets} layout="vertical" margin={{ left: 20, right: 10 }}>
                              <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                              <XAxis type="number" tickFormatter={(v) => `${v}%`} />
                              <YAxis dataKey="name" type="category" width={120} tick={{fontSize: 10}} />
                              <Tooltip formatter={(value) => `${parseFloat(value).toFixed(1)}%`} />
                              <Bar dataKey="weight" fill="#6366f1" radius={[0, 4, 4, 0]}>
                                {analytics.risk_buckets.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                                ))}
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      <div className="card glass" style={{ padding: '1.5rem', borderRadius: '12px' }}>
                        <h4 style={{ margin: '0 0 1rem 0' }}>Stress Test Shocks</h4>
                        <div style={{ overflowX: 'auto' }}>
                          <table className="dense-table" style={{ fontSize: '0.75rem' }}>
                            <thead>
                              <tr>
                                <th>Scenario</th>
                                <th>Shock Impact</th>
                                <th>Ending Value</th>
                              </tr>
                            </thead>
                            <tbody>
                              {analytics.stress_tests.map((st, i) => (
                                <tr key={i}>
                                  <td style={{ fontWeight: '600' }}>{st.scenario}</td>
                                  <td className={st.loss >= 0 ? 'pos' : 'neg'} style={{ fontWeight: '600' }}>
                                    ₹ {st.loss.toLocaleString('en-IN')} ({st.loss_pct.toFixed(2)}%)
                                  </td>
                                  <td>₹ {st.ending_value.toLocaleString('en-IN')}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>

                    {/* Holdings Action Table */}
                    <div className="card glass" style={{ padding: '1.5rem', borderRadius: '12px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                        <h4 style={{ margin: 0 }}>Detailed Holdings Actions</h4>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                          <div className="search-box" style={{ background: 'rgba(255,255,255,0.05)', padding: '0.3rem 0.6rem', width: '200px' }}>
                            <Search size={14} />
                            <input 
                              type="text" 
                              placeholder="Search symbol/sector..." 
                              value={analyticsSearch}
                              onChange={(e) => setAnalyticsSearch(e.target.value)}
                              style={{ fontSize: '0.8rem' }}
                            />
                          </div>
                          
                          <div className="filter-tabs" style={{ padding: '0.1rem' }}>
                            {["ALL", "Buy/Add", "Hold", "Trim", "Exit/Review"].map((tab) => (
                              <button 
                                key={tab} 
                                className={`filter-tab-btn ${analyticsRecFilter === tab ? 'active' : ''}`}
                                onClick={() => setAnalyticsRecFilter(tab)}
                                style={{ padding: '0.3rem 0.6rem', fontSize: '0.7rem' }}
                              >
                                {tab} {analytics.action_counts[tab] !== undefined && `(${analytics.action_counts[tab]})`}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="table-wrapper">
                        <table className="analysis-table" style={{ fontSize: '0.75rem' }}>
                          <thead>
                            <tr>
                              <th>Symbol</th>
                              <th>Sector</th>
                              <th>Risk Bucket</th>
                              <th>Weight</th>
                              <th>P&L</th>
                              <th>Recommendation</th>
                              <th>Value Thesis</th>
                              <th>Trade Recommendation</th>
                              <th>Pros / Cons</th>
                            </tr>
                          </thead>
                          <tbody>
                            {analytics.holdings
                              .filter(h => {
                                const matchSearch = h.symbol.toLowerCase().includes(analyticsSearch.toLowerCase()) || 
                                                    h.sector.toLowerCase().includes(analyticsSearch.toLowerCase());
                                const matchFilter = analyticsRecFilter === "ALL" || h.recommendation === analyticsRecFilter;
                                return matchSearch && matchFilter;
                              })
                              .map((h, i) => (
                                <tr key={i} className={`row-rec-${h.recommendation.toLowerCase().replace('/', '-')}`}>
                                  <td style={{ fontWeight: '700' }}>{h.symbol}</td>
                                  <td style={{ fontWeight: '600', color: 'var(--text-muted)' }}>{h.sector}</td>
                                  <td><span className="risk-bucket-badge">{h.risk_bucket}</span></td>
                                  <td style={{ fontWeight: '600' }}>{h.weight.toFixed(2)}%</td>
                                  <td className={h.pnl >= 0 ? 'pos' : 'neg'} style={{ fontWeight: '600' }}>
                                    ₹ {h.pnl.toLocaleString('en-IN')} ({h.pnl_percentage.toFixed(2)}%)
                                  </td>
                                  <td>
                                    <span className={`badge-rec badge-rec-${h.recommendation.toLowerCase().replace('/', '-')}`}>
                                      {h.recommendation}
                                    </span>
                                  </td>
                                  <td>{h.value_case}</td>
                                  <td>{h.trade_case}</td>
                                  <td>
                                    <div className="pros-cons">
                                      <span className="pos-bullet" style={{ color: '#10b981', display: 'block' }}>✓ {h.pros}</span>
                                      <span className="neg-bullet" style={{ color: '#f43f5e', display: 'block' }}>✗ {h.cons}</span>
                                    </div>
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </div>

                  </div>
                )}
              </div>
            )}
          </div>

          {/* System Diagnostics, Tech Stack, & Security Audit Center */}
          <div className="card glass full-width-card" style={{ marginTop: '2rem', padding: '1.75rem', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.05)', textAlign: 'left', clear: 'both' }}>
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
        </>
      )}

      {/* Manual Asset Form Modal (Add/Edit) */}
      {showAssetModal && (
        <div className="form-modal-overlay" onClick={() => setShowAssetModal(false)}>
          <div className="glass modal-content fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingAsset ? 'Edit Asset Portfolio' : 'Add Manual Investment'}</h3>
              <button className="close-btn" onClick={() => setShowAssetModal(false)}><X size={20} /></button>
            </div>
            
            {/* Modal Asset Tabs */}
            {!editingAsset && (
              <div className="tabs-container" style={{ margin: 0 }}>
                <button 
                  className={`tab-btn ${modalAssetType === 'FD' ? 'active' : ''}`}
                  onClick={() => setModalAssetType('FD')}
                >
                  Fixed Deposit
                </button>
                <button 
                  className={`tab-btn ${modalAssetType === 'GOLD' ? 'active' : ''}`}
                  onClick={() => setModalAssetType('GOLD')}
                >
                  Gold
                </button>
              </div>
            )}

            <form onSubmit={handleSaveAsset} style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
              
              {/* FD FORM FIELDS */}
              {modalAssetType === 'FD' && (
                <>
                  <div className="form-group">
                    <label>Bank Name / Institution</label>
                    <input 
                      type="text" 
                      value={fdForm.name} 
                      onChange={(e) => setFdForm({...fdForm, name: e.target.value})}
                      placeholder="e.g. HDFC Bank, ICICI Bank"
                      required
                    />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Principal Amount (INR)</label>
                      <input 
                        type="number" 
                        step="any"
                        value={fdForm.principal} 
                        onChange={(e) => setFdForm({...fdForm, principal: e.target.value})}
                        placeholder="1,00,000"
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Interest Rate (% Per Annum)</label>
                      <input 
                        type="number" 
                        step="any"
                        value={fdForm.interest_rate} 
                        onChange={(e) => setFdForm({...fdForm, interest_rate: e.target.value})}
                        placeholder="7.5"
                        required
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label>Compounding Frequency</label>
                    <select 
                      value={fdForm.compounding_frequency}
                      onChange={(e) => setFdForm({...fdForm, compounding_frequency: e.target.value})}
                    >
                      <option value="Monthly">Monthly</option>
                      <option value="Quarterly">Quarterly (Indian Standard)</option>
                      <option value="Half-Yearly">Half-Yearly</option>
                      <option value="Yearly">Yearly</option>
                      <option value="Cumulative">Cumulative</option>
                    </select>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Start Date</label>
                      <input 
                        type="date" 
                        value={fdForm.start_date} 
                        onChange={(e) => setFdForm({...fdForm, start_date: e.target.value})}
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Maturity Date</label>
                      <input 
                        type="date" 
                        value={fdForm.maturity_date} 
                        onChange={(e) => setFdForm({...fdForm, maturity_date: e.target.value})}
                        required
                      />
                    </div>
                  </div>
                </>
              )}

              {/* GOLD FORM FIELDS */}
              {modalAssetType === 'GOLD' && (
                <>
                  <div className="form-group">
                    <label>Gold Description</label>
                    <input 
                      type="text" 
                      value={goldForm.name} 
                      onChange={(e) => setGoldForm({...goldForm, name: e.target.value})}
                      placeholder="e.g. SGB 2023 Series I, Physical Gold Coins"
                      required
                    />
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Weight (Grams)</label>
                      <input 
                        type="number" 
                        step="any"
                        value={goldForm.quantity} 
                        onChange={(e) => setGoldForm({...goldForm, quantity: e.target.value})}
                        placeholder="e.g. 10, 50"
                        required
                      />
                    </div>
                    <div className="form-group">
                      <label>Total Purchase Price (INR)</label>
                      <input 
                        type="number" 
                        step="any"
                        value={goldForm.principal} 
                        onChange={(e) => setGoldForm({...goldForm, principal: e.target.value})}
                        placeholder="Total investment value"
                        required
                      />
                    </div>
                  </div>

                  <div className="form-row">
                    <div className="form-group">
                      <label>Gold Type</label>
                      <select 
                        value={goldForm.gold_type}
                        onChange={(e) => setGoldForm({...goldForm, gold_type: e.target.value})}
                      >
                        <option value="PHYSICAL">Physical (Coins/Jewelry)</option>
                        <option value="SGB">Sovereign Gold Bond (SGB)</option>
                        <option value="DIGITAL">Digital Gold / ETF</option>
                      </select>
                    </div>
                    <div className="form-group">
                      <label>Investment Date</label>
                      <input 
                        type="date" 
                        value={goldForm.start_date} 
                        onChange={(e) => setGoldForm({...goldForm, start_date: e.target.value})}
                        required
                      />
                    </div>
                  </div>
                </>
              )}

              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAssetModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Changes
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

    </div>
  );
}
