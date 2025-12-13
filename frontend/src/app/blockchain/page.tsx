'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface BlockchainStats {
  blockchain_type: string;
  features: string[];
  total_blocks: number;
  total_audits: number;
  unique_users: number;
  actions_breakdown: Record<string, number>;
  chain_integrity: boolean;
}

interface AuditLog {
  block_number: number;
  action: string;
  data_hash: string;
  timestamp: string;
  block_hash: string;
  previous_hash: string;
  metadata: any;
}

export default function BlockchainAuditPage() {
  const router = useRouter();
  const [stats, setStats] = useState<BlockchainStats | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'stats' | 'audit'>('stats');

  useEffect(() => {
    fetchBlockchainData();
  }, []);

  const fetchBlockchainData = async () => {
    try {
      setLoading(true);
      
      // Fetch public stats (no auth needed)
      const statsResponse = await fetch('http://localhost:8000/blockchain/stats');
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }

      // Fetch personal audit trail (requires auth)
      const token = localStorage.getItem('token');
      if (token) {
        // Get anonymous_id from backend (includes master_key salt)
        const anonIdResponse = await fetch('http://localhost:8000/auth/anonymous-id', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (anonIdResponse.ok) {
          const anonData = await anonIdResponse.json();
          const anonymousId = anonData.anonymous_id;
          
          // Fetch audit trail using the correct anonymous_id
          const auditResponse = await fetch(
            `http://localhost:8000/compliance/audit/${anonymousId}`,
            {
              headers: {
                'Authorization': `Bearer ${token}`
              }
            }
          );
          
          if (auditResponse.ok) {
            const auditData = await auditResponse.json();
            setAuditTrail(auditData.audit_trail || []);
          } else {
            console.error('Audit trail fetch failed:', await auditResponse.text());
          }
        }
      }
    } catch (err) {
      setError('Failed to load blockchain data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading blockchain data...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.push('/')}
            className="mb-4 text-indigo-600 hover:text-indigo-700 flex items-center gap-2"
          >
            ← Back to Chat
          </button>
          <h1 className="text-4xl font-bold text-gray-800 flex items-center gap-3">
            🔗 Blockchain Audit Trail
          </h1>
          <p className="text-gray-600 mt-2">
            Immutable, tamper-proof medical record audit system
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setActiveTab('stats')}
            className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
              activeTab === 'stats'
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            📊 Statistics
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-6 py-3 rounded-lg font-semibold transition-colors ${
              activeTab === 'audit'
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-50'
            }`}
          >
            📋 My Audit Trail
          </button>
        </div>

        {/* Statistics Tab */}
        {activeTab === 'stats' && stats && (
          <div className="space-y-6">
            {/* Blockchain Info Card */}
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-800 mb-4">
                {stats.blockchain_type}
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-3xl font-bold text-blue-600">
                    {stats.total_blocks}
                  </div>
                  <div className="text-gray-600 text-sm">Total Blocks</div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-3xl font-bold text-green-600">
                    {stats.total_audits}
                  </div>
                  <div className="text-gray-600 text-sm">Total Audits</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="text-3xl font-bold text-purple-600">
                    {stats.unique_users}
                  </div>
                  <div className="text-gray-600 text-sm">Unique Users</div>
                </div>
              </div>

              {/* Chain Integrity */}
              <div className={`p-4 rounded-lg mb-6 ${
                stats.chain_integrity 
                  ? 'bg-green-50 border-2 border-green-200' 
                  : 'bg-red-50 border-2 border-red-200'
              }`}>
                <div className="flex items-center gap-2">
                  <span className="text-2xl">
                    {stats.chain_integrity ? '✅' : '❌'}
                  </span>
                  <div>
                    <div className="font-bold text-gray-800">
                      Chain Integrity: {stats.chain_integrity ? 'VERIFIED' : 'COMPROMISED'}
                    </div>
                    <div className="text-sm text-gray-600">
                      {stats.chain_integrity 
                        ? 'No tampering detected. All blocks are valid.'
                        : 'WARNING: Tampering detected in blockchain!'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Features */}
              <div className="mb-6">
                <h3 className="font-semibold text-gray-800 mb-3">Features:</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {stats.features.map((feature, index) => (
                    <div key={index} className="flex items-center gap-2 text-gray-700">
                      <span className="text-green-500">✓</span>
                      {feature}
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions Breakdown */}
              <div>
                <h3 className="font-semibold text-gray-800 mb-3">Actions Breakdown:</h3>
                <div className="space-y-2">
                  {Object.entries(stats.actions_breakdown).map(([action, count]) => (
                    <div key={action} className="flex items-center gap-3">
                      <div className="w-32 font-mono text-sm text-gray-600">
                        {action}
                      </div>
                      <div className="flex-1 bg-gray-200 rounded-full h-6">
                        <div
                          className="bg-indigo-600 h-6 rounded-full flex items-center justify-end pr-2 text-white text-xs font-semibold"
                          style={{
                            width: `${(count / stats.total_audits) * 100}%`
                          }}
                        >
                          {count}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Audit Trail Tab */}
        {activeTab === 'audit' && (
          <div className="space-y-4">
            {auditTrail.length === 0 ? (
              <div className="bg-white rounded-xl shadow-lg p-8 text-center">
                <div className="text-6xl mb-4">🔒</div>
                <h3 className="text-xl font-semibold text-gray-800 mb-2">
                  No Audit Records Yet
                </h3>
                <p className="text-gray-600">
                  Your medical interactions will appear here as you use the AI assistant.
                </p>
              </div>
            ) : (
              <>
                <div className="bg-indigo-50 border-l-4 border-indigo-600 p-4 rounded">
                  <p className="text-sm text-gray-700">
                    📊 Showing {auditTrail.length} audit records from your private blockchain
                  </p>
                </div>
                
                {auditTrail.map((log, index) => (
                  <div
                    key={index}
                    className="bg-white rounded-xl shadow-lg p-6 hover:shadow-xl transition-shadow"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-2xl">
                            {log.action === 'DIAGNOSIS' ? '🩺' :
                             log.action === 'DATA_ACCESS' ? '🔍' :
                             log.action === 'PRESCRIPTION' ? '💊' : '📝'}
                          </span>
                          <h3 className="text-xl font-bold text-gray-800">
                            {log.action}
                          </h3>
                        </div>
                        <div className="text-sm text-gray-500">
                          {new Date(log.timestamp).toLocaleString()}
                        </div>
                      </div>
                      <div className="bg-indigo-100 px-3 py-1 rounded-full text-indigo-700 font-semibold text-sm">
                        Block #{log.block_number}
                      </div>
                    </div>

                    {/* Show message content if available */}
                    {log.metadata && (log.metadata.message_preview || log.metadata.response_preview) && (
                      <div className="my-4 p-4 bg-blue-50 rounded-lg">
                        {log.metadata.message_preview && (
                          <div className="mb-2">
                            <span className="font-semibold text-gray-700">💬 Message: </span>
                            <span className="text-gray-800">{log.metadata.message_preview}</span>
                          </div>
                        )}
                        {log.metadata.response_preview && (
                          <div>
                            <span className="font-semibold text-gray-700">🤖 Response: </span>
                            <span className="text-gray-800">{log.metadata.response_preview}</span>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="space-y-2 text-sm">
                      <div className="flex gap-2">
                        <span className="font-semibold text-gray-600 w-32">
                          Block Hash:
                        </span>
                        <span className="font-mono text-xs text-gray-800 break-all">
                          {log.block_hash}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <span className="font-semibold text-gray-600 w-32">
                          Data Hash:
                        </span>
                        <span className="font-mono text-xs text-gray-800 break-all">
                          {log.data_hash}
                        </span>
                      </div>
                    </div>

                    {log.metadata && Object.keys(log.metadata).length > 0 && (
                      <details className="mt-4">
                        <summary className="cursor-pointer text-indigo-600 hover:text-indigo-700 font-semibold text-sm">
                          📋 View Full Metadata
                        </summary>
                        <pre className="mt-2 p-3 bg-gray-50 rounded text-xs overflow-auto max-h-60">
                          {JSON.stringify(log.metadata, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {error && (
          <div className="bg-red-50 border-l-4 border-red-600 p-4 rounded mt-4">
            <p className="text-red-800">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}
