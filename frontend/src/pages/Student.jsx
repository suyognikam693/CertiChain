import React, { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { getStudentCredentials, getStudentQRCodes } from '../api/client';

const VERIFIED_REDIRECT_URL = 'https://suyognikam693.github.io/verify/';
const FAILED_REDIRECT_URL = 'https://suyognikam693.github.io/failed/';

const normalizeQRCodes = (responseData) => {
  const rawQrs = Array.isArray(responseData)
    ? responseData
    : (Array.isArray(responseData?.qr_codes) ? responseData.qr_codes : []);

  return rawQrs.map((item) => {
    if (item?.qr_code_base64) return item;

    let parsedStatus = null;
    if (typeof item?.qr_data === 'string') {
      try {
        const parsed = JSON.parse(item.qr_data);
        parsedStatus = typeof parsed?.status === 'string' ? parsed.status.toUpperCase() : null;
      } catch {
        parsedStatus = null;
      }
    }

    const bakedStatus = typeof item?.status_baked_in === 'string' ? item.status_baked_in.toUpperCase() : null;
    const finalStatus = bakedStatus || parsedStatus || 'VERIFIED';
    const qrPayload = item?.qr_payload || (finalStatus === 'REVOKED' ? FAILED_REDIRECT_URL : VERIFIED_REDIRECT_URL);

    return {
      ...item,
      qr_payload: qrPayload,
      qr_code_base64: `https://api.qrserver.com/v1/create-qr-code/?size=420x420&data=${encodeURIComponent(qrPayload)}`,
    };
  });
};

const Student = () => {
  const { uid } = useParams();
  const navigate = useNavigate();

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [credentials, setCredentials] = useState([]);
  const [selectedCred, setSelectedCred] = useState(null);
  const [qrCodes, setQrCodes] = useState([]);
  const [copyMessage, setCopyMessage] = useState('');

  const selectedIndex = selectedCred ? credentials.findIndex((c) => c === selectedCred) : -1;
  const selectedQr = selectedIndex >= 0 ? qrCodes[selectedIndex] : null;

  const copyToClipboard = async (value, successText) => {
    const text = String(value ?? '');
    if (!text.trim()) {
      setCopyMessage('Nothing to copy');
      return;
    }

    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const tempInput = document.createElement('textarea');
        tempInput.value = text;
        tempInput.setAttribute('readonly', '');
        tempInput.style.position = 'fixed';
        tempInput.style.left = '-9999px';
        document.body.appendChild(tempInput);
        tempInput.focus();
        tempInput.select();
        const copied = document.execCommand('copy');
        document.body.removeChild(tempInput);
        if (!copied) throw new Error('Fallback copy failed');
      }

      setCopyMessage(successText || 'Copied');
      window.setTimeout(() => setCopyMessage(''), 1800);
    } catch {
      setCopyMessage('Copy failed');
      window.setTimeout(() => setCopyMessage(''), 1800);
    }
  };

  useEffect(() => {
    const storedUid = localStorage.getItem('cc_student_uid');
    if (!uid || uid !== storedUid) {
      navigate('/student/login', { replace: true });
        return;
    }

    const fetchIdentity = async () => {
      setLoading(true);
      try {
        const studentDid = uid;
        const tuplesRes = await getStudentCredentials(studentDid);
        const processedCreds = Array.isArray(tuplesRes) ? tuplesRes : tuplesRes.credentials || [];
        
        setCredentials(processedCreds);
        if(processedCreds.length > 0) setSelectedCred(processedCreds[0]);
        
        try {
          const qrs = await getStudentQRCodes(studentDid);
          setQrCodes(normalizeQRCodes(qrs));
        } catch (e) {
          console.warn("QR fetching disabled or failed.");
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchIdentity();
  }, [uid, navigate]);
  return (
    <div className="selection:bg-emerald-500 selection:text-white overflow-x-hidden min-h-screen bg-transparent text-slate-50">
      {/* Header/Footer are left embedded to match EXACT structure */}
      {/*  Shared TopNavBar — centered nav + right CTA (matches index)  */}
<header className="relative fixed left-0 right-0 top-0 z-50 flex min-h-[72px] w-full items-center border-b border-mist/50 bg-slate-900/40 px-6 backdrop-blur-[12px] md:px-8 dark:bg-emerald-600/80">
<div className="flex min-w-0 flex-1 items-center gap-3">
<button type="button" onClick={() => setDrawerOpen(!drawerOpen)} className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-[6px] border border-mist/80 text-ink transition-colors hover:bg-surface-container-low icon-btn border-white/20 dark:text-white" aria-label="Open menu">
<span className="material-symbols-outlined text-[22px]">menu</span>
</button>
<Link className="nav-link shrink-0 font-serif text-2xl italic text-ink dark:text-white" to="/index">CertiChain</Link>
</div>
<nav className="absolute left-1/2 top-1/2 z-10 hidden -translate-x-1/2 -translate-y-1/2 md:block" aria-label="Primary">
<ul className="flex items-center gap-10 font-serif text-lg tracking-tight text-ink lg:gap-12 dark:text-white">
<li><Link className="nav-link opacity-70 hover:text-seal" to="/university-login">Universities</Link></li>
<li><Link className="nav-link border-b-2 border-seal pb-1 font-medium text-seal" to="/student/login" aria-current="page">Students</Link></li>
<li><Link className="nav-link opacity-70 hover:text-seal" to="/employer">Verify</Link></li>
</ul>
</nav>
<div className="flex min-w-0 flex-1 justify-end"></div>
</header>
<nav id="student-nav-drawer" className="mobile-drawer md:hidden fixed left-0 right-0 top-[72px] z-40 border-b border-mist/50 bg-paper/95 backdrop-blur-[12px] px-6 py-6 flex flex-col gap-4 shadow-[0_1px_3px_rgba(15,15,15,0.06)]" data-open={drawerOpen} aria-label="Site">
<Link className="font-serif text-lg py-2 border-b border-mist/40" to="/university-login">Universities</Link>
<Link className="font-serif text-lg py-2 border-b border-mist/40 text-seal" to="/student/login">Students</Link>
<Link className="font-serif text-lg py-2 border-b border-mist/40" to="/employer">Verify</Link>
<Link className="font-serif text-lg py-2 text-ink/60" to="/index">Home</Link>
</nav>
<main className="mx-auto flex max-w-[1440px] flex-col gap-12 px-8 pb-20 pt-28 md:flex-row">
{/*  Content Area  */}
<div className="flex-grow">
{/*  Header Section  */}
<header className="mb-12">
<h1 className="font-serif text-[40px] leading-[1.1] tracking-tight mb-2">Credentials Vault</h1>
<p className="text-on-surface-variant font-sans text-base opacity-80">12 verified assets · Cryptographically secured</p>
</header>
{/*  Wallet Bar  */}
<div className="bg-surface-container-low border border-mist/50 px-4 py-2 rounded-lg flex items-center justify-between mb-12">
<div className="flex items-center gap-3">
<span className="material-symbols-outlined text-[18px] text-seal">account_balance_wallet</span>
<span className="font-mono text-[12px] tracking-tight text-ink">0x742d35Cc...782e · Sepholia TestNet</span>
</div>
<div className="flex items-center gap-2">
<div className="w-2 h-2 rounded-full bg-secondary"></div>
<span className="font-mono text-[11px] uppercase tracking-wider text-secondary">Connected via MetaMask</span>
</div>
</div>
{/*  Credentials Grid  */}
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {loading ? (
     <div className="col-span-3 py-12 text-center text-slate-500 font-mono text-sm">Loading vault...</div>
  ) : credentials.length === 0 ? (
     <div className="col-span-3 py-20 text-center text-slate-500 font-mono text-sm">No credentials found in vault.<br/><span className="text-[11px] opacity-60">Ask your university to upload your credential CSV.</span></div>
  ) : credentials.map((cred, i) => (
     <div key={i} onClick={() => setSelectedCred(cred)} className="interactive-surface cursor-pointer bg-slate-800 border border-emerald-500/50 border-l-2 border-l-emerald-500 p-6 rounded-[6px] hover:border-emerald-500 flex flex-col justify-between min-h-[280px] shadow-[0_1px_3px_rgba(15,15,15,0.04)]">
       <div>
         <div className="flex justify-between items-start mb-6">
           <span className="font-sans font-medium uppercase text-[11px] tracking-[0.08em] text-slate-400">{cred.university_name || 'University'}</span>
           <span className="font-mono text-[11px] px-2 py-0.5 border border-emerald-500 text-emerald-500">VERIFIED</span>
         </div>
         <h3 className="font-serif text-[22px] leading-tight mb-1">{cred.degree || 'Degree'}</h3>
         <p className="text-slate-400 text-[14px]">{cred.branch || 'Program'}</p>
         <p className="text-slate-500 text-[13px] mt-1">{cred.student_name || 'Student Name'}</p>
       </div>
       <div className="mt-auto flex items-end justify-between">
         <div className="flex flex-col gap-1">
           <span className="font-mono text-[12px] text-slate-400 opacity-60 uppercase">{cred.graduation_year || 'Date'}</span>
           <span className="font-mono text-[10px] text-slate-500">Batch: {cred.batch_id || '-'}</span>
           <span className="font-mono text-[10px] text-slate-500">Leaf: {Number.isInteger(cred.leaf_index) ? cred.leaf_index : '-'}</span>
         </div>
         <div className="flex gap-2">
           <div className="font-mono text-[10px] truncate max-w-[100px] opacity-50 absolute bottom-3 right-4">{(cred.credential_hash || '').substring(0, 16)}...</div>
         </div>
       </div>
     </div>
  ))}
</div>
</div>
{/*  Right Drawer: Share Panel  */}
<aside className="w-full md:w-[360px] flex-shrink-0">
<div className="sticky top-24 bg-surface-container-low p-8 border border-mist/50 rounded-lg">
<h2 className="font-serif text-[28px] leading-tight mb-8">Share with Employer</h2>
{/*  QR Placeholder  */}
<div className="aspect-square w-full bg-paper border border-mist/50 flex items-center justify-center p-6 mb-8">
<div className="relative w-full h-full border-4 border-ink p-2 flex items-center justify-center bg-white rounded-lg">
  {selectedCred ? (
    selectedQr?.qr_code_base64 ? (
      <img src={selectedQr.qr_code_base64} alt="Credential QR" className="max-h-full max-w-full" />
    ) : (
      <span className="text-slate-400 font-mono text-sm text-center px-3">
        QR not available from backend for this credential.
      </span>
    )
  ) : (
    <span className="text-slate-400 font-mono text-sm">Select a credential</span>
  )}
</div>
</div>
<div className="space-y-6">
{/*  Certificate hash (paste on Verify page)  */}
<div className="space-y-2">
<label className="block font-sans text-[11px] font-medium uppercase tracking-[0.08em] text-slate-400" htmlFor="share-certificate-hash-input">Certificate hash</label>
<div className="flex min-w-0">
<input id="share-certificate-hash-input" className="min-w-0 flex-1 bg-slate-800 border border-slate-800/50 rounded-l-[6px] p-3 font-mono text-[12px] leading-snug focus:border-emerald-500 text-slate-50 focus:ring-0 focus:outline-none" readOnly type="text" value={selectedCred?.credential_hash || "Select a credential..."}/>
<button type="button" className="icon-btn shrink-0 border border-emerald-600 bg-emerald-600 px-4 text-white rounded-r-[6px] hover:bg-emerald-500" data-copy-target="share-certificate-hash-input" aria-label="Copy certificate hash" onClick={() => copyToClipboard(selectedCred?.credential_hash, 'Hash copied')}>
<span className="material-symbols-outlined text-[20px]">content_copy</span>
</button>
</div>
{copyMessage ? <p className="font-mono text-[11px] text-emerald-400">{copyMessage}</p> : null}
<p className="font-sans text-[12px] leading-relaxed text-on-surface-variant">Employers paste this hash on the <Link className="nav-link text-seal underline underline-offset-4 hover:opacity-80" to="/employer">Verify</Link> page (Paste Hash) to confirm the anchor.</p>
</div>

<div className="space-y-2">
<label className="block font-sans text-[11px] font-medium uppercase tracking-[0.08em] text-slate-400">Merkle proof details</label>
<div className="bg-slate-900/60 border border-slate-700 rounded-[6px] p-3 space-y-2">
<div className="flex items-center gap-2">
<p className="font-mono text-[11px] break-all text-slate-300 flex-1">Batch ID: {selectedCred?.batch_id || 'Select a credential...'}</p>
<button type="button" className="icon-btn shrink-0 border border-emerald-600 bg-emerald-600 px-3 py-1 text-white rounded-[6px] hover:bg-emerald-500 text-[10px]" onClick={() => copyToClipboard(selectedCred?.batch_id, 'Batch ID copied')}>Copy</button>
</div>
<div className="flex items-center gap-2">
<p className="font-mono text-[11px] break-all text-slate-300 flex-1">Leaf Index: {selectedCred && Number.isInteger(selectedCred.leaf_index) ? selectedCred.leaf_index : 'Select a credential...'}</p>
<button type="button" className="icon-btn shrink-0 border border-emerald-600 bg-emerald-600 px-3 py-1 text-white rounded-[6px] hover:bg-emerald-500 text-[10px]" onClick={() => copyToClipboard(selectedCred?.leaf_index, 'Leaf index copied')}>Copy</button>
</div>
<div>
<div className="flex items-center gap-2 mb-1">
<p className="font-mono text-[11px] text-slate-300 flex-1">Merkle Proof:</p>
<button type="button" className="icon-btn shrink-0 border border-emerald-600 bg-emerald-600 px-3 py-1 text-white rounded-[6px] hover:bg-emerald-500 text-[10px]" onClick={() => copyToClipboard(selectedCred ? JSON.stringify(selectedCred.proof || [], null, 2) : '', 'Merkle proof copied')}>Copy</button>
</div>
<pre className="max-h-36 overflow-auto bg-slate-950 border border-slate-800 rounded p-2 font-mono text-[10px] leading-relaxed text-slate-200 whitespace-pre-wrap break-all">{selectedCred ? JSON.stringify(selectedCred.proof || [], null, 2) : 'Select a credential...'}</pre>
</div>
</div>
</div>
</div>
<div className="mt-8 pt-8 border-t border-mist/30">
<div className="flex items-start gap-4">
<span className="material-symbols-outlined text-seal">verified_user</span>
<p className="text-[12px] leading-relaxed text-on-surface-variant">
              The hash is derived from your credential payload; revocations and re-issuance rotate this value on-chain.
            </p>
</div>
</div>
</div>
</aside>
</main>
<footer className="w-full py-12 px-8 flex flex-col md:flex-row justify-between items-center border-t border-slate-800 bg-slate-900/40 dark:bg-emerald-600/40 text-slate-50 dark:text-white font-sans text-[11px] uppercase tracking-widest">
<div className="flex flex-wrap gap-8 mb-6 md:mb-0">
<Link className="opacity-50 hover:opacity-100 transition-opacity hover:underline underline-offset-4 nav-link" to="/index">Home</Link>
</div>
<div className="opacity-50">© 2026 CertiChain Ledger. All Rights Reserved.</div>
</footer>
    </div>
  );
};

export default Student;
