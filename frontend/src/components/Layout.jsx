import React, { useEffect, useState } from 'react';
import { Outlet, NavLink } from 'react-router-dom';
import { ShieldCheck, CheckCircle2, LayoutDashboard, Search, GraduationCap } from 'lucide-react';
import { checkHealth, checkClusterStatus } from '../api/client';

const Layout = () => {
  const [healthStatus, setHealthStatus] = useState('offline');
  const [clusterStatus, setClusterStatus] = useState('offline');

  useEffect(() => {
    const fetchStatuses = async () => {
      try {
        const health = await checkHealth();
        if (health) setHealthStatus('online');
      } catch (err) {
        setHealthStatus('offline');
      }

      try {
        const cluster = await checkClusterStatus();
        if (cluster && cluster.ok) setClusterStatus('online');
      } catch (err) {
        setClusterStatus('offline');
      }
    };

    fetchStatuses();
    const interval = setInterval(fetchStatuses, 15000); // Check every 15s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="flex items-center gap-2">
            <ShieldCheck className="text-emerald" size={24} />
            <h1 className="font-serif">CertiChain</h1>
          </div>
          <p className="text-xs text-muted">Academic Credential System</p>
        </div>

        <nav className="sidebar-nav">
          <NavLink to="/admin" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <LayoutDashboard size={20} />
            <span>Admin Control</span>
          </NavLink>
          <NavLink to="/student/default_did" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <GraduationCap size={20} />
            <span>Student View</span>
          </NavLink>
          <NavLink to="/verify" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
            <Search size={20} />
            <span>Verify Hub</span>
          </NavLink>
        </nav>

        <div className="p-4 border-t" style={{ borderColor: 'var(--border-color)' }}>
          <div className="flex flex-col gap-2">
            <div className="status-pill justify-between" title="API System Health">
              <span>API Health</span>
              <div className={`status-dot ${healthStatus}`}></div>
            </div>
            <div className="status-pill justify-between" title="IPFS Cluster Health">
              <span>IPFS Cluster</span>
              <div className={`status-dot ${clusterStatus}`}></div>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <h2 className="font-serif text-lg">Dashboard</h2>
          <div className="flex items-center gap-2">
            <div className="status-pill">
              <CheckCircle2 size={14} className="text-emerald" />
              <span>Network: Local</span>
            </div>
          </div>
        </header>

        <div className="page-content">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default Layout;
