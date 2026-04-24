import React from 'react';
import { Link, useLocation, Navigate } from 'react-router-dom';

const VerifySuccess = () => {
  const location = useLocation();
  const result = location.state?.result;

  if (!result) {
    return <Navigate to="/employer" replace />;
  }

  return (
    <div className="selection:bg-emerald-500 selection:text-white min-h-screen bg-transparent text-slate-50 flex flex-col pt-24 items-center">
      <header className="fixed left-0 right-0 top-0 z-50 flex min-h-[72px] w-full items-center border-b border-white/10 bg-slate-900/40 px-6 backdrop-blur-[12px] md:px-8">
        <Link className="font-serif text-2xl italic text-white" to="/index">CertiChain</Link>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center w-full max-w-2xl px-6 py-12">
        <div className="mb-6 rounded-full bg-emerald-500/10 p-5 border border-emerald-500/30">
          <span className="material-symbols-outlined text-[64px] text-emerald-500">verified</span>
        </div>
        
        <h1 className="font-serif text-4xl text-emerald-500 mb-2">Authentic Credential</h1>
        <p className="text-slate-400 font-sans mb-10 text-center">
          This document has been cryptographically verified against the blockchain ledger.
        </p>

        <div className="w-full bg-slate-800/80 border border-emerald-600/50 rounded-xl p-8 shadow-lg shadow-emerald-900/20 text-left space-y-4">
          <div className="border-b border-slate-700 pb-4 mb-4">
             <h2 className="text-xs uppercase tracking-widest text-emerald-500 font-semibold mb-1">Student Name</h2>
             <p className="font-serif text-2xl text-white">{result.student_name || 'N/A'}</p>
          </div>
          
          <div className="grid grid-cols-2 gap-6">
            <div>
               <h2 className="text-xs uppercase tracking-widest text-slate-400 font-semibold mb-1">Institution</h2>
               <p className="text-slate-100">{result.university_name || 'N/A'}</p>
            </div>
            <div>
               <h2 className="text-xs uppercase tracking-widest text-slate-400 font-semibold mb-1">Degree Program</h2>
               <p className="text-slate-100">{result.degree || 'N/A'}</p>
            </div>
            <div>
               <h2 className="text-xs uppercase tracking-widest text-slate-400 font-semibold mb-1">Graduation Year</h2>
               <p className="text-slate-100">{result.graduation_year || 'N/A'}</p>
            </div>
            <div>
               <h2 className="text-xs uppercase tracking-widest text-slate-400 font-semibold mb-1">Current Status</h2>
               <p className="text-emerald-400 font-bold">{result.is_revoked ? 'REVOKED' : 'VALID / ACTIVE'}</p>
            </div>
          </div>
        </div>

        <Link to="/employer" className="mt-12 btn-primary inline-flex w-full items-center justify-center rounded-[6px] bg-slate-800 border border-slate-700 py-3 text-[11px] font-medium uppercase tracking-[0.08em] hover:bg-slate-700 hover:border-slate-500 text-white transition-colors">
          Verify Another Credential
        </Link>
      </main>
    </div>
  );
};

export default VerifySuccess;
