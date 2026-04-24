import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const VerifyFailed = () => {
  const location = useLocation();
  const errorMsg = location.state?.error || 'Invalid or missing cryptographic proofs.';

  return (
    <div className="selection:bg-red-500 selection:text-white min-h-screen bg-transparent text-slate-50 flex flex-col pt-24 items-center">
      <header className="fixed left-0 right-0 top-0 z-50 flex min-h-[72px] w-full items-center border-b border-white/10 bg-slate-900/40 px-6 backdrop-blur-[12px] md:px-8">
        <Link className="font-serif text-2xl italic text-white" to="/index">CertiChain</Link>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center w-full max-w-2xl px-6 py-12">
        <div className="mb-6 rounded-full bg-red-500/10 p-5 border border-red-500/30">
          <span className="material-symbols-outlined text-[64px] text-red-500">gpp_bad</span>
        </div>
        
        <h1 className="font-serif text-4xl text-red-500 mb-2">Verification Failed</h1>
        <p className="text-slate-400 font-sans mb-10 text-center">
          The credential could not be authenticated against the blockchain ledger.
        </p>

        <div className="w-full bg-slate-800/80 border border-red-600/50 rounded-xl p-8 shadow-lg shadow-red-900/20 text-center space-y-4">
           <h2 className="text-sm uppercase tracking-widest text-slate-400 font-semibold">Error Details</h2>
           <p className="font-mono text-red-400 text-sm bg-red-950/40 p-4 rounded-md inline-block max-w-full overflow-hidden text-ellipsis whitespace-nowrap">
             {errorMsg}
           </p>
           <p className="text-xs text-slate-500 mt-4 max-w-md mx-auto">
             This failure occurs if the hash does not match, the Merkle tree array is incorrect, the issuer revoked the credential, or the document was tampered with.
           </p>
        </div>

        <Link to="/employer" className="mt-12 btn-primary inline-flex w-full items-center justify-center rounded-[6px] bg-slate-800 border border-slate-700 py-3 text-[11px] font-medium uppercase tracking-[0.08em] hover:bg-slate-700 hover:border-slate-500 text-white transition-colors">
          Return to Verifier
        </Link>
      </main>
    </div>
  );
};

export default VerifyFailed;
