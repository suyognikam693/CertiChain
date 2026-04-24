import React, { useState } from 'react';
import { verifyCredential } from '../api/client';
import { Search, CheckCircle, XCircle, ShieldAlert } from 'lucide-react';

const VerifierHub = () => {
  const [formData, setFormData] = useState({
    credential_hash: '',
    proof: '', // we will parse this as JSON array
    leaf_index: ''
  });
  
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      // Parse proof array safely
      let parsedProof = [];
      if (formData.proof) {
        try {
          parsedProof = JSON.parse(formData.proof);
          if (!Array.isArray(parsedProof)) throw new Error('Proof must be an array');
        } catch (err) {
          alert('Invalid proof array format. Please provide a valid JSON array of hashes. e.g. ["0x..."]');
          setLoading(false);
          return;
        }
      }

      const payload = {
        credential_hash: formData.credential_hash,
        proof: parsedProof,
        leaf_index: parseInt(formData.leaf_index, 10)
      };

      const res = await verifyCredential(payload);
      setResult(res);
    } catch (err) {
      console.error(err);
      setResult({ error: 'Verification request failed. Ensure inputs are correct.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto grid gap-6">
      <div className="text-center mb-4">
        <h2 className="font-serif text-3xl mb-2 text-emerald">Verify Credentials</h2>
        <p className="text-secondary">Perform an on-chain cryptographic verification using Merkle proofs</p>
      </div>

      <div className="card">
        <form onSubmit={handleVerify} className="flex flex-col gap-5">
          <div>
            <label className="text-sm text-secondary mb-1 block">Credential Hash</label>
            <input 
              type="text" 
              name="credential_hash"
              className="input-field font-mono text-sm" 
              placeholder="0x..."
              value={formData.credential_hash}
              onChange={handleInputChange}
              required
            />
          </div>

          <div>
            <label className="text-sm text-secondary mb-1 block">Merkle Proof Array (JSON format)</label>
            <textarea 
              name="proof"
              className="input-field font-mono text-sm min-h-[100px]" 
              placeholder='["0x..."]'
              value={formData.proof}
              onChange={handleInputChange}
              required
            ></textarea>
          </div>

          <div>
            <label className="text-sm text-secondary mb-1 block">Leaf Index</label>
            <input 
              type="number" 
              name="leaf_index"
              className="input-field font-mono text-sm" 
              placeholder="Number"
              value={formData.leaf_index}
              onChange={handleInputChange}
              required
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={loading}>
            <Search size={18} />
            {loading ? 'Verifying on-chain...' : 'Run Cryptographic Verification'}
          </button>
        </form>
      </div>

      {result && (
        <div className={`card border-l-4 ${result.is_valid ? 'border-emerald-500' : 'border-error'}`}>
          <div className="flex items-center gap-3 mb-4">
            {result.error ? (
               <ShieldAlert className="text-error" size={28} />
            ) : result.is_valid ? (
               <CheckCircle className="text-emerald" size={28} />
            ) : (
               <XCircle className="text-error" size={28} />
            )}
            <h3 className="font-serif text-2xl">
               {result.error ? 'Verification Error' : (result.is_valid ? 'Cryptographically Valid' : 'Invalid Proof')}
            </h3>
          </div>
          
          <div className="bg-surface-elevated p-4 rounded font-mono text-xs overflow-x-auto text-secondary">
             <pre>{JSON.stringify(result, null, 2)}</pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default VerifierHub;
