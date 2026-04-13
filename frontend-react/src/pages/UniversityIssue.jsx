import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { addBatchCredential, uploadBatchCSV, commitBatch } from '../api/client';

const getApiErrorMessage = (err, fallback) => {
  const detail = err?.response?.data?.detail;
  if (!detail) return fallback;
  return Array.isArray(detail) ? detail.map((d) => d?.msg || JSON.stringify(d)).join('; ') : String(detail);
};

const UniversityIssue = () => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [batchId, setBatchId] = useState('');
  const [stagedCount, setStagedCount] = useState(0);
  const [activeTab, setActiveTab] = useState('csv');
  
  const fileInputRef = useRef(null);

  // Form State
  const [formData, setFormData] = useState({
    student_did: '',
    student_name: '',
    student_email: '',
    university_name: 'Sardar Patel Institute of Technology',
    degree: '',
    branch: '',
    graduation_year: '',
    cgpa: ''
  });

  useEffect(() => {
    setBatchId('batch-' + Date.now());
  }, []);

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
       setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
       setFile(e.target.files[0]);
    }
  };

  const handleChange = (e) => {
    setFormData({...formData, [e.target.name]: e.target.value});
  };

  const getToken = () => localStorage.getItem('cc_token');

  const handleManualAdd = async (e) => {
    e.preventDefault();
    if (!formData.student_name || !formData.student_did || !formData.student_email || !formData.degree || !formData.branch || !formData.graduation_year) {
      return alert("Please fill all required fields before staging.");
    }
    setLoading(true);
    try {
      const token = getToken();
      if (!token) {
        setResults('Please login as university first.');
        return;
      }
      const res = await addBatchCredential({ ...formData, batch_id: batchId }, token);
      setStagedCount(prev => prev + 1);
      setResults(`Staged credential for ${formData.student_name}. CID: ${res.bare_ipfs_cid || 'N/A'}`);
      setFormData({
        student_did: '',
        student_name: '',
        student_email: '',
        university_name: formData.university_name,
        degree: '',
        branch: '',
        graduation_year: '',
        cgpa: ''
      });
    } catch (err) {
      setResults(`Error staging: ${getApiErrorMessage(err, err.message)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCSVUpload = async () => {
    if (!file) return alert("Please select a CSV file");
    setLoading(true);
    try {
      const token = getToken();
      if (!token) {
        setResults('Please login as university first.');
        return;
      }
      const res = await uploadBatchCSV(batchId, file, token);
      const totalPending = Number(res.total_pending || 0);
      setStagedCount(totalPending);
      setResults(res.message || `Successfully staged credentials from CSV. Pending: ${totalPending}`);
    } catch (err) {
      setResults(`Error uploading CSV: ${getApiErrorMessage(err, err.message)}`);
    } finally {
      setLoading(false);
    }
  };

  const finalizeBatch = async () => {
    if (stagedCount === 0) return alert("No credentials staged in batch.");
    setLoading(true);
    try {
      const token = getToken();
      if (!token) {
        setResults('Please login as university first.');
        return;
      }
      const res = await commitBatch(batchId, token);
      setResults(`Batch committed! Merkle Root: ${res.merkle_root}. Credentials: ${res.credential_count}. TX: ${res.tx_hash || 'N/A'}`);
      setStagedCount(0);
      setBatchId('batch-' + Date.now()); // reset batch
    } catch (err) {
      setResults(`Error committing batch: ${getApiErrorMessage(err, err.message)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="selection:bg-emerald-500 selection:text-white overflow-x-hidden min-h-screen bg-transparent text-slate-50">
      <header className="relative fixed left-0 right-0 top-0 z-50 flex min-h-[72px] w-full items-center border-b border-mist/50 bg-slate-900/40 px-6 backdrop-blur-[12px] md:px-8 dark:border-white/10 dark:bg-emerald-600/80">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <button type="button" onClick={() => setDrawerOpen(!drawerOpen)} className="md:hidden inline-flex h-10 w-10 items-center justify-center rounded-[6px] border border-mist/80 text-ink transition-colors hover:bg-surface-container-low icon-btn border-white/20 dark:text-white" aria-label="Open menu">
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
      </header>

      <nav id="uni-issue-nav-drawer" className="mobile-drawer fixed left-0 right-0 top-[72px] z-40 flex flex-col gap-4 border-b border-mist/50 bg-paper/95 px-6 py-6 shadow-[0_1px_3px_rgba(15,15,15,0.06)] backdrop-blur-[12px] md:hidden" data-open={drawerOpen}>
        <Link className="border-b border-mist/30 py-2 text-sm text-ink/80" to="/university">Dashboard</Link>
        <Link className="border-b border-mist/30 py-2 text-sm font-medium text-seal" to="/university-issue">Issue credentials</Link>
        <Link className="py-2 text-sm text-ink/80" to="/university-revoke">Revoke</Link>
      </nav>

      <main className="mx-auto max-w-[720px] px-6 pb-20 pt-28 md:px-8">
        <nav className="mb-10 flex flex-wrap items-center gap-x-8 gap-y-3 border-b border-mist/50 pb-6 font-serif text-[15px] tracking-tight md:gap-x-12" aria-label="Registrar workspace">
          <Link className="nav-link text-ink/55 transition-colors hover:text-ink" to="/university">Dashboard</Link>
          <Link className="nav-link border-b-2 border-seal pb-1 font-medium text-seal" to="/university-issue" aria-current="page">Issue</Link>
          <Link className="nav-link text-ink/55 transition-colors hover:text-ink" to="/university-revoke">Revoke</Link>
        </nav>

        <header className="mb-8">
          <p className="mb-2 font-sans text-[11px] uppercase tracking-[0.08em] text-ink/50">Batch #{batchId}</p>
          <h1 className="font-serif text-[40px] leading-[1.1] tracking-tight text-ink">Stage Credentials</h1>
          <p className="mt-4 max-w-lg text-[15px] leading-relaxed text-on-surface-variant">Add items individually via JSON map or upload a bulk CSV. Stagings are kept in-memory until committed.</p>
        </header>

        <div className="flex gap-4 mb-8">
          <button onClick={() => setActiveTab('csv')} className={`px-4 py-2 rounded-md ${activeTab === 'csv' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-white'}`}>Upload CSV</button>
          <button onClick={() => setActiveTab('manual')} className={`px-4 py-2 rounded-md ${activeTab === 'manual' ? 'bg-emerald-600 text-white' : 'bg-slate-800 text-white'}`}>Add Manually</button>
        </div>

        {activeTab === 'csv' ? (
          <div>
            <label className="mb-2 block font-sans text-[11px] uppercase tracking-[0.08em] text-slate-400">Graduate file</label>
            <input type="file" ref={fileInputRef} onChange={handleFileSelect} id="csv-file-input" accept=".csv" className="hidden"/>
            <div onClick={() => fileInputRef.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={handleFileDrop} className="group mb-8 flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-[6px] border border-dashed border-slate-800/80 bg-slate-800 px-6 py-12 text-center transition-colors hover:border-emerald-500/60 hover:bg-slate-900">
              <span className="material-symbols-outlined mb-4 text-4xl text-slate-50/25 transition-colors group-hover:text-emerald-500" aria-hidden="true">upload_file</span>
              <p className="text-[15px] text-slate-50/75">{file ? `✓ ${file.name} ready` : 'Drop CSV here'}</p>
            </div>
            <button type="button" onClick={handleCSVUpload} disabled={loading} className="btn-primary w-full items-center justify-center rounded-[6px] bg-slate-800 border border-emerald-500 py-3 text-[11px] font-medium uppercase tracking-[0.08em] text-emerald-500 transition-colors hover:bg-emerald-600 hover:text-white" data-ripple="">
              {loading ? 'Uploading...' : 'Stage CSV Items'}
            </button>
          </div>
        ) : (
          <form className="space-y-4 bg-slate-800/50 p-6 rounded-md border border-slate-700" onSubmit={handleManualAdd}>
            <div className="grid grid-cols-2 gap-4">
              <input name="student_name" value={formData.student_name} onChange={handleChange} placeholder="Student Name" required className="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white" />
              <input name="student_did" value={formData.student_did} onChange={handleChange} placeholder="Student DID" required className="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white" />
              <input name="student_email" value={formData.student_email} onChange={handleChange} placeholder="Student Email" required className="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white" />
              <input name="university_name" value={formData.university_name} onChange={handleChange} placeholder="University Name" required className="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white" />
              <input name="degree" value={formData.degree} onChange={handleChange} placeholder="Degree" className="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white" />
              <input name="branch" value={formData.branch} onChange={handleChange} placeholder="Branch" className="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white" />
              <input name="cgpa" value={formData.cgpa} onChange={handleChange} placeholder="CGPA" className="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white" />
              <input name="graduation_year" value={formData.graduation_year} onChange={handleChange} placeholder="Year" className="w-full bg-slate-900 border border-slate-700 p-2 rounded text-white" />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full rounded-[6px] bg-slate-800 border border-emerald-500 py-3 text-[11px] font-medium uppercase tracking-[0.08em] text-emerald-500 transition-colors hover:bg-emerald-600 hover:text-white">
              {loading ? 'Staging...' : 'Stage Individual Credential'}
            </button>
          </form>
        )}

        <div className="mt-10 p-4 border border-emerald-500/30 rounded bg-slate-900">
           <h3 className="text-emerald-500 uppercase tracking-widest text-xs font-semibold mb-2">Pending Batch Status</h3>
            <p className="text-sm text-slate-300">{stagedCount} Credentials staged. Minimum 2 required for non-empty Merkle proof.</p>
        </div>

        <div className="flex flex-col gap-4 sm:flex-row mt-8">
          <button type="button" onClick={finalizeBatch} disabled={loading || stagedCount < 2} className={`btn-primary inline-flex flex-1 items-center justify-center rounded-[6px] py-3 text-[11px] font-medium uppercase tracking-[0.08em] text-white transition-colors ${stagedCount < 2 ? 'bg-slate-700' : 'bg-emerald-600 hover:bg-emerald-500'}`}>
            {loading ? 'Committing...' : 'Commit Batch to Ledger'}
          </button>
        </div>

        {results && <div className="mt-8 p-4 rounded bg-slate-800/80 border border-emerald-400 text-sm break-words">{results}</div>}
      </main>

      <footer className="flex w-full flex-col items-center justify-between gap-6 border-t border-mist/50 px-8 py-12 md:flex-row">
        <p className="font-sans text-[11px] uppercase tracking-widest text-ink/30">© 2026 CertiChain Ledger</p>
      </footer>
    </div>
  );
};

export default UniversityIssue;
