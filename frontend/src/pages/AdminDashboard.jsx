import React, { useState } from 'react';
import { addBatchCredential, commitBatch, getBatchStatus } from '../api/client';
import { PlusCircle, Search, Save, AlertCircle, FileText } from 'lucide-react';

const AdminDashboard = () => {
  const [activeBatchId, setActiveBatchId] = useState('batch-001');
  const [formData, setFormData] = useState({
    student_did: '',
    student_name: '',
    cgpa: '',
    degree: '',
    graduation_date: '',
  });

  const [stagedCredentials, setStagedCredentials] = useState([]);
  const [commitStatus, setCommitStatus] = useState(null);
  
  // Lookup states
  const [lookupBatchId, setLookupBatchId] = useState('');
  const [lookupResult, setLookupResult] = useState(null);

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleStageCredential = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('cc_token');
      const payload = {
        batch_id: activeBatchId,
        ...formData,
      };
      // Sends to backend to add to in-memory batch managed by backend
      await addBatchCredential(payload, token);
      
      // Update local UI state
      setStagedCredentials([...stagedCredentials, payload]);
      setFormData({
        student_did: '',
        student_name: '',
        cgpa: '',
        degree: '',
        graduation_date: '',
      });
    } catch (err) {
      console.error('Failed to stage credential:', err);
      alert('Failed to stage credential. See console.');
    }
  };

  const handleCommitBatch = async () => {
    if (stagedCredentials.length === 0) {
      alert('Batch is empty');
      return;
    }
    try {
      setCommitStatus('committing');
      const token = localStorage.getItem('cc_token');
      const result = await commitBatch(activeBatchId, token);
      setCommitStatus('success');
      setStagedCredentials([]); // Backend clears its memory too
      
      alert(`Batch committed successfully! Root Hash: ${result.merkle_root}`);
    } catch (err) {
      console.error(err);
      setCommitStatus('error');
      alert('Failed to commit batch.');
    }
  };

  const handleLookup = async (e) => {
    e.preventDefault();
    try {
      const status = await getBatchStatus(lookupBatchId);
      setLookupResult(status);
    } catch (err) {
      setLookupResult({ error: 'Batch not found or an error occurred' });
    }
  };

  return (
    <div className="grid gap-6">
      <div className="grid grid-cols-2 gap-6">
        {/* ADD CREDENTIALS FORM */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <PlusCircle className="text-emerald" size={20} />
            <h3 className="font-serif text-lg">Stage Credential</h3>
          </div>
          <form onSubmit={handleStageCredential} className="flex flex-col gap-4">
            <div>
              <label className="text-xs text-muted mb-1 block">Batch ID</label>
              <input 
                type="text" 
                className="input-field" 
                value={activeBatchId} 
                onChange={(e) => setActiveBatchId(e.target.value)} 
                required 
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
               <div>
                  <label className="text-xs text-muted mb-1 block">Student DID</label>
                  <input type="text" name="student_did" className="input-field" value={formData.student_did} onChange={handleInputChange} required />
               </div>
               <div>
                  <label className="text-xs text-muted mb-1 block">Student Name</label>
                  <input type="text" name="student_name" className="input-field" value={formData.student_name} onChange={handleInputChange} required />
               </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
               <div>
                  <label className="text-xs text-muted mb-1 block">CGPA / Grade</label>
                  <input type="text" name="cgpa" className="input-field" value={formData.cgpa} onChange={handleInputChange} required />
               </div>
               <div>
                  <label className="text-xs text-muted mb-1 block">Degree/Program</label>
                  <input type="text" name="degree" className="input-field" value={formData.degree} onChange={handleInputChange} required />
               </div>
               <div>
                  <label className="text-xs text-muted mb-1 block">Graduation Date</label>
                  <input type="date" name="graduation_date" className="input-field" value={formData.graduation_date} onChange={handleInputChange} required />
               </div>
            </div>
            <button type="submit" className="btn btn-secondary mt-2">
              Add to In-Memory Batch
            </button>
          </form>
        </div>

        {/* BATCH STATUS & STAGED LIST */}
        <div className="card flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <FileText className="text-emerald" size={20} />
              <h3 className="font-serif text-lg">In-Memory Batch</h3>
            </div>
            <span className="status-pill">{stagedCredentials.length} Items</span>
          </div>
          
          <div className="flex-1 border border-color rounded mb-4 overflow-y-auto" style={{ maxHeight: '200px' }}>
            {stagedCredentials.length === 0 ? (
              <div className="p-4 text-center text-muted text-sm my-auto">No credentials staged.</div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>DID</th>
                    <th>Name</th>
                    <th>Program</th>
                  </tr>
                </thead>
                <tbody>
                  {stagedCredentials.map((cred, i) => (
                    <tr key={i}>
                      <td className="font-mono text-xs truncate max-w-[100px]" title={cred.student_did}>{cred.student_did}</td>
                      <td className="text-sm">{cred.student_name}</td>
                      <td className="text-sm">{cred.degree}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <button 
            className="btn btn-primary w-full" 
            onClick={handleCommitBatch} 
            disabled={stagedCredentials.length === 0 || commitStatus === 'committing'}
          >
            <Save size={18} />
            {commitStatus === 'committing' ? 'Committing to Chain...' : 'Finalize & Commit Batch'}
          </button>
        </div>
      </div>

      {/* BATCH LOOKUP SECTION */}
      <div className="card">
         <div className="flex items-center gap-2 mb-4">
            <Search className="text-emerald" size={20} />
            <h3 className="font-serif text-lg">Batch Status Lookup</h3>
         </div>
         <form onSubmit={handleLookup} className="flex gap-4">
            <input 
              type="text" 
              className="input-field" 
              placeholder="Enter Batch ID" 
              value={lookupBatchId}
              onChange={(e) => setLookupBatchId(e.target.value)}
            />
            <button type="submit" className="btn btn-secondary whitespace-nowrap">Check Status</button>
         </form>

         {lookupResult && (
           <div className="mt-4 p-4 rounded bg-surface-elevated">
             {lookupResult.error ? (
               <div className="flex items-center gap-2 text-error">
                 <AlertCircle size={18} />
                 <span>{lookupResult.error}</span>
               </div>
             ) : (
               <pre className="font-mono text-xs overflow-x-auto text-secondary">
                 {JSON.stringify(lookupResult, null, 2)}
               </pre>
             )}
           </div>
         )}
      </div>
    </div>
  );
};

export default AdminDashboard;
