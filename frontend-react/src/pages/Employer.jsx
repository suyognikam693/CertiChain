import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { verifyCredential } from '../api/client';

const stripHexPrefix = (value = '') => value.replace(/^0x/i, '').trim();

const Employer = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const searchParams = new URLSearchParams(location.search);

  const [drawerOpen, setDrawerOpen] = useState(false);
    const [hashInput, setHashInput] = useState(searchParams.get('credential_hash') || searchParams.get('hash') || '');
  const [batchId, setBatchId] = useState(searchParams.get('batch_id') || '');
  const [leafIndex, setLeafIndex] = useState(searchParams.get('leaf_index') || '0');
    const [proof, setProof] = useState(searchParams.get('proof') || '');
  
  const [loading, setLoading] = useState(false);
  const verifyRunRef = useRef(0);
  // Replaced inline result display state with Navigation Logic

  useEffect(() => {
        const hasAutoVerifyPayload =
            !!searchParams.get('batch_id') &&
            !!searchParams.get('leaf_index') &&
            !!(searchParams.get('credential_hash') || searchParams.get('hash')) &&
            !!searchParams.get('proof');

        if (hasAutoVerifyPayload) {
            handleVerify();
        }
    }, [location.search]);

  const handleVerify = async () => {
        if (!hashInput || !batchId) {
            return;
        }

    setLoading(true);
    const runId = ++verifyRunRef.current;
    
    try {
            let proofArr = [];

            if (proof) {
                try {
                    const maybeJson = JSON.parse(proof);
                    proofArr = Array.isArray(maybeJson) ? maybeJson : [];
                } catch {
                    proofArr = proof.split(',').map(s => s.trim()).filter(Boolean);
                }
            }

      let hashToUse = hashInput;
      if (!hashToUse && searchParams.get('hash')) hashToUse = searchParams.get('hash');
      
      const res = await verifyCredential({ 
         batch_id: batchId, 
                 credential_hash: stripHexPrefix(hashToUse), 
                 proof: proofArr.map(stripHexPrefix), 
         leaf_index: parseInt(leafIndex, 10) || 0 
      });

            // Ignore stale responses from earlier verify attempts.
            if (runId !== verifyRunRef.current) return;
      
      if (res.is_valid) {
         navigate('/verify-success', { state: { result: res } });
      } else {
                 navigate('/verify-failed', { state: { error: res.message || 'Credential marked invalid or tampered' } });
      }
    } catch (err) {
            if (runId !== verifyRunRef.current) return;
            const detail = err?.response?.data?.detail;
            navigate('/verify-failed', { state: { error: detail || err.message || 'Server connection failed.' } });
    } finally {
            if (runId === verifyRunRef.current) {
                setLoading(false);
            }
    }
  };

  return (
    <div className="selection:bg-emerald-500 selection:text-white overflow-x-hidden min-h-screen bg-transparent text-slate-50">
      {/* Header/Footer are left embedded to match EXACT structure */}
      <header className="relative fixed left-0 right-0 top-0 z-50 flex min-h-[72px] w-full items-center border-b border-mist/50 bg-paper/75 px-6 backdrop-blur-[12px] md:px-8">
<div className="flex min-w-0 flex-1 items-center gap-3">
<button type="button" onClick={() => setDrawerOpen(!drawerOpen)} className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-[6px] border border-slate-800 text-slate-50 transition-colors hover:bg-slate-800 icon-btn" aria-label="Open menu">
<span className="material-symbols-outlined text-[22px]">menu</span>
</button>
<Link className="nav-link shrink-0 font-serif text-2xl italic text-ink" to="/index">CertiChain</Link>
</div>
<nav className="absolute left-1/2 top-1/2 z-10 hidden -translate-x-1/2 -translate-y-1/2 md:block" aria-label="Primary">
<ul className="flex items-center gap-10 font-serif text-lg tracking-tight text-ink lg:gap-12">
<li><Link className="nav-link opacity-70 hover:text-seal" to="/university-login">Universities</Link></li>
<li><Link className="nav-link opacity-70 hover:text-seal" to="/student/login">Students</Link></li>
<li><span className="border-b-2 border-seal pb-1 font-medium text-seal" aria-current="page">Verify</span></li>
</ul>
</nav>
<div className="flex min-w-0 flex-1 justify-end gap-3">
<Link className="hidden items-center rounded-[6px] border border-mist px-4 py-2 text-[11px] font-medium uppercase tracking-[0.08em] text-ink transition-colors hover:border-ink hover:bg-ink hover:text-paper sm:inline-flex btn-secondary icon-btn" to="/university-login">Issuer login</Link>
</div>
</header>
<nav id="employer-nav-drawer" className="mobile-drawer md:hidden fixed left-0 right-0 top-[72px] z-40 border-b border-mist/50 bg-paper/95 backdrop-blur-[12px] px-6 py-6 flex flex-col gap-4 shadow-[0_1px_3px_rgba(15,15,15,0.06)]" data-open={drawerOpen} aria-label="Site">
<Link className="font-serif text-lg py-2 border-b border-mist/40" to="/university-login">Universities</Link>
<Link className="font-serif text-lg py-2 border-b border-mist/40" to="/student/login">Students</Link>
<Link className="font-serif text-lg py-2 border-b border-mist/40 text-seal" to="/employer">Verify</Link>
<Link className="font-serif text-lg py-2 text-ink/60" to="/index">Home</Link>
<Link className="font-serif text-lg py-2 border-b border-mist/40" to="/university-login">Issuer login</Link>
</nav>
{/*  Result Section (Verified State)  */}
<main className="mx-auto max-w-[640px] px-6 pb-24 pt-28">
    <div className="text-center mb-12">
        <h1 className="font-serif text-[48px] leading-[1.1] tracking-tight mb-4 text-ink">Verify a credential.</h1>
        <p className="font-body text-[15px] text-on-surface-variant opacity-70">
            Paste the certificate hash and proof details. No account needed.
        </p>
    </div>
    <div data-verify-tabs="">
        <section data-verify-panel="paste" className="space-y-4 mb-10 text-left">
            <div className="flex flex-col">
                <label className="font-label text-[11px] uppercase tracking-[0.08em] mb-2 px-1 text-on-surface-variant">Certificate Hash</label>
                <input id="hash-input" className="w-full h-10 px-4 bg-slate-800 border border-slate-800/50 rounded-[6px] font-mono text-[13px] focus:outline-none focus:border-emerald-500 transition-colors" placeholder="0x..." type="text" value={hashInput} onChange={(e) => setHashInput(e.target.value)} />
            </div>
            <div className="flex gap-4">
                <div className="flex flex-col flex-1">
                    <label className="font-label text-[11px] uppercase tracking-[0.08em] mb-2 px-1 text-on-surface-variant">Batch ID</label>
                    <input className="w-full h-10 px-4 bg-slate-800 border border-slate-800/50 rounded-[6px] font-mono text-[13px] focus:outline-none focus:border-emerald-500" placeholder="batch-..." type="text" value={batchId} onChange={(e) => setBatchId(e.target.value)} />
                </div>
                <div className="flex flex-col flex-1">
                    <label className="font-label text-[11px] uppercase tracking-[0.08em] mb-2 px-1 text-on-surface-variant">Leaf Index</label>
                    <input className="w-full h-10 px-4 bg-slate-800 border border-slate-800/50 rounded-[6px] font-mono text-[13px] focus:outline-none focus:border-emerald-500" placeholder="0" type="number" value={leafIndex} onChange={(e) => setLeafIndex(e.target.value)} />
                </div>
            </div>
            <div className="flex flex-col mb-4">
                <label className="font-label text-[11px] uppercase tracking-[0.08em] mb-2 px-1 text-on-surface-variant">Merkle Proof Array (comma separated)</label>
                <input className="w-full h-10 px-4 bg-slate-800 border border-slate-800/50 rounded-[6px] font-mono text-[13px] focus:outline-none focus:border-emerald-500" placeholder="0x..., 0x..." type="text" value={proof} onChange={(e) => setProof(e.target.value)} />
            </div>
            
            <button type="button" onClick={handleVerify} disabled={loading} id="lookup-btn" className="btn-primary w-full h-12 bg-slate-50 text-emerald-900 rounded-[6px] font-label text-[11px] uppercase tracking-[0.15em] font-semibold hover:bg-emerald-400 mt-6 transition-all">
                {loading ? 'Verifying Proof...' : 'Verify on Local Chain'}
            </button>
        </section>
        {/* Result rendering handled via Navigation implicitly */}
    </div>
</main>
<footer className="w-full py-12 px-8 flex flex-col sm:flex-row gap-6 justify-between items-center border-t border-mist/30">
<p className="font-label text-[11px] uppercase tracking-widest text-ink opacity-50">© 2026 CertiChain Ledger. All Rights Reserved.</p>
<div className="flex flex-wrap gap-8 justify-center">
<Link className="font-label text-[11px] uppercase tracking-widest text-ink opacity-50 transition-all hover:opacity-100 hover:underline hover:underline-offset-4 nav-link" to="/index">Home</Link>
</div>
</footer>
    </div>
  );
};

export default Employer;
