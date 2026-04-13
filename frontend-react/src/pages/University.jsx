import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { checkClusterStatus, checkHealth } from '../api/client';

const University = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [health, setHealth] = useState(null);
  const [cluster, setCluster] = useState(null);

  useEffect(() => {
    const loadInfraStatus = async () => {
      try {
        const [healthRes, clusterRes] = await Promise.all([checkHealth(), checkClusterStatus()]);
        setHealth(healthRes);
        setCluster(clusterRes);
      } catch {
        setHealth({ status: 'offline' });
        setCluster({ reachable: false });
      }
    };

    loadInfraStatus();
  }, []);

  return (
    <div className="selection:bg-emerald-500 selection:text-white overflow-x-hidden min-h-screen bg-transparent text-slate-50">
      {/* Header/Footer are left embedded to match EXACT structure */}
      {/*  Site header (matches student / employer)  */}
<header className="relative fixed left-0 right-0 top-0 z-50 flex min-h-[72px] w-full items-center border-b border-mist/50 bg-slate-900/40 px-6 backdrop-blur-[12px] md:px-8 dark:border-white/10 dark:bg-emerald-600/80">
<div className="flex min-w-0 flex-1 items-center gap-3">
<button type="button" className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-[6px] border border-mist/80 text-ink transition-colors hover:bg-surface-container-low icon-btn border-white/20 dark:text-white" data-mobile-nav-toggle="" aria-controls="university-nav-drawer" aria-expanded="false" aria-label="Open menu">
<span className="material-symbols-outlined text-[22px]">menu</span>
</button>
<Link className="nav-link shrink-0 font-serif text-2xl italic text-ink dark:text-white" to="/index">CertiChain</Link>
</div>
<nav className="absolute left-1/2 top-1/2 z-10 hidden -translate-x-1/2 -translate-y-1/2 md:block" aria-label="Primary">
<ul className="flex items-center gap-10 font-serif text-lg tracking-tight text-ink lg:gap-12 dark:text-white">
<li><Link className="nav-link border-b-2 border-seal pb-1 font-medium text-seal" to="/university" aria-current="page">Universities</Link></li>
<li><Link className="nav-link opacity-70 hover:text-seal" to="/student/login">Students</Link></li>
<li><Link className="nav-link opacity-70 hover:text-seal" to="/employer">Verify</Link></li>
</ul>
</nav>
<div className="flex min-w-0 flex-1 justify-end"></div>
</header>
<nav id="university-nav-drawer" className="mobile-drawer fixed left-0 right-0 top-[72px] z-40 flex flex-col gap-4 border-b border-mist/50 bg-paper/95 px-6 py-6 shadow-[0_1px_3px_rgba(15,15,15,0.06)] backdrop-blur-[12px] md:hidden" data-mobile-drawer="" data-open="false" aria-label="Site">
<Link className="border-b border-mist/40 py-2 font-serif text-lg text-seal" to="/university">Universities</Link>
<Link className="border-b border-mist/40 py-2 font-serif text-lg" to="/student/login">Students</Link>
<Link className="border-b border-mist/40 py-2 font-serif text-lg" to="/employer">Verify</Link>
<Link className="py-2 font-serif text-lg text-ink/60" to="/index">Home</Link>
<p className="pt-2 font-sans text-[11px] uppercase tracking-[0.08em] text-ink/40">Registrar</p>
<Link className="border-b border-mist/30 py-2 text-sm text-ink/80" to="/university">Dashboard</Link>
<Link className="border-b border-mist/30 py-2 text-sm text-ink/80" to="/university-issue">Issue credentials</Link>
<Link className="py-2 text-sm text-ink/80" to="/university-revoke">Revoke</Link>
</nav>
<main className="mx-auto max-w-[1100px] px-6 pb-20 pt-28 md:px-8">
{/*  Workspace modes (all viewports)  */}
<nav className="mb-10 flex flex-wrap items-center gap-x-8 gap-y-3 border-b border-mist/50 pb-6 font-serif text-[15px] tracking-tight md:gap-x-12" aria-label="Registrar workspace">
<Link className="nav-link border-b-2 border-seal pb-1 font-medium text-seal" to="/university" aria-current="page">Dashboard</Link>
<Link className="nav-link text-ink/55 transition-colors hover:text-ink" to="/university-issue">Issue</Link>
<Link className="nav-link text-ink/55 transition-colors hover:text-ink" to="/university-revoke">Revoke</Link>
</nav>
<header className="mb-10 flex flex-wrap items-end justify-between gap-6">
<div>
<h1 className="mb-2 font-serif text-[40px] leading-[1.1] tracking-tight text-ink">Registrar overview</h1>
<p className="max-w-xl text-[15px] leading-relaxed text-on-surface-variant">Sardar Patel Institute of Technology registrar dashboard</p>
</div>
</header>
<section className="mb-8 rounded-[6px] border border-mist/50 bg-surface-container-low px-4 py-3">
<div className="flex flex-wrap items-center gap-5 text-[12px]">
<span className="font-mono text-ink/80">API: {health?.status || (health ? 'online' : 'loading')}</span>
<span className="font-mono text-ink/80">Cluster: {cluster?.reachable === true ? 'reachable' : cluster?.reachable === false ? 'unreachable' : 'loading'}</span>
<span className="font-mono text-ink/80">Peers: {Array.isArray(cluster?.peers) ? cluster.peers.length : '-'}</span>
</div>
</section>
{/*  Institutional wallet (mono for chain truth)  */}
<div className="mb-12 flex flex-col gap-3 rounded-[6px] border border-mist/50 bg-surface-container-low px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
<div className="flex items-center gap-3">
<span className="material-symbols-outlined text-[18px] text-seal" aria-hidden="true">account_balance_wallet</span>
<span className="font-mono text-[12px] tracking-tight text-ink">0x8a3F…7f2a · Sepholia TestNet</span>
</div>
<div className="flex items-center gap-2">
<span className="h-2 w-2 rounded-full bg-[#2A7A5A]" aria-hidden="true"></span>
<span className="font-mono text-[11px] uppercase tracking-wider text-emerald-500">Connected</span>
</div>
</div>
{/*  Surface shift — recent activity (DESIGN tonal layering)  */}
<section className="rounded-[6px] bg-surface-container-low px-6 py-10 md:px-10">
<div className="mb-8 flex flex-wrap items-end justify-between gap-4">
<div>
<p className="mb-2 font-sans text-[11px] uppercase tracking-[0.08em] text-ink/50">Integrity log</p>
<h2 className="font-serif text-[28px] leading-tight text-ink">Recent anchors</h2>
</div>
</div>
<ul className="space-y-2">
<li className="flex flex-col gap-1 rounded-[6px] py-4 transition-colors hover:bg-paper/70 sm:flex-row sm:items-baseline sm:justify-between sm:px-3">
<span className="font-mono text-[13px] text-ink/55">Qmx…9p21</span>
<span className="text-[15px] text-ink/85">B.Tech Honors · Arjun Mehra</span>
<span className="font-mono text-[11px] uppercase tracking-tight text-emerald-500">Verified</span>
</li>
<li className="flex flex-col gap-1 rounded-[6px] py-4 transition-colors hover:bg-paper/70 sm:flex-row sm:items-baseline sm:justify-between sm:px-3">
<span className="font-mono text-[13px] text-ink/55">Qmz…5r42</span>
<span className="text-[15px] text-ink/85">M.Tech AI · Sarah D'Souza</span>
<span className="font-mono text-[11px] uppercase tracking-tight text-emerald-500">Verified</span>
</li>
<li className="flex flex-col gap-1 rounded-[6px] py-4 transition-colors hover:bg-paper/70 sm:flex-row sm:items-baseline sm:justify-between sm:px-3">
<span className="font-mono text-[13px] text-ink/55">Qmx…4k02</span>
<span className="text-[15px] text-ink/85">MBA Systems · Riya Verma</span>
<span className="font-mono text-[11px] uppercase tracking-tight text-[#8A6A20]">Pending</span>
</li>
</ul>
</section>
{/*  Actions: primary + secondary per DESIGN.md  */}
<section className="mt-14 flex flex-col gap-4 sm:flex-row sm:items-center">
<Link className="btn-primary inline-flex items-center justify-center rounded-[6px] bg-ink px-8 py-3 text-[11px] font-medium uppercase tracking-[0.08em] text-paper shadow-[0_1px_3px_rgba(15,15,15,0.06)] transition-colors hover:bg-seal" to="/university-issue" data-ripple="">Issue credentials</Link>
<Link className="inline-flex items-center justify-center rounded-[6px] border border-mist px-8 py-3 text-[11px] font-medium uppercase tracking-[0.08em] text-ink transition-colors hover:border-ink hover:bg-ink hover:text-paper" to="/university-revoke">Revoke mode</Link>
</section>
</main>
<footer className="flex w-full flex-col items-center justify-between gap-6 border-t border-mist/50 px-8 py-12 md:flex-row">
<div className="flex flex-wrap justify-center gap-8 font-sans text-[11px] uppercase tracking-widest text-ink/50"></div>
<p className="font-sans text-[11px] uppercase tracking-widest text-ink/30">© 2026 CertiChain Ledger</p>
</footer>
    </div>
  );
};

export default University;
