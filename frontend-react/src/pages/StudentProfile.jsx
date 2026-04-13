import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getStudentCredentials, getIPFSData, getStudentQRCodes } from '../api/client';
import { GraduationCap, ShieldCheck, RefreshCw, AlertTriangle } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

// Web Crypto API helper for SHA-256
async function sha256(message) {
  const msgBuffer = new TextEncoder().encode(message);
  const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return '0x' + hashHex;
}

const StudentProfile = () => {
  const { did } = useParams();
  const [loading, setLoading] = useState(true);
  const [credentials, setCredentials] = useState([]);
  const [qrCodes, setQrCodes] = useState(null);

  useEffect(() => {
    const fetchIdentity = async () => {
      setLoading(true);
      try {
        // 1. Fetch Tuples / Pointers from backend
        const tuplesRes = await getStudentCredentials(did);
        const tuples = Array.isArray(tuplesRes) ? tuplesRes : tuplesRes.credentials || [];

        // 2. Flow: For each tuple, fetch from IPFS, and verify hash
        const processedCreds = await Promise.all(tuples.map(async (tuple) => {
          try {
            // Pull JSON from IPFS
            const ipfsData = await getIPFSData(tuple.cid);
            
            // Recompute local hash for verification
            // Assuming canonical JSON stringification or just stringifying the raw object
            const canonicalString = JSON.stringify(ipfsData, Object.keys(ipfsData).sort());
            const localHash = await sha256(canonicalString);
            
            // Compare hashes normalized to lowercase without '0x' prefix
            const normalizeHash = (h = '') => h.replace(/^0x/i, '').toLowerCase();
            const isVerifiedLocally = normalizeHash(localHash) === normalizeHash(tuple.credential_hash);

            return {
              ...tuple,
              ipfsData,
              localHash,
              isVerifiedLocally
            };
          } catch (err) {
            return {
              ...tuple,
              error: 'IPFS Fetch Failed or Tampered data',
              isVerifiedLocally: false
            };
          }
        }));

        setCredentials(processedCreds);

        // Fetch QRs
        try {
          const qrs = await getStudentQRCodes(did);
          setQrCodes(qrs);
        } catch (err) {
          console.warn("QR fetching failed or endpoint not ready", err);
        }

      } catch (err) {
        console.error("Failed to load student data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchIdentity();
  }, [did]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64 text-emerald">
        <RefreshCw className="animate-spin" size={32} />
      </div>
    );
  }

  return (
    <div className="grid gap-6">
      <div className="flex items-center gap-3 mb-2">
        <GraduationCap className="text-emerald" size={28} />
        <h2 className="font-serif text-2xl">Identity Vault: {did}</h2>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 flex flex-col gap-4">
          <h3 className="font-serif text-lg text-secondary">Verified Credentials</h3>
          {credentials.length === 0 ? (
            <div className="card text-center text-muted p-8">
              No credentials found for this identity.
            </div>
          ) : (
            credentials.map((cred, idx) => (
              <div key={idx} className="card border-l-4" style={{ borderLeftColor: cred.isVerifiedLocally ? 'var(--emerald-500)' : 'var(--error)' }}>
                {cred.error ? (
                  <div className="flex items-center gap-2 text-error">
                    <AlertTriangle />
                    <span>{cred.error}</span>
                  </div>
                ) : (
                  <div>
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <h4 className="font-serif text-xl mb-1">{cred.ipfsData.degree || 'Credential'}</h4>
                        <p className="text-secondary">{cred.ipfsData.student_name}</p>
                      </div>
                      <div className="status-pill" style={{ color: 'var(--emerald-500)', borderColor: 'var(--emerald-500)' }}>
                        <ShieldCheck size={14} />
                        Locally Verified
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm mt-4 p-3 bg-surface-elevated rounded">
                      <div>
                        <span className="text-muted block text-xs">IPFS CID</span>
                        <span className="font-mono text-emerald truncate block w-full" title={cred.cid}>{cred.cid || 'N/A'}</span>
                      </div>
                      <div>
                        <span className="text-muted block text-xs">Recomputed Hash (SHA-256)</span>
                        <span className="font-mono truncate block w-full" title={cred.localHash}>{cred.localHash}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="col-span-1 flex flex-col gap-4">
        <h3 className="font-serif text-lg text-secondary">Verification QRs</h3>
          {qrCodes ? (
             <div className="card">
               {/* Iterate over qrCodes if it's an array or just display the raw info */}
               <pre className="text-xs font-mono">{JSON.stringify(qrCodes, null, 2)}</pre>
             </div>
          ) : (
            credentials.map((cred, idx) => {
              if (cred.error) return null;
              // Fallback to purely local QR generation
              const qrValue = JSON.stringify({ 
                did, 
                cid: cred.cid, 
                hash: cred.localHash 
              });
              
              return (
                <div key={`qr-${idx}`} className="card flex flex-col items-center gap-3">
                  <span className="text-sm text-secondary truncate w-full text-center">{cred.ipfsData.degree}</span>
                  <div className="p-3 bg-white rounded-lg">
                    <QRCodeSVG value={qrValue} size={150} />
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export default StudentProfile;
