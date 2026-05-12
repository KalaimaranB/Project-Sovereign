import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Users, 
  Database, 
  Cpu, 
  Terminal, 
  ArrowUpRight, 
  ShieldCheck, 
  RefreshCw, 
  Server,
  AlertTriangle,
  UploadCloud,
  DownloadCloud,
  Hammer
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid 
} from 'recharts';
import './App.css';

// ---------------------------------------------------------
// Types & Simulated Data Pools
// ---------------------------------------------------------

interface Log {
  id: string;
  timestamp: string;
  service: 'nas' | 'profile' | 'natneg';
  level: 'info' | 'warn' | 'error';
  message: string;
}

interface ChartPoint {
  time: string;
  pps: number;
  latency: number;
}

const RANDOM_IPS = ['192.168.1.45', '10.244.1.12', '24.15.88.230', '98.139.18.4', '172.217.7.14'];
const GAMES = ['mariokartwii', 'metroidprime', 'tetrisds', 'pokemonbw'];

const SIMULATED_MESSAGES = [
  { service: 'profile' as const, level: 'info' as const, msg: (ip: string, game: string) => `New stream opened from ${ip}` },
  { service: 'profile' as const, level: 'info' as const, msg: (ip: string, game: string) => `Processing COMMAND: login (gameid: ${game})` },
  { service: 'profile' as const, level: 'info' as const, msg: (ip: string, game: string) => `Auth success: generated profile token` },
  { service: 'natneg' as const, level: 'info' as const, msg: (ip: string, game: string) => `Received NN_INIT command from ${ip}` },
  { service: 'natneg' as const, level: 'info' as const, msg: (ip: string, game: string) => `Successfully mapped local address to public NAT port` },
  { service: 'nas' as const, level: 'info' as const, msg: (ip: string, game: string) => `POST /ac connection successful - 200 OK` },
  { service: 'nas' as const, level: 'info' as const, msg: (ip: string, game: string) => `GET /conntest triggered fallback response - ok` },
  { service: 'profile' as const, level: 'warn' as const, msg: (ip: string, game: string) => `High latent Redis lookup overhead detected` },
  { service: 'natneg' as const, level: 'warn' as const, msg: (ip: string, game: string) => `Retrying ADDR_CHECK handshake for ${ip}` },
  { service: 'nas' as const, level: 'error' as const, msg: (ip: string, game: string) => `User ${ip} attempted connection while marked banned!` }
];

// ---------------------------------------------------------
// Main Component
// ---------------------------------------------------------

export default function App() {
  // States
  const [activePlayers, setActivePlayers] = useState(142);
  const [pps, setPps] = useState(324);
  const [dbLatency, setDbLatency] = useState(8);
  const [cpuLoad, setCpuLoad] = useState(24.5);
  const [logs, setLogs] = useState<Log[]>([]);
  const [activeFilter, setActiveFilter] = useState<'all' | 'nas' | 'profile' | 'natneg'>('all');
  const [chartData, setChartData] = useState<ChartPoint[]>([]);
  
  const logEndRef = useRef<HTMLDivElement>(null);

  // Patcher Engine States
  const [romFile, setRomFile] = useState<File | null>(null);
  const [targetIp, setTargetIp] = useState('10.8.0.1');
  const [isDragging, setIsDragging] = useState(false);
  const [patchState, setPatchState] = useState<'idle' | 'processing' | 'success' | 'error'>('idle');
  const [patchFeedback, setPatchFeedback] = useState('');

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setRomFile(e.dataTransfer.files[0]);
      setPatchState('idle');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setRomFile(e.target.files[0]);
      setPatchState('idle');
    }
  };

  const triggerPatchProcess = async () => {
    if (!romFile) return;

    setPatchState('processing');
    setPatchFeedback('Compiling C Patcher buffer stream...');

    const payload = new FormData();
    payload.append('rom', romFile);
    payload.append('ip', targetIp);

    try {
      const apiHost = window.location.hostname;
      const response = await fetch(`http://${apiHost}:9999/api/patch`, {
        method: 'POST',
        body: payload
      });

      if (!response.ok) {
        const rawErr = await response.text();
        throw new Error(rawErr || 'Patcher boundary returned a critical fault.');
      }

      setPatchFeedback('Executing binary byte substitution...');
      
      // Ingestion of streamed output buffer
      const outputBlob = await response.blob();
      const blobUrl = window.URL.createObjectURL(outputBlob);

      // Dispatch instant browser download bridge
      const triggerLink = document.createElement('a');
      triggerLink.href = blobUrl;
      triggerLink.download = `patched_${romFile.name}`;
      document.body.appendChild(triggerLink);
      triggerLink.click();
      document.body.removeChild(triggerLink);
      window.URL.revokeObjectURL(blobUrl);

      setPatchState('success');
      setPatchFeedback('Replacement matrix complete. ROM download triggered!');
    } catch (error: any) {
      setPatchState('error');
      setPatchFeedback(error.message || 'Network failed to ingest payload.');
    }
  };

  // Initialize Chart Data with past window
  useEffect(() => {
    const initData: ChartPoint[] = [];
    for (let i = 15; i >= 0; i--) {
      const timeStr = new Date(Date.now() - i * 2000).toLocaleTimeString([], { hour12: false });
      initData.push({
        time: timeStr.slice(-8),
        pps: Math.floor(Math.random() * 100) + 250,
        latency: Math.floor(Math.random() * 5) + 5
      });
    }
    setChartData(initData);

    // Initial batch of logs
    const initialLogs: Log[] = [];
    for (let i = 0; i < 8; i++) {
      initialLogs.push(generateSimulatedLog());
    }
    setLogs(initialLogs);
  }, []);

  // Real-time Engine Simulator loop
  useEffect(() => {
    const interval = setInterval(() => {
      // 1. Tick Stats marginally
      setActivePlayers(prev => {
        const delta = Math.random() > 0.5 ? 1 : -1;
        const chance = Math.random() > 0.6 ? delta : 0;
        return Math.max(50, Math.min(500, prev + chance));
      });
      
      const nextPps = Math.floor(Math.random() * 120) + 280;
      setPps(nextPps);
      
      setDbLatency(Math.floor(Math.random() * 4) + 6);
      setCpuLoad(prev => {
        const walk = (Math.random() - 0.5) * 2;
        return Math.max(10, Math.min(80, Number((prev + walk).toFixed(1))));
      });

      // 2. Append dynamic chart point
      const timeStr = new Date().toLocaleTimeString([], { hour12: false }).slice(-8);
      setChartData(prev => [
        ...prev.slice(1),
        {
          time: timeStr,
          pps: nextPps,
          latency: Math.floor(Math.random() * 8) + 5
        }
      ]);

      // 3. 80% chance of a new log entry per tick
      if (Math.random() > 0.2) {
        setLogs(prev => [...prev.slice(-49), generateSimulatedLog()]);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // Auto-scroll logs terminal
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // Helper helper log builder
  function generateSimulatedLog(): Log {
    const template = SIMULATED_MESSAGES[Math.floor(Math.random() * SIMULATED_MESSAGES.length)];
    const ip = RANDOM_IPS[Math.floor(Math.random() * RANDOM_IPS.length)];
    const game = GAMES[Math.floor(Math.random() * GAMES.length)];
    const timestamp = new Date().toLocaleTimeString([], { hour12: false, fractionalSecondDigits: 3 } as any);
    return {
      id: Math.random().toString(36).substring(2, 9),
      timestamp,
      service: template.service,
      level: template.level,
      message: template.msg(ip, game)
    };
  }

  const filteredLogs = logs.filter(log => activeFilter === 'all' || log.service === activeFilter);

  return (
    <div className="app-container">
      
      {/* Top Navigation & SRE Branding */}
      <header className="dashboard-header glass-panel glow-border-hover">
        <div className="header-brand">
          <Activity className="text-gradient animate-pulse-glow" size={32} />
          <div>
            <h1 className="text-gradient">Sovereign Engine</h1>
            <p style={{fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px'}}>SRE OBSERVE STACK v1.0.0</p>
          </div>
          <span>LIVE MOCK TRAFFIC</span>
        </div>
        <div className="system-status">
          <div className="status-badge">
            <span className="status-dot"></span>
            HEALTHY
          </div>
          <div style={{display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '2px'}}>
            <span style={{fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)'}}>UPTIME</span>
            <span style={{fontFamily: 'var(--font-mono)', fontSize: '0.875rem', fontWeight: 600}}>482:12:33</span>
          </div>
        </div>
      </header>

      {/* Grid 1: Key Metric Quantities */}
      <div className="stats-grid">
        <div className="stat-card glass-panel glow-border-hover">
          <div className="stat-info">
            <span className="stat-label">Active Concurrent Players</span>
            <span className="stat-value">{activePlayers}</span>
            <span className="stat-trend trend-up"><ArrowUpRight size={14} /> 2.4% against baselines</span>
          </div>
          <div className="stat-icon"><Users size={24} /></div>
        </div>

        <div className="stat-card glass-panel glow-border-hover">
          <div className="stat-info">
            <span className="stat-label">Network Packet Velocity</span>
            <span className="stat-value" style={{color: 'var(--accent-cyan)'}}>{pps} <span style={{fontSize: '1rem', color: 'var(--text-muted)'}}>PPS</span></span>
            <span className="stat-trend trend-up"><ArrowUpRight size={14} /> Streaming Nominal</span>
          </div>
          <div className="stat-icon" style={{color: 'var(--accent-cyan)'}}><RefreshCw size={24} /></div>
        </div>

        <div className="stat-card glass-panel glow-border-hover">
          <div className="stat-info">
            <span className="stat-label">PostgreSQL Query Latency</span>
            <span className="stat-value" style={{color: 'var(--accent-green)'}}>{dbLatency} <span style={{fontSize: '1rem', color: 'var(--text-muted)'}}>ms</span></span>
            <span className="stat-trend trend-up"><ShieldCheck size={14} /> Performance Optimized</span>
          </div>
          <div className="stat-icon" style={{color: 'var(--accent-green)'}}><Database size={24} /></div>
        </div>

        <div className="stat-card glass-panel glow-border-hover">
          <div className="stat-info">
            <span className="stat-label">Cluster Engine Load</span>
            <span className="stat-value">{cpuLoad}<span style={{fontSize: '1.25rem'}}>%</span></span>
            <span className="stat-trend" style={{color: 'var(--text-muted)'}}><Server size={14} /> Pi 4 Node Core</span>
          </div>
          <div className="stat-icon"><Cpu size={24} /></div>
        </div>
      </div>

      {/* Grid 2: Charts & Monitoring Elements */}
      <div className="matrix-grid">
        
        {/* Chart Widget */}
        <div className="matrix-panel glass-panel">
          <div className="panel-header">
            <h2 className="panel-title"><Activity size={18} /> Protocol Pulse & Ingestion Bandwidth</h2>
            <span style={{fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)'}}>WINDOW: 30S</span>
          </div>
          
          <div style={{ flex: 1, width: '100%', marginTop: '1rem' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorPps" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
                <XAxis 
                  dataKey="time" 
                  stroke="var(--text-muted)" 
                  fontSize={10} 
                  tickLine={false} 
                  axisLine={false}
                />
                <YAxis 
                  stroke="var(--text-muted)" 
                  fontSize={10} 
                  tickLine={false} 
                  axisLine={false}
                  domain={['auto', 'auto']}
                />
                <Tooltip 
                  contentStyle={{ 
                    background: 'rgba(10, 10, 15, 0.95)', 
                    border: '1px solid var(--glass-border)',
                    borderRadius: '8px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: '12px'
                  }} 
                />
                <Area 
                  type="monotone" 
                  dataKey="pps" 
                  stroke="var(--accent-blue)" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorPps)" 
                  name="Packets/Sec"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Services Check */}
        <div className="matrix-panel glass-panel">
          <div className="panel-header">
            <h2 className="panel-title"><Server size={18} /> Node Component Matrix</h2>
          </div>
          <div className="service-status-list">
            <div className="svc-item">
              <div className="svc-meta">
                <span className="svc-name">Sovereign Profile Server</span>
                <span className="svc-port">EXPOSE: 28910 | METRICS: 9100</span>
              </div>
              <div className="svc-stats">
                <div style={{color: 'var(--accent-green)'}}>ONLINE</div>
                <div style={{fontSize: '0.7rem', color: 'var(--text-muted)'}}>{Math.floor(activePlayers * 0.6)} CONNS</div>
              </div>
            </div>

            <div className="svc-item">
              <div className="svc-meta">
                <span className="svc-name">Sovereign NatNeg Server</span>
                <span className="svc-port">EXPOSE: 27901 | METRICS: 9101</span>
              </div>
              <div className="svc-stats">
                <div style={{color: 'var(--accent-green)'}}>ONLINE</div>
                <div style={{fontSize: '0.7rem', color: 'var(--text-muted)'}}>SOCKET OK</div>
              </div>
            </div>

            <div className="svc-item">
              <div className="svc-meta">
                <span className="svc-name">Sovereign NAS Account Portal</span>
                <span className="svc-port">EXPOSE: 9000 | METRICS: 9102</span>
              </div>
              <div className="svc-stats">
                <div style={{color: 'var(--accent-green)'}}>ONLINE</div>
                <div style={{fontSize: '0.7rem', color: 'var(--text-muted)'}}>HTTP GW</div>
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Grid 3: Secure Zero-Touch ROM Patcher (UX Bridge) */}
      <section className="glass-panel glow-border-hover patcher-panel" style={{ padding: '1.5rem' }}>
        <div className="panel-header">
          <h2 className="panel-title"><Hammer size={18} className="text-gradient" /> Secure Appliance ROM Patcher Gateway</h2>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>ENGINE: nossl_patch_arm9.c</span>
        </div>

        <div className="patcher-grid">
          {/* Interactive Drag & Drop Layer */}
          <div 
            className={`dropzone ${isDragging ? 'dropzone-active' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => document.getElementById('rom-input-field')?.click()}
          >
            <input 
              type="file" 
              id="rom-input-field" 
              accept=".nds,.iso,.wbfs,.bin" 
              style={{ display: 'none' }} 
              onChange={handleFileChange}
            />
            {romFile ? (
              <>
                <ShieldCheck size={40} style={{ color: 'var(--accent-green)' }} />
                <div>
                  <p style={{ fontWeight: 600, fontSize: '0.95rem' }}>{romFile.name}</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {(romFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
                <button 
                  className="file-remove-btn" 
                  onClick={(e) => {
                    e.stopPropagation();
                    setRomFile(null);
                    setPatchState('idle');
                  }}
                >
                  REMOVE FILE
                </button>
              </>
            ) : (
              <>
                <UploadCloud size={40} className="text-gradient" />
                <div>
                  <p style={{ fontWeight: 600 }}>Drag & drop your Nintendo ROM file here</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Supports .NDS, .ISO, or Raw Binary Buffers
                  </p>
                </div>
                <span style={{
                  fontSize: '0.75rem',
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  padding: '4px 12px',
                  borderRadius: '4px',
                  marginTop: '0.5rem'
                }}>BROWSE FILES</span>
              </>
            )}
          </div>

          {/* Form Controls and Sub-State Execution Handler */}
          <div className="patcher-controls">
            <div className="patcher-input-group">
              <label className="patcher-label">Target WireGuard Gateway IP</label>
              <input 
                type="text" 
                className="patcher-input"
                value={targetIp}
                onChange={(e) => setTargetIp(e.target.value)}
                placeholder="e.g. 10.8.0.1"
              />
              <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                This redirects hardcoded 'nintendowifi.net' packets straight to your server.
              </p>
            </div>

            <button 
              className="patch-btn"
              disabled={!romFile || patchState === 'processing'}
              onClick={triggerPatchProcess}
            >
              {patchState === 'processing' ? (
                <>
                  <RefreshCw className="animate-spin" size={18} />
                  EXECUTING PATCH...
                </>
              ) : (
                <>
                  <DownloadCloud size={18} />
                  PATCH & DOWNLOAD ROM
                </>
              )}
            </button>

            {/* Async State Alerts */}
            {patchState !== 'idle' && (
              <div className={`patch-alert ${patchState === 'error' ? 'error' : patchState === 'success' ? 'success' : ''}`} style={{ 
                background: patchState === 'processing' ? 'rgba(79, 172, 254, 0.05)' : undefined,
                color: patchState === 'processing' ? 'var(--accent-cyan)' : undefined,
                border: patchState === 'processing' ? '1px solid rgba(79, 172, 254, 0.15)' : undefined
              }}>
                {patchFeedback}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Full Width Log Terminal */}
      <section className="glass-panel" style={{display: 'flex', flexDirection: 'column', padding: '1.5rem', gap: '1rem', height: '400px'}}>
        <div className="panel-header">
          <h2 className="panel-title"><Terminal size={18} /> Unified Centralized Logging Engine</h2>
          <div style={{fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', gap: '1.5rem'}}>
            <span style={{display: 'flex', alignItems: 'center', gap: '4px'}}>
              <AlertTriangle size={12} style={{color: 'var(--accent-red)'}}/> {logs.filter(l => l.level === 'error').length} ERRORS
            </span>
            <span>BUFFER: {logs.length}/50</span>
          </div>
        </div>

        <div className="log-console-container">
          <div className="console-toolbar">
            <div className="toolbar-buttons">
              <button className={`filter-btn ${activeFilter === 'all' ? 'active' : ''}`} onClick={() => setActiveFilter('all')}>ALL SERVICES</button>
              <button className={`filter-btn ${activeFilter === 'nas' ? 'active' : ''}`} onClick={() => setActiveFilter('nas')}>NAS</button>
              <button className={`filter-btn ${activeFilter === 'profile' ? 'active' : ''}`} onClick={() => setActiveFilter('profile')}>PROFILE</button>
              <button className={`filter-btn ${activeFilter === 'natneg' ? 'active' : ''}`} onClick={() => setActiveFilter('natneg')}>NATNEG</button>
            </div>
          </div>
          
          <div className="console-lines">
            {filteredLogs.map((log) => (
              <div key={log.id} className={`log-entry lvl-${log.level}`}>
                <span className="log-time">[{log.timestamp}]</span>
                <span className={`log-service srv-${log.service}`}>{log.service.toUpperCase()}</span>
                <span className="log-msg">{log.message}</span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </div>
      </section>

    </div>
  );
}
