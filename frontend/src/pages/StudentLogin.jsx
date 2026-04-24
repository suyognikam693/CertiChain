import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const StudentLogin = () => {
  const navigate = useNavigate();
  const [uid, setUid] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (password === '1234' && uid.trim() !== '') {
      const cleanUid = uid.trim();
      localStorage.setItem('cc_student_uid', cleanUid);
      localStorage.setItem('cc_wallet', cleanUid); // Map universal DID correctly
      navigate(`/student/${cleanUid}`);
    } else {
      setError('Invalid DID or password');
    }
  };

  return (
    <div className="selection:bg-emerald-500 selection:text-white overflow-x-hidden min-h-screen bg-transparent text-slate-50">
      {/* Header/Footer are left embedded to match EXACT structure */}
      <header className="fixed left-0 right-0 top-0 z-50 flex min-h-[72px] w-full items-center border-b border-mist/50 bg-[var(--paper)]/75 px-6 backdrop-blur-[12px] md:px-8">
  <div className="flex min-w-0 flex-1 items-center">
    <Link className="font-serif text-2xl italic text-[var(--ink)]" to="/index">CertiChain</Link>
  </div>
  <nav className="absolute left-1/2 top-1/2 hidden -translate-x-1/2 -translate-y-1/2 md:block">
    <ul className="flex items-center gap-10 font-serif text-lg tracking-tight text-[var(--ink)]">
      <li><Link className="opacity-70 hover:text-[var(--seal)]" to="/university-login">Universities</Link></li>
      <li><Link className="border-b-2 border-[var(--seal)] pb-1 font-medium text-[var(--seal)]" to="/student/login">Students</Link></li>
      <li><Link className="opacity-70 hover:text-[var(--seal)]" to="/employer">Verify</Link></li>
    </ul>
  </nav>
</header>
<main className="mx-auto max-w-[420px] px-6 pb-24 pt-32">
  <div className="text-center mb-10">
    <span className="font-sans text-[11px] uppercase tracking-[0.2em] text-[var(--ink)]/50">Student Access</span>
    <h1 className="font-serif text-[40px] leading-[1.1] tracking-tight mt-3 mb-3">Student Vault</h1>
    <p className="font-sans text-[14px] text-[var(--on-surface-variant)] opacity-80">
      Sign in to view and share your credentials.
    </p>
  </div>
  <form id="student-login-form" className="space-y-5" onSubmit={handleSubmit}>
    <div>
      <label className="block font-sans text-[11px] uppercase tracking-[0.08em] text-[var(--on-surface-variant)] mb-2" htmlFor="uid">
        Student DID
      </label>
      <input id="uid" name="uid" type="text" required
             placeholder="e.g. did:ethr:0xabc123..."
             value={uid} onChange={(e) => setUid(e.target.value)}
             className="w-full h-12 px-4 bg-[var(--surface-container-low)] border border-[var(--mist)]/50 rounded-[6px]
                    font-sans text-[14px] focus:outline-none focus:border-[var(--seal)] transition-colors"/>
    </div>
    <div>
      <label className="block font-sans text-[11px] uppercase tracking-[0.08em] text-[var(--on-surface-variant)] mb-2" htmlFor="password">
        Password
      </label>
      <input id="password" name="password" type="password" autoComplete="current-password" required
             placeholder="••••••"
             value={password} onChange={(e) => setPassword(e.target.value)}
             className="w-full h-12 px-4 bg-[var(--surface-container-low)] border border-[var(--mist)]/50 rounded-[6px]
                    font-sans text-[14px] focus:outline-none focus:border-[var(--seal)] transition-colors"/>
    </div>
    <p id="login-error" className="font-mono text-[12px] text-red-500 min-h-[1.2em]">{error}</p>
    <button type="submit"
            className="btn-primary w-full h-12 bg-slate-50 text-emerald-900 rounded-[6px] font-sans text-[11px]
                   uppercase tracking-[0.15em] font-semibold hover:bg-emerald-400 transition-colors" data-ripple="">
      Sign In
    </button>
  </form>
  <p className="text-center mt-8 font-sans text-[12px] text-[var(--ink)]/40">
    Are you a university? <Link to="/university-login" className="text-[var(--seal)] underline underline-offset-4">University login →</Link>
  </p>
    <p className="text-center mt-4 font-sans text-[11px] text-[var(--ink)]/30">
    Use the exact DID used during issuance. Demo password: 1234
  </p>
</main>
<footer className="border-t border-mist/50 px-8 py-8 text-center font-sans text-[11px] uppercase tracking-widest text-ink/40">
  © 2026 CertiChain Ledger
</footer>
    </div>
  );
};

export default StudentLogin;
