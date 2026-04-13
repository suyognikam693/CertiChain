import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { revokeCredential } from '../api/client';

const stripHexPrefix = (value = '') => value.replace(/^0x/i, '').trim();

const UniversityRevoke = () => {
  const [form, setForm] = useState({ batch_id: '', credential_hash: '' });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const getToken = () => localStorage.getItem('cc_token') || 'dev-key';

  const onSubmit = async (e) => {
    e.preventDefault();
    if (!form.batch_id || !form.credential_hash) {
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const response = await revokeCredential(
        {
          batch_id: form.batch_id,
          credential_hash: stripHexPrefix(form.credential_hash),
        },
        getToken()
      );
      setResult({ ok: true, data: response });
    } catch (error) {
      setResult({ ok: false, error: error?.response?.data?.detail || error.message || 'Revocation failed' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="selection:bg-emerald-500 selection:text-white overflow-x-hidden min-h-screen bg-transparent text-slate-50">
      {/* Header/Footer are left embedded to match EXACT structure */}
      <header className="relative fixed left-0 right-0 top-0 z-50 flex min-h-[72px] w-full items-center border-b border-mist/50 bg-slate-900/40 px-6 backdrop-blur-[12px] md:px-8 dark:border-white/10 dark:bg-emerald-600/80">
<div className="flex min-w-0 flex-1 items-center gap-3">
<button type="button" className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-[6px] border border-mist/80 text-ink transition-colors hover:bg-surface-container-low icon-btn border-white/20 dark:text-white" data-mobile-nav-toggle="" aria-controls="uni-revoke-nav-drawer" aria-expanded="false" aria-label="Open menu">
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
<nav id="uni-revoke-nav-drawer" className="mobile-drawer fixed left-0 right-0 top-[72px] z-40 flex flex-col gap-4 border-b border-mist/50 bg-paper/95 px-6 py-6 shadow-[0_1px_3px_rgba(15,15,15,0.06)] backdrop-blur-[12px] md:hidden" data-mobile-drawer="" data-open="false" aria-label="Site">
<Link className="border-b border-mist/40 py-2 font-serif text-lg text-seal" to="/university">Universities</Link>
<Link className="border-b border-mist/40 py-2 font-serif text-lg" to="/student/login">Students</Link>
<Link className="border-b border-mist/40 py-2 font-serif text-lg" to="/employer">Verify</Link>
<Link className="py-2 font-serif text-lg text-ink/60" to="/index">Home</Link>
<p className="pt-2 font-sans text-[11px] uppercase tracking-[0.08em] text-ink/40">Registrar</p>
<Link className="border-b border-mist/30 py-2 text-sm text-ink/80" to="/university">Dashboard</Link>
<Link className="border-b border-mist/30 py-2 text-sm text-ink/80" to="/university-issue">Issue credentials</Link>
<Link className="py-2 text-sm font-medium text-seal" to="/university-revoke">Revoke</Link>
</nav>
<main className="mx-auto max-w-[900px] px-6 pb-20 pt-28 md:px-8">
<nav className="mb-10 flex flex-wrap items-center gap-x-8 gap-y-3 border-b border-mist/50 pb-6 font-serif text-[15px] tracking-tight md:gap-x-12" aria-label="Registrar workspace">
<Link className="nav-link text-ink/55 transition-colors hover:text-ink" to="/university">Dashboard</Link>
<Link className="nav-link text-ink/55 transition-colors hover:text-ink" to="/university-issue">Issue</Link>
<Link className="nav-link border-b-2 border-seal pb-1 font-medium text-seal" to="/university-revoke" aria-current="page">Revoke</Link>
</nav>
<header className="mb-10">
<p className="mb-2 font-sans text-[11px] uppercase tracking-[0.08em] text-ink/50">Ledger action</p>
<h1 className="font-serif text-[40px] leading-[1.1] tracking-tight text-ink">Revoke credentials</h1>
<p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-on-surface-variant">Revocation emits a new on-chain attestation. Use only after internal policy sign-off; revoked rows cannot be reactivated from this console.</p>
</header>
<section className="mb-10 rounded-[6px] border border-mist/50 bg-surface-container-low p-6">
<form onSubmit={onSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-3">
<input
className="rounded-[6px] border border-mist bg-paper px-3 py-2 text-sm text-ink"
placeholder="Batch ID"
value={form.batch_id}
onChange={(e) => setForm({ ...form, batch_id: e.target.value })}
required
/>
<input
className="rounded-[6px] border border-mist bg-paper px-3 py-2 text-sm text-ink"
placeholder="Credential Hash (0x...)"
value={form.credential_hash}
onChange={(e) => setForm({ ...form, credential_hash: e.target.value })}
required
/>
<button
type="submit"
disabled={loading}
className="rounded-[6px] border border-error px-4 py-2 text-[11px] uppercase tracking-[0.08em] text-error transition-colors hover:bg-error/10 disabled:opacity-50"
>
{loading ? 'Revoking...' : 'Revoke on-chain'}
</button>
</form>
{result && (
<div className={`mt-4 rounded-[6px] border px-3 py-2 text-sm ${result.ok ? 'border-emerald-500 text-emerald-500' : 'border-error text-error'}`}>
{result.ok ? `Revoked successfully. TX: ${result.data?.tx_hash || 'N/A'}` : result.error}
</div>
)}
</section>
<p className="mb-6 font-sans text-[11px] uppercase tracking-[0.08em] text-ink/50">Eligible records</p>
<div className="rounded-[6px] bg-surface-container-low px-2 py-2 md:px-4">
<ul className="space-y-0">
<li className="flex flex-col gap-3 py-6 transition-colors first:pt-4 hover:bg-paper/80 sm:flex-row sm:items-center sm:justify-between sm:px-4">
<div>
<p className="font-sans text-[15px] font-medium text-ink">Arjun Mehra</p>
<p className="mt-1 font-sans text-[12px] text-ink/50">B.Tech Honors · 2024</p>
<p className="mt-2 font-mono text-[13px] text-ink/45">Qmx…9p21</p>
</div>
<div className="flex items-center gap-4">
<span className="font-mono text-[11px] uppercase tracking-tight text-emerald-500">Verified</span>
<button type="button" className="rounded-[6px] border border-mist px-4 py-2 text-[11px] font-medium uppercase tracking-[0.08em] text-error transition-colors hover:border-error hover:bg-error/5 icon-btn">Revoke</button>
</div>
</li>
<li className="flex flex-col gap-3 py-6 transition-colors hover:bg-paper/80 sm:flex-row sm:items-center sm:justify-between sm:px-4">
<div>
<p className="font-sans text-[15px] font-medium text-ink">Sarah D'Souza</p>
<p className="mt-1 font-sans text-[12px] text-ink/50">M.Tech AI · 2024</p>
<p className="mt-2 font-mono text-[13px] text-ink/45">Qmz…5r42</p>
</div>
<div className="flex items-center gap-4">
<span className="font-mono text-[11px] uppercase tracking-tight text-emerald-500">Verified</span>
<button type="button" className="rounded-[6px] border border-mist px-4 py-2 text-[11px] font-medium uppercase tracking-[0.08em] text-error transition-colors hover:border-error hover:bg-error/5 icon-btn">Revoke</button>
</div>
</li>
<li className="flex flex-col gap-3 py-6 pb-4 transition-colors last:pb-4 hover:bg-paper/80 sm:flex-row sm:items-center sm:justify-between sm:px-4">
<div>
<p className="font-sans text-[15px] font-medium text-ink">Riya Verma</p>
<p className="mt-1 font-sans text-[12px] text-ink/50">MBA Systems · 2024</p>
<p className="mt-2 font-mono text-[13px] text-ink/45">Qmx…4k02</p>
</div>
<div className="flex items-center gap-4">
<span className="font-mono text-[11px] uppercase tracking-tight text-[#8A6A20]">Pending</span>
<button type="button" className="rounded-[6px] border border-mist/50 px-4 py-2 text-[11px] font-medium uppercase tracking-[0.08em] text-ink/35" disabled="">Unavailable</button>
</div>
</li>
</ul>
</div>
</main>
<footer className="flex w-full flex-col items-center justify-between gap-6 border-t border-mist/50 px-8 py-12 md:flex-row">
<div className="flex flex-wrap justify-center gap-8 font-sans text-[11px] uppercase tracking-widest text-ink/50"></div>
<p className="font-sans text-[11px] uppercase tracking-widest text-ink/30">© 2026 CertiChain Ledger</p>
</footer>
    </div>
  );
};

export default UniversityRevoke;
