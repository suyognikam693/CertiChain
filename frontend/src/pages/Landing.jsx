import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const Landing = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="selection:bg-emerald-500 selection:text-white overflow-x-hidden min-h-screen bg-transparent text-slate-50">
      {/* Header/Footer are left embedded to match EXACT structure */}
      {/*  TopNavBar — centered primary nav (DESIGN.md glass bar)  */}
<header className="relative fixed left-0 right-0 top-0 z-50 flex min-h-[72px] w-full items-center border-b border-slate-800/50 bg-slate-900/40 px-6 backdrop-blur-[12px] md:px-8 dark:bg-emerald-600/80">
<div className="flex min-w-0 flex-1 items-center gap-3">
<button type="button" onClick={() => setDrawerOpen(!drawerOpen)} className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-[6px] border border-slate-800/80 text-slate-50 transition-colors hover:bg-slate-800 icon-btn border-white/20 dark:text-white dark:hover:bg-slate-800/10" aria-label="Open menu">
<span className="material-symbols-outlined text-[22px]">menu</span>
</button>
<Link className="nav-link shrink-0 font-serif text-2xl italic text-slate-50 dark:text-white" to="/index">CertiChain</Link>
</div>
<nav className="absolute left-1/2 top-1/2 z-10 hidden -translate-x-1/2 -translate-y-1/2 md:block" aria-label="Primary">
<ul className="flex items-center gap-10 font-serif text-lg tracking-tight lg:gap-12">
<li><Link className="nav-link text-slate-50 opacity-70 hover:text-emerald-500 dark:text-white" to="/university-login">Universities</Link></li>
<li><Link className="nav-link text-slate-50 opacity-70 hover:text-emerald-500 dark:text-white" to="/student/login">Students</Link></li>
<li><Link className="nav-link text-slate-50 opacity-70 hover:text-emerald-500 dark:text-white" to="/employer">Verify</Link></li>
</ul>
</nav>
<div className="flex min-w-0 flex-1 justify-end"></div>
</header>
<nav id="site-nav-drawer" className="mobile-drawer md:hidden fixed left-0 right-0 top-[72px] z-40 border-b border-slate-800/50 bg-slate-900/95 backdrop-blur-[12px] px-6 py-6 flex flex-col gap-4 shadow-[0_1px_3px_rgba(15,15,15,0.06)]" data-open={drawerOpen} aria-label="Site">
<Link className="font-serif text-lg text-slate-50 py-2 border-b border-slate-800/40" to="/university-login">Universities</Link>
<Link className="font-serif text-lg text-slate-50 py-2 border-b border-slate-800/40" to="/student/login">Students</Link>
<Link className="font-serif text-lg text-slate-50 py-2 border-b border-slate-800/40" to="/employer">Verify credential</Link>
</nav>
<main className="pt-32 pb-24">
{/*  Hero Section  */}
<section className="max-w-screen-xl mx-auto px-8 text-center mt-20 mb-32">
<div className="mb-6">
<span className="font-sans text-[11px] uppercase tracking-[0.2em] text-slate-500">WEB3-01 · VELORA 1.0</span>
</div>
<h1 className="font-serif text-[64px] leading-[1.1] tracking-[-0.02em] text-slate-50 mb-8 max-w-4xl mx-auto">
                Credential fraud ends here.
            </h1>
<p className="font-sans text-[15px] text-slate-400 max-w-xl mx-auto mb-12 leading-relaxed">
                Universities issue. Students own. Employers verify in 2 seconds. No middlemen.
            </p>
<div className="flex flex-col sm:flex-row items-center justify-center gap-8 mb-24">
<Link className="btn-primary relative inline-flex items-center justify-center bg-emerald-600 text-white px-8 py-4 rounded-[6px] font-sans text-sm font-medium hover:bg-emerald-500 shadow-[0_1px_3px_rgba(15,15,15,0.06)]" to="/university-login" data-ripple="">
                    Issue Credentials
                </Link>
<Link className="link-arrow group flex items-center gap-2 font-sans text-sm font-medium text-slate-50 hover:text-emerald-500 nav-link" to="/employer">
                    Verify a Degree
                    <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
</Link>
</div>
{/*  Micro-stats  */}
<div className="flex flex-wrap justify-center items-center gap-x-12 gap-y-6 max-w-4xl mx-auto py-12 border-t border-slate-800/50">
<div className="flex flex-col items-center">
<span className="font-mono text-xl text-slate-50 tracking-tighter">&lt; ₹2</span>
<span className="font-sans text-[10px] uppercase tracking-widest text-slate-500 mt-1">per check</span>
</div>
<div className="h-8 w-[1px] bg-[#E8E6E1] hidden sm:block"></div>
<div className="flex flex-col items-center">
<span className="font-mono text-xl text-slate-50 tracking-tighter">&lt; 2 seconds</span>
<span className="font-sans text-[10px] uppercase tracking-widest text-slate-500 mt-1">verification</span>
</div>
<div className="h-8 w-[1px] bg-[#E8E6E1] hidden sm:block"></div>
<div className="flex flex-col items-center">
<span className="font-mono text-xl text-slate-50 tracking-tighter">0%</span>
<span className="font-sans text-[10px] uppercase tracking-widest text-slate-500 mt-1">fraud rate</span>
</div>
</div>
</section>
{/*  Full-width thin horizontal rule  */}
<hr className="border-t border-slate-800 opacity-50 w-full"/>
{/*  Features Section  */}
<section className="max-w-screen-xl mx-auto px-8 py-32">
<div className="grid grid-cols-1 md:grid-cols-3 gap-16 lg:gap-24">
{/*  Universities  */}
<Link className="interactive-surface group flex flex-col p-6 -m-6 rounded-xl hover:bg-slate-800" to="/university-login">
<div className="w-12 h-12 flex items-center justify-center mb-8">
<span className="material-symbols-outlined text-3xl text-slate-50" data-icon="shield">shield</span>
</div>
<h3 className="font-serif text-2xl mb-4 group-hover:text-emerald-500 transition-colors">Universities</h3>
<p className="font-sans text-[15px] text-slate-400 leading-relaxed">
                        Issue and revoke with one click. Digital signatures replace manual paperwork and stamped envelopes.
                    </p>
<span className="mt-6 inline-flex items-center gap-1 font-sans text-[11px] uppercase tracking-[0.08em] text-slate-50 opacity-60 group-hover:opacity-100">Open portal <span className="material-symbols-outlined text-base">arrow_forward</span></span>
</Link>
{/*  Students  */}
<Link className="interactive-surface group flex flex-col p-6 -m-6 rounded-xl hover:bg-slate-800" to="/student/login">
<div className="w-12 h-12 flex items-center justify-center mb-8">
<span className="material-symbols-outlined text-3xl text-slate-50" data-icon="wallet">wallet</span>
</div>
<h3 className="font-serif text-2xl mb-4 group-hover:text-emerald-500 transition-colors">Students</h3>
<p className="font-sans text-[15px] text-slate-400 leading-relaxed">
                        Own your credentials forever. A permanent, portable record that belongs to you, not the institution.
                    </p>
<span className="mt-6 inline-flex items-center gap-1 font-sans text-[11px] uppercase tracking-[0.08em] text-slate-50 opacity-60 group-hover:opacity-100">View vault <span className="material-symbols-outlined text-base">arrow_forward</span></span>
</Link>
{/*  Employers  */}
<Link className="interactive-surface group flex flex-col p-6 -m-6 rounded-xl hover:bg-slate-800" to="/employer">
<div className="w-12 h-12 flex items-center justify-center mb-8">
<span className="material-symbols-outlined text-3xl text-slate-50" data-icon="scan">scan</span>
</div>
<h3 className="font-serif text-2xl mb-4 group-hover:text-emerald-500 transition-colors">Employers</h3>
<p className="font-sans text-[15px] text-slate-400 leading-relaxed">
                        Verify without calling anyone. Instant cryptographic proof of authenticity directly from the source.
                    </p>
<span className="mt-6 inline-flex items-center gap-1 font-sans text-[11px] uppercase tracking-[0.08em] text-slate-50 opacity-60 group-hover:opacity-100">Verify now <span className="material-symbols-outlined text-base">arrow_forward</span></span>
</Link>
</div>
</section>
{/*  Additional Proof Section (Asymmetric Bento)  */}
<section className="max-w-screen-xl mx-auto px-8 pb-32">
<div className="grid grid-cols-1 md:grid-cols-12 gap-8">
<div className="md:col-span-8 bg-slate-800 p-12 rounded-xl flex flex-col justify-between aspect-[16/7]">
<div className="max-w-sm">
<span className="font-sans text-[11px] uppercase tracking-widest text-emerald-500 mb-4 block">Security First</span>
<h2 className="font-serif text-3xl mb-4">Tamper-proof by design.</h2>
<p className="font-sans text-sm text-slate-400">Every certificate is hashed and anchored to the global ledger, making unauthorized alterations mathematically impossible.</p>
</div>
<div className="flex gap-4 items-end overflow-hidden">
<div className="flex-1 h-32 bg-slate-800 rounded-t-lg shadow-sm p-4 flex flex-col justify-between">
<div className="h-2 w-1/2 bg-[#E8E6E1] rounded-full"></div>
<div className="space-y-2">
<div className="h-1.5 w-full bg-slate-800 rounded-full"></div>
<div className="h-1.5 w-3/4 bg-slate-800 rounded-full"></div>
</div>
</div>
<div className="flex-1 h-40 bg-slate-800 rounded-t-lg shadow-sm p-4 flex flex-col justify-between border-x border-t border-emerald-500/20">
<div className="flex justify-between items-start">
<div className="h-2 w-1/3 bg-[#C17A3A]/40 rounded-full"></div>
<span className="material-symbols-outlined text-emerald-500 text-sm" style={{fontVariationSettings: '\'FILL\' 1'}}>verified_user</span>
</div>
<div className="space-y-2">
<div className="h-1.5 w-full bg-slate-800 rounded-full"></div>
<div className="h-1.5 w-full bg-slate-800 rounded-full"></div>
<div className="h-1.5 w-1/2 bg-slate-800 rounded-full"></div>
</div>
</div>
<div className="flex-1 h-32 bg-slate-800 rounded-t-lg shadow-sm p-4 flex flex-col justify-between">
<div className="h-2 w-1/2 bg-[#E8E6E1] rounded-full"></div>
<div className="space-y-2">
<div className="h-1.5 w-full bg-slate-800 rounded-full"></div>
<div className="h-1.5 w-3/4 bg-slate-800 rounded-full"></div>
</div>
</div>
</div>
</div>
<div className="md:col-span-4 bg-emerald-600 text-white p-12 rounded-xl flex flex-col justify-center text-center">
<span className="font-mono text-4xl mb-4 text-emerald-500">99.9%</span>
<p className="font-sans text-[11px] uppercase tracking-widest opacity-60 mb-6">Efficiency Increase</p>
<p className="font-sans text-sm italic opacity-80 leading-relaxed">"CertiChain transformed our registrar operations from weeks of mailing to minutes of issuing."</p>
</div>
</div>
</section>
</main>
{/*  Footer  */}
<footer className="bg-slate-900/40 dark:bg-emerald-600/40 w-full py-12 px-8 flex flex-col md:flex-row justify-between items-center border-t border-slate-800">
<div className="mb-8 md:mb-0 text-center md:text-left">
<div className="flex flex-wrap justify-center md:justify-start gap-x-8 gap-y-2 mb-4 font-sans text-[11px] uppercase tracking-[0.08em] text-slate-50 dark:text-white">
<Link className="nav-link opacity-60 hover:opacity-100 hover:text-emerald-500" to="/university-login">University portal</Link>
<Link className="nav-link opacity-60 hover:opacity-100 hover:text-emerald-500" to="/student/login">Student vault</Link>
<Link className="nav-link opacity-60 hover:opacity-100 hover:text-emerald-500" to="/employer">Verify</Link>
</div>
<p className="font-sans text-[11px] uppercase tracking-widest text-slate-50 dark:text-white opacity-50">
                © 2026 CertiChain Ledger. All Rights Reserved.
            </p>
</div>
<div className="flex flex-wrap justify-center gap-8"></div>
</footer>
    </div>
  );
};

export default Landing;
