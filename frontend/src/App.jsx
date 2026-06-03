import React, { useState, useEffect, useRef } from 'react';
import { 
  TrendingDown, 
  TrendingUp, 
  Bell, 
  Plus, 
  Activity, 
  Trash2, 
  ExternalLink, 
  RefreshCw, 
  Settings, 
  Grid, 
  Layers, 
  Database, 
  Clock,
  Sparkles,
  AlertCircle,
  Volume2
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid 
} from 'recharts';

const API_BASE = window.location.hostname === 'localhost' 
  ? 'http://localhost:8001' 
  : `http://${window.location.hostname}:8001`;

const WS_BASE = window.location.hostname === 'localhost' 
  ? 'ws://localhost:8001/ws' 
  : `ws://${window.location.hostname}:8001/ws`;

export default function App() {
  const [sneakers, setSneakers] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [filter, setFilter] = useState('all');
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [selectedSneaker, setSelectedSneaker] = useState(null);
  const [detailedHistory, setDetailedHistory] = useState([]);
  
  // Form states
  const [url, setUrl] = useState('');
  const [size, setSize] = useState('9.5');
  const [targetPrice, setTargetPrice] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Settings Edit states
  const [editTargetPrice, setEditTargetPrice] = useState('');
  const [editAlertEnabled, setEditAlertEnabled] = useState(true);

  // Connection State
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef(null);

  // Audio for alerts
  const playAlertSound = () => {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5 note
      osc.frequency.exponentialRampToValueAtTime(1200, audioCtx.currentTime + 0.15);
      
      gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.3);
      
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      
      osc.start();
      osc.stop(audioCtx.currentTime + 0.3);
    } catch (e) {
      console.warn("Audio Context blocked by browser auto-play policy");
    }
  };

  // Fetch initial data
  useEffect(() => {
    fetchSneakers();
    fetchNotifications();
    setupWebSocket();
    return () => {
      if (ws.current) ws.current.close();
    };
  }, []);

  const fetchSneakers = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/sneakers`);
      if (res.ok) {
        const data = await res.json();
        setSneakers(data);
      }
    } catch (err) {
      console.error("Failed to fetch sneakers:", err);
    }
  };

  const fetchNotifications = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/notifications`);
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
      }
    } catch (err) {
      console.error("Failed to fetch notifications:", err);
    }
  };

  // WebSockets setup
  const setupWebSocket = () => {
    const connect = () => {
      console.log("[WS] Connecting to:", WS_BASE);
      const socket = new WebSocket(WS_BASE);
      
      socket.onopen = () => {
        console.log("[WS] Connected successfully.");
        setIsConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const { type, data } = JSON.parse(event.data);
          console.log("[WS] Received event:", type);
          
          if (type === 'SNEAKER_ADDED') {
            setSneakers(prev => [data, ...prev]);
          } 
          else if (type === 'SNEAKER_UPDATED') {
            setSneakers(prev => prev.map(s => s.id === data.id ? data : s));
            // Update details modal if active
            setSelectedSneaker(curr => {
              if (curr && curr.id === data.id) {
                // Fetch updated history
                fetchSneakerHistory(data.id);
                return { ...curr, ...data };
              }
              return curr;
            });
          }
          else if (type === 'SNEAKER_DELETED') {
            setSneakers(prev => prev.filter(s => s.id !== data.id));
            setIsDetailOpen(curr => {
              if (selectedSneaker && selectedSneaker.id === data.id) {
                return false;
              }
              return curr;
            });
          }
          else if (type === 'NEW_NOTIFICATION') {
            setNotifications(prev => [data, ...prev]);
            playAlertSound();
          }
        } catch (e) {
          console.error("Error processing websocket payload:", e);
        }
      };

      socket.onclose = () => {
        console.warn("[WS] Socket closed. Reconnecting in 3s...");
        setIsConnected(false);
        setTimeout(connect, 3000);
      };

      socket.onerror = (err) => {
        console.error("[WS] Socket error:", err);
        socket.close();
      };
      
      ws.current = socket;
    };
    
    connect();
  };

  const fetchSneakerHistory = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/api/sneakers/${id}/history`);
      if (res.ok) {
        const data = await res.json();
        const formatted = data.map(h => ({
          price: h.price,
          date: new Date(h.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' })
        }));
        setDetailedHistory(formatted);
      }
    } catch (err) {
      console.error("Failed to fetch history:", err);
    }
  };

  // Handlers
  const handleAddSneaker = async (e) => {
    e.preventDefault();
    setFormError('');
    setIsSubmitting(true);
    
    try {
      const res = await fetch(`${API_BASE}/api/sneakers`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, size, target_price: targetPrice ? parseFloat(targetPrice) : null })
      });
      
      if (res.ok) {
        setUrl('');
        setTargetPrice('');
        setIsAddOpen(false);
      } else {
        const errData = await res.json();
        setFormError(errData.detail || "Failed to start tracking.");
      }
    } catch (err) {
      setFormError("Server connection failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateAlertSettings = async (e) => {
    e.preventDefault();
    if (!selectedSneaker) return;
    
    try {
      const res = await fetch(`${API_BASE}/api/sneakers/${selectedSneaker.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_price: parseFloat(editTargetPrice), is_active: editAlertEnabled })
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedSneaker(updated);
      }
    } catch (err) {
      console.error("Failed to update settings:", err);
    }
  };

  const handleDeleteSneaker = async (id) => {
    if (!confirm("Are you sure you want to stop tracking this sneaker?")) return;
    
    try {
      const res = await fetch(`${API_BASE}/api/sneakers/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setIsDetailOpen(false);
      }
    } catch (err) {
      console.error("Failed to delete sneaker:", err);
    }
  };

  const handleForceCheck = async (id) => {
    try {
      await fetch(`${API_BASE}/api/sneakers/${id}/check`, { method: 'POST' });
    } catch (err) {
      console.error("Failed to trigger check:", err);
    }
  };

  const handleMarkNotificationsRead = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/notifications/read`, { method: 'POST' });
      if (res.ok) {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      }
    } catch (err) {
      console.error("Failed to clear notifications:", err);
    }
  };

  const openDetails = (sneaker) => {
    setSelectedSneaker(sneaker);
    setEditTargetPrice(sneaker.target_price);
    setEditAlertEnabled(sneaker.is_active);
    fetchSneakerHistory(sneaker.id);
    setIsDetailOpen(true);
  };

  // Calculations for Stats
  const totalTracked = sneakers.length;
  const activeDrops = sneakers.filter(s => s.status === 'Dropped').length;
  const maxSavings = sneakers.reduce((max, s) => {
    const discount = s.original_price - s.current_price;
    const savingsPct = discount > 0 ? (discount / s.original_price) * 100 : 0;
    return savingsPct > max ? savingsPct : max;
  }, 0);

  // Filters mapping
  const filteredSneakers = sneakers.filter(s => {
    if (filter === 'dropped') return s.status === 'Dropped';
    if (filter === 'Simulated Crawler') return s.updates_type === 'Simulated Crawler';
    if (filter === 'Live Scraper') return s.updates_type === 'Live Scraper';
    return true;
  });

  const unreadCount = notifications.filter(n => !n.read).length;

  // Custom SVG Sparkline Component
  const Sparkline = ({ points }) => {
    if (!points || points.length < 2) return null;
    
    const prices = points.map(p => p.price);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    const range = max - min || 1;
    
    const width = 120;
    const height = 30;
    const padding = 2;
    
    const coordinates = points.map((p, index) => {
      const x = padding + (index / (points.length - 1)) * (width - 2 * padding);
      const y = padding + (1 - (p.price - min) / range) * (height - 2 * padding);
      return `${x},${y}`;
    }).join(' ');

    const strokeColor = points[points.length - 1].price < points[0].price ? '#00ff88' : '#646a7d';
    
    return (
      <svg width={width} height={height} className="overflow-visible">
        <polyline
          fill="none"
          stroke={strokeColor}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          points={coordinates}
        />
      </svg>
    );
  };

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="flex justify-between items-center px-6 py-4 bg-app/80 backdrop-blur-md border-b border-white/5 sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <span className="text-3xl filter drop-shadow-[0_0_8px_#00f0ff]">⚡</span>
          <h1 className="font-display font-extrabold text-2xl tracking-tight bg-gradient-to-r from-white to-neoncyan bg-clip-text text-transparent">
            SoleSentry Pro
          </h1>
        </div>

        <div className="flex items-center gap-4">
          {/* Notifications Trigger */}
          <div className="relative group">
            <button 
              id="notification-bell-btn"
              popovertarget="notifications-popover"
              className="p-2 rounded-lg bg-white/5 border border-white/5 text-gray-400 hover:border-neoncyan hover:text-white transition-all duration-200 relative"
              onClick={handleMarkNotificationsRead}
            >
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-neonred text-white font-bold text-[10px] w-4.5 h-4.5 rounded-full flex items-center justify-center border border-[#08090d]">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* Notifications Popover */}
            <div 
              id="notifications-popover" 
              popover="true" 
              className="glass-popover w-[360px] p-4 rounded-xl shadow-2xl mt-2 inset-auto right-6"
            >
              <div className="flex justify-between items-center border-b border-white/5 pb-2 mb-3">
                <h3 className="font-display font-bold text-sm">Recent Alerts</h3>
                <span className="text-[10px] text-gray-500 flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-neonemerald' : 'bg-neonred'}`}></span>
                  {isConnected ? 'Real-time active' : 'Offline'}
                </span>
              </div>
              
              <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">
                {notifications.length === 0 ? (
                  <p className="text-xs text-gray-500 text-center py-4">No recent price drops</p>
                ) : (
                  notifications.map(n => (
                    <div key={n.id} className={`flex gap-2.5 p-2 rounded-lg border text-xs items-center transition-all ${n.read ? 'bg-white/[0.01] border-white/5' : 'bg-neoncyan/5 border-neoncyan/20'}`}>
                      <div className="flex-1">
                        <p className="text-gray-300 font-medium leading-normal">{n.message}</p>
                        <span className="text-[9px] text-gray-500 block mt-1">{new Date(n.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          <button 
            className="btn btn-primary bg-gradient-to-r from-neoncyan to-blue-500 text-black font-semibold text-sm px-4 py-2 rounded-lg flex items-center gap-1.5 shadow-neon hover:shadow-[0_0_20px_rgba(0,240,255,0.4)] transition-all duration-200"
            onClick={() => setIsAddOpen(true)}
          >
            <Plus className="w-5 h-5 stroke-[2.5]" />
            <span>Track Sneaker</span>
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 flex flex-col gap-8">
        
        {/* Stats Grid */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass-card p-6 rounded-2xl flex items-center gap-4 hover:border-neoncyan/30 hover:shadow-neon transition-all duration-300">
            <span className="text-3xl p-3 bg-white/5 rounded-xl">👟</span>
            <div>
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Tracked Items</span>
              <h2 className="font-display font-extrabold text-3xl mt-0.5">{totalTracked}</h2>
            </div>
          </div>

          <div className="glass-card p-6 rounded-2xl flex items-center gap-4 hover:border-neonemerald/30 hover:shadow-neongreen transition-all duration-300">
            <span className="text-3xl p-3 bg-white/5 rounded-xl">🔥</span>
            <div>
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Price Drops</span>
              <h2 className="font-display font-extrabold text-3xl mt-0.5 text-neonemerald">{activeDrops}</h2>
            </div>
          </div>

          <div className="glass-card p-6 rounded-2xl flex items-center gap-4 hover:border-neonpurple/30 hover:shadow-[0_0_15px_rgba(189,0,255,0.25)] transition-all duration-300">
            <span className="text-3xl p-3 bg-white/5 rounded-xl">💎</span>
            <div>
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Max Savings</span>
              <h2 className="font-display font-extrabold text-3xl mt-0.5 text-neonpurple">{maxSavings.toFixed(0)}%</h2>
            </div>
          </div>
        </section>

        {/* Dashboard Split Body */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-8 items-start">
          
          {/* Watchlist Grid */}
          <section className="flex flex-col gap-5">
            <div className="flex justify-between items-center">
              <h2 className="font-display font-bold text-xl flex items-center gap-2">
                <Grid className="w-5 h-5 text-neoncyan" /> Watchlist
              </h2>
              
              <div className="flex gap-1.5 bg-white/5 p-1 border border-white/5 rounded-lg text-xs">
                <button 
                  className={`px-3 py-1.5 rounded-md font-semibold ${filter === 'all' ? 'bg-white/10 text-neoncyan' : 'text-gray-400 hover:text-white'}`}
                  onClick={() => setFilter('all')}
                >
                  All
                </button>
                <button 
                  className={`px-3 py-1.5 rounded-md font-semibold ${filter === 'dropped' ? 'bg-white/10 text-neoncyan' : 'text-gray-400 hover:text-white'}`}
                  onClick={() => setFilter('dropped')}
                >
                  Drops
                </button>
                <button 
                  className={`px-3 py-1.5 rounded-md font-semibold ${filter === 'Live Scraper' ? 'bg-white/10 text-neoncyan' : 'text-gray-400 hover:text-white'}`}
                  onClick={() => setFilter('Live Scraper')}
                >
                  Live
                </button>
                <button 
                  className={`px-3 py-1.5 rounded-md font-semibold ${filter === 'Simulated Crawler' ? 'bg-white/10 text-neoncyan' : 'text-gray-400 hover:text-white'}`}
                  onClick={() => setFilter('Simulated Crawler')}
                >
                  Simulated
                </button>
              </div>
            </div>

            {filteredSneakers.length === 0 ? (
              <div className="glass-card p-12 text-center rounded-2xl flex flex-col items-center gap-3">
                <AlertCircle className="w-8 h-8 text-gray-500" />
                <p className="text-sm text-gray-400">No sneakers found matching this filter.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {filteredSneakers.map(s => (
                  <div 
                    key={s.id}
                    className="glass-card rounded-2xl overflow-hidden group hover:border-neoncyan/40 hover:shadow-neon transition-all duration-300 flex flex-col h-full"
                  >
                    {/* Card Image */}
                    <div className="relative aspect-[16/10] overflow-hidden bg-black/25">
                      <img 
                        src={s.image} 
                        alt={s.name} 
                        className="absolute inset-0 w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                      />
                      <span className="absolute top-3 left-3 bg-black/75 backdrop-blur-sm border border-white/10 text-[9px] font-bold uppercase tracking-wider px-2 py-1 rounded">
                        {s.store}
                      </span>
                      <span className={`absolute top-3 right-3 text-[9px] font-semibold px-2 py-1 rounded border ${s.updates_type === 'Live Scraper' ? 'bg-neoncyan/15 border-neoncyan/40 text-cyan-200' : 'bg-neonpurple/15 border-neonpurple/40 text-purple-200'}`}>
                        {s.updates_type === 'Live Scraper' ? 'Live' : 'Simulated'}
                      </span>
                    </div>

                    {/* Card Body */}
                    <div className="p-5 flex flex-col flex-1">
                      <span className="text-[10px] font-bold text-neoncyan tracking-widest uppercase mb-1">{s.brand}</span>
                      <h3 className="font-semibold text-[15px] leading-snug line-clamp-2 h-[2.5rem] mb-4">{s.name}</h3>
                      
                      {/* Sparkline Visual */}
                      <div className="flex justify-between items-center my-3 bg-black/10 p-2 rounded-lg border border-white/5">
                        <span className="text-[9px] text-gray-500 uppercase font-semibold">Trend</span>
                        <Sparkline points={s.history} />
                      </div>

                      <div className="flex justify-between items-center mt-auto pt-4 border-t border-white/5">
                        <div>
                          <span className="text-[9px] text-gray-500 uppercase block leading-none">Current</span>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span className={`font-display font-bold text-base ${s.status === 'Dropped' ? 'text-neonemerald' : s.status === 'Increased' ? 'text-neonred' : 'text-white'}`}>
                              ₹{s.current_price.toFixed(2)}
                            </span>
                            {s.original_price > s.current_price && (
                              <span className="text-xs text-gray-500 line-through">₹{s.original_price.toFixed(2)}</span>
                            )}
                          </div>
                        </div>

                        <div className={`text-[10px] font-medium flex items-center gap-1 px-2 py-1 rounded-lg border ${s.current_price <= s.target_price ? 'bg-neonemerald/10 border-neonemerald/35 text-neonemerald pulse-border' : 'bg-white/5 border-white/5 text-gray-400'}`}>
                          <span>Target: ₹{s.target_price.toFixed(0)}</span>
                        </div>
                      </div>

                      {/* Card Overlay Actions */}
                      <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-white/5">
                        <button 
                          className="btn py-1.5 px-2 bg-white/5 border border-white/5 hover:bg-white/10 hover:border-white/20 text-xs rounded-lg flex items-center justify-center gap-1"
                          onClick={() => openDetails(s)}
                        >
                          <Settings className="w-3.5 h-3.5" /> Settings
                        </button>
                        <button 
                          className="btn py-1.5 px-2 bg-white/5 border border-white/5 hover:border-neoncyan/40 hover:text-neoncyan text-xs rounded-lg flex items-center justify-center gap-1"
                          onClick={() => handleForceCheck(s.id)}
                        >
                          <RefreshCw className="w-3.5 h-3.5" /> Check Price
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Deals Sidebar */}
          <aside className="glass-card p-5 rounded-2xl h-[560px] flex flex-col">
            <div className="flex justify-between items-center border-b border-white/5 pb-3">
              <h3 className="font-display font-bold text-sm flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-neonemerald" /> Ticker Alerts
              </h3>
              <span className="text-[10px] text-gray-400 flex items-center gap-1 bg-neonemerald/10 text-neonemerald px-2 py-0.5 rounded-full font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-neonemerald pulse-dot-anim"></span> Monitor Active
              </span>
            </div>
            
            <div className="flex-1 overflow-y-auto mt-4 pr-1 flex flex-col gap-3">
              {notifications.length === 0 ? (
                <p className="text-xs text-gray-500 text-center py-12">Waiting for price events...</p>
              ) : (
                notifications.map(n => {
                  const pct = Math.round(((n.old_price - n.new_price) / n.old_price) * 100);
                  return (
                    <div key={n.id} className="flex gap-2.5 p-2.5 bg-white/[0.01] hover:bg-white/[0.03] border border-white/5 rounded-xl transition-all duration-200">
                      <div className="flex flex-col flex-1 gap-1 text-[11px]">
                        <p className="text-gray-200 leading-snug">{n.message}</p>
                        <div className="flex justify-between items-center mt-1">
                          <span className="text-[9px] text-gray-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" /> {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                          <span className="bg-neonemerald/10 border border-neonemerald/30 text-neonemerald font-bold text-[10px] px-1.5 py-0.5 rounded">
                            -{pct > 0 ? pct : 5}%
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </aside>

        </div>
      </main>

      {/* Footer */}
      <footer className="text-center py-6 border-t border-white/5 text-gray-600 text-xs mt-12 bg-app">
        &copy; 2026 SoleSentry Pro. Distributed architecture built with FastAPI, PostgreSQL, Celery, Redis, and Playwright.
      </footer>

      {/* Add Sneaker Dialog */}
      {isAddOpen && (
        <dialog open className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm w-full h-full">
          <div className="glass-card w-[480px] max-w-full p-6 rounded-2xl shadow-2xl relative animate-slide-up-fade">
            <div className="flex justify-between items-center border-b border-white/5 pb-3 mb-4">
              <h2 className="font-display font-bold text-lg">Track New Sneaker</h2>
              <button className="text-gray-500 hover:text-white text-2xl" onClick={() => setIsAddOpen(false)}>&times;</button>
            </div>
            
            <form onSubmit={handleAddSneaker} className="flex flex-col gap-4 text-sm">
              <div className="flex flex-col gap-1.5">
                <label className="font-semibold text-gray-400 text-xs">Product Page URL</label>
                <input 
                  type="url" 
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="Paste URL (Nike, Adidas, StockX, GOAT, Foot Locker)" 
                  required
                  className="bg-white/3 p-3 rounded-lg border border-white/5 outline-none focus:border-neoncyan text-gray-200"
                />
                <span className="text-[10px] text-gray-500 leading-normal">
                  URLs matching supported retail sites use Playwright. Custom URL strings fallback to generic crawling patterns.
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1.5">
                  <label className="font-semibold text-gray-400 text-xs">US Size</label>
                  <select 
                    value={size}
                    onChange={(e) => setSize(e.target.value)}
                    className="bg-[#12141c] p-3 rounded-lg border border-white/5 outline-none focus:border-neoncyan text-gray-200"
                  >
                    {['7', '7.5', '8', '8.5', '9', '9.5', '10', '10.5', '11', '11.5', '12', '12.5', '13'].map(sz => (
                      <option key={sz} value={sz}>US {sz}</option>
                    ))}
                  </select>
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="font-semibold text-gray-400 text-xs">Target Alert Price (₹)</label>
                  <input 
                    type="number"
                    value={targetPrice}
                    onChange={(e) => setTargetPrice(e.target.value)}
                    placeholder="E.g. 150"
                    required
                    className="bg-white/3 p-3 rounded-lg border border-white/5 outline-none focus:border-neoncyan text-gray-200"
                  />
                </div>
              </div>

              {formError && (
                <div className="bg-neonred/10 border border-neonred/20 text-neonred text-xs p-3 rounded-lg flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              <div className="flex justify-end gap-3 mt-4 pt-4 border-t border-white/5">
                <button 
                  type="button" 
                  className="btn py-2 px-4 bg-white/5 border border-white/5 hover:bg-white/10 rounded-lg"
                  onClick={() => setIsAddOpen(false)}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  disabled={isSubmitting}
                  className="btn btn-primary bg-gradient-to-r from-neoncyan to-blue-500 hover:shadow-neon text-black font-semibold"
                >
                  {isSubmitting ? 'Configuring Scraper...' : 'Start Tracking'}
                </button>
              </div>
            </form>
          </div>
        </dialog>
      )}

      {/* Details Dialog */}
      {isDetailOpen && selectedSneaker && (
        <dialog open className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm w-full h-full">
          <div className="glass-card w-[840px] max-w-full p-6 rounded-2xl shadow-2xl relative animate-slide-up-fade">
            <div className="flex justify-between items-center border-b border-white/5 pb-3 mb-4">
              <h2 className="font-display font-bold text-lg">Product Details & Pricing</h2>
              <button className="text-gray-500 hover:text-white text-2xl" onClick={() => setIsDetailOpen(false)}>&times;</button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-[280px_1fr] gap-6 text-sm">
              {/* Left Column: Image, Info */}
              <div className="flex flex-col gap-4">
                <div className="relative aspect-square overflow-hidden bg-black/25 rounded-xl border border-white/5">
                  <img src={selectedSneaker.image} alt={selectedSneaker.name} className="absolute inset-0 w-full h-full object-cover" />
                </div>
                
                <div className="flex flex-col gap-2.5 bg-white/2 p-4 rounded-xl border border-white/5 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Store</span>
                    <span className="font-semibold text-gray-200">{selectedSneaker.store}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Brand</span>
                    <span className="font-semibold text-gray-200">{selectedSneaker.brand}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Size Watched</span>
                    <span className="font-semibold text-gray-200">US {selectedSneaker.size}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Mode</span>
                    <span className={`font-semibold ${selectedSneaker.updates_type === 'Live Scraper' ? 'text-neoncyan' : 'text-neonpurple'}`}>
                      {selectedSneaker.updates_type}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Checked</span>
                    <span className="font-semibold text-gray-400">
                      {new Date(selectedSneaker.last_checked).toLocaleTimeString()}
                    </span>
                  </div>
                </div>

                <a 
                  href={selectedSneaker.url} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="btn bg-white/5 border border-white/5 hover:bg-white/10 justify-center py-2.5 text-xs rounded-lg flex items-center gap-1.5"
                >
                  <span>Go to Shop Page</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

              {/* Right Column: Chart, Edit Alert */}
              <div className="flex flex-col gap-5">
                {/* Stats row */}
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-white/2 p-3 border border-white/5 rounded-xl text-center">
                    <span className="text-[10px] text-gray-500 uppercase block">Current</span>
                    <span className="font-display font-extrabold text-lg text-neoncyan">₹{selectedSneaker.current_price.toFixed(2)}</span>
                  </div>
                  <div className="bg-white/2 p-3 border border-white/5 rounded-xl text-center">
                    <span className="text-[10px] text-gray-500 uppercase block">Original</span>
                    <span className="font-display font-extrabold text-lg text-gray-300">₹{selectedSneaker.original_price.toFixed(2)}</span>
                  </div>
                  <div className="bg-white/2 p-3 border border-white/5 rounded-xl text-center">
                    <span className="text-[10px] text-gray-500 uppercase block">Lowest</span>
                    <span className="font-display font-extrabold text-lg text-neonemerald">
                      ₹{detailedHistory.length > 0 ? Math.min(...detailedHistory.map(h => h.price)).toFixed(2) : selectedSneaker.current_price.toFixed(2)}
                    </span>
                  </div>
                </div>

                {/* Graph */}
                <div className="h-[200px] bg-black/20 border border-white/5 rounded-xl p-3">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={detailedHistory}>
                      <defs>
                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#00f0ff" stopOpacity={0.25}/>
                          <stop offset="95%" stopColor="#00f0ff" stopOpacity={0.0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                      <XAxis dataKey="date" stroke="#666" fontSize={10} tickLine={false} />
                      <YAxis stroke="#666" fontSize={10} tickLine={false} domain={['auto', 'auto']} />
                      <Tooltip 
                        contentStyle={{ backgroundColor: '#12141c', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px' }}
                        labelStyle={{ fontSize: '10px', color: '#666' }}
                        itemStyle={{ fontSize: '12px', color: '#00f0ff', fontWeight: 'bold' }}
                      />
                      <Area type="monotone" dataKey="price" stroke="#00f0ff" strokeWidth={2} fillOpacity={1} fill="url(#colorPrice)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {/* Alert Editor Form */}
                <form onSubmit={handleUpdateAlertSettings} className="bg-white/2 p-4 rounded-xl border border-white/5 flex flex-col gap-4">
                  <h3 className="font-display font-bold text-sm">Target Threshold & Alerts</h3>
                  
                  <div className="grid grid-cols-2 gap-6 items-center">
                    <div className="flex flex-col gap-1">
                      <label className="text-[10px] text-gray-500 font-semibold uppercase">Alert Trigger Price (₹)</label>
                      <input 
                        type="number" 
                        value={editTargetPrice}
                        onChange={(e) => setEditTargetPrice(e.target.value)}
                        className="bg-[#12141c] p-2.5 rounded-lg border border-white/5 outline-none focus:border-neoncyan"
                        required
                      />
                    </div>
                    
                    <div className="flex justify-between items-center bg-black/10 p-3 rounded-lg border border-white/5">
                      <span className="text-[10px] text-gray-500 font-semibold uppercase">Alert Active</span>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input 
                          type="checkbox" 
                          checked={editAlertEnabled}
                          onChange={(e) => setEditAlertEnabled(e.target.checked)}
                          className="sr-only peer"
                        />
                        <div className="w-9 h-5 bg-white/10 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-neoncyan"></div>
                      </label>
                    </div>
                  </div>

                  <div className="flex justify-between items-center mt-2 border-t border-white/5 pt-3">
                    <button 
                      type="button" 
                      className="btn py-2 px-3 bg-neonred/10 border border-neonred/20 text-neonred hover:bg-neonred/20 text-xs rounded-lg flex items-center gap-1"
                      onClick={() => handleDeleteSneaker(selectedSneaker.id)}
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Stop Tracking
                    </button>
                    
                    <button 
                      type="submit" 
                      className="btn py-2 px-4 bg-neoncyan text-black hover:bg-cyan-400 font-bold text-xs rounded-lg"
                    >
                      Save Settings
                    </button>
                  </div>
                </form>
              </div>

            </div>
          </div>
        </dialog>
      )}

    </div>
  );
}
