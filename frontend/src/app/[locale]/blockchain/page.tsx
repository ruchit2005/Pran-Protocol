'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';

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
  const t = useTranslations('Blockchain');
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
      const statsResponse = await fetch('/api/blockchain/stats');
      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        setStats(statsData);
      }

      // Fetch personal audit trail (requires auth)
      const token = localStorage.getItem('token');
      if (token) {
        // Get anonymous_id from backend (includes master_key salt)
        const anonIdResponse = await fetch('/api/auth/anonymous-id', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        if (anonIdResponse.ok) {
          const anonData = await anonIdResponse.json();
          const anonymousId = anonData.anonymous_id;

          // Fetch audit trail using the correct anonymous_id
          const auditResponse = await fetch(
            `/api/compliance/audit/${anonymousId}`,
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
      setError(t('error'));
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FDFCF8] p-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-20">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary mx-auto"></div>
            <p className="mt-4 text-stone-600">{t('loading')}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FDFCF8] p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.push('/')}
            className="mb-4 text-primary hover:text-primary-dark flex items-center gap-2 font-medium transition-colors"
          >
            ← {t('backToChat')}
          </button>
          <h1 className="text-4xl font-bold text-stone-800 flex items-center gap-3 font-serif">
            🔗 {t('title')}
          </h1>
          <p className="text-stone-600 mt-2">
            {t('subtitle')}
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setActiveTab('stats')}
            className={`px-6 py-3 rounded-xl font-semibold transition-all ${activeTab === 'stats'
                ? 'bg-primary text-white shadow-lg'
                : 'bg-white text-stone-700 hover:bg-stone-50 border border-stone-200'
              }`}
          >
            📊 {t('tabStats')}
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`px-6 py-3 rounded-xl font-semibold transition-all ${activeTab === 'audit'
                ? 'bg-primary text-white shadow-lg'
                : 'bg-white text-stone-700 hover:bg-stone-50 border border-stone-200'
              }`}
          >
            📋 {t('tabAudit')}
          </button>
        </div>

        {/* Statistics Tab */}
        {activeTab === 'stats' && stats && (
          <div className="space-y-6">
            {/* Blockchain Info Card */}
            <div className="bg-white rounded-xl shadow-organic p-6 border border-stone-100">
              <h2 className="text-2xl font-bold text-stone-800 mb-4 font-serif">
                Blockchain Audit System
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-[#F2E8CF]/30 p-4 rounded-xl border border-[#F2E8CF]">
                  <div className="text-3xl font-bold text-primary">
                    {stats.total_blocks}
                  </div>
                  <div className="text-stone-600 text-sm">{t('totalBlocks')}</div>
                </div>
                <div className="bg-green-50 p-4 rounded-xl border border-green-100">
                  <div className="text-3xl font-bold text-green-600">
                    {stats.total_audits}
                  </div>
                  <div className="text-stone-600 text-sm">{t('totalAudits')}</div>
                </div>
                <div className="bg-purple-50 p-4 rounded-xl border border-purple-100">
                  <div className="text-3xl font-bold text-purple-600">
                    {stats.unique_users}
                  </div>
                  <div className="text-stone-600 text-sm">{t('uniqueUsers')}</div>
                </div>
              </div>

              {/* Chain Integrity */}
              <div className={`p-4 rounded-xl mb-6 ${stats.chain_integrity
                  ? 'bg-green-50 border-2 border-green-200'
                  : 'bg-red-50 border-2 border-red-200'
                }`}>
                <div className="flex items-center gap-2">
                  <span className="text-2xl">
                    {stats.chain_integrity ? '✅' : '❌'}
                  </span>
                  <div>
                    <div className="font-bold text-stone-800">
                      {t('chainIntegrity')}: {stats.chain_integrity ? t('verified') : t('compromised')}
                    </div>
                    <div className="text-sm text-stone-600">
                      {stats.chain_integrity
                        ? t('integrityGood')
                        : t('integrityBad')}
                    </div>
                  </div>
                </div>
              </div>

              {/* Features */}
              <div className="mb-6">
                <h3 className="font-semibold text-stone-800 mb-3">{t('features')}</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {stats.features.map((feature, index) => (
                    <div key={index} className="flex items-center gap-2 text-stone-700">
                      <span className="text-green-500">✓</span>
                      {feature}
                    </div>
                  ))}
                </div>
              </div>

              {/* Actions Breakdown */}
              <div>
                <h3 className="font-semibold text-stone-800 mb-3">{t('actionsBreakdown')}</h3>
                <div className="space-y-2">
                  {Object.entries(stats.actions_breakdown).map(([action, count]) => (
                    <div key={action} className="flex items-center gap-3">
                      <div className="w-32 font-mono text-sm text-stone-600">
                        {action}
                      </div>
                      <div className="flex-1 bg-stone-200 rounded-full h-6">
                        <div
                          className="bg-primary h-6 rounded-full flex items-center justify-end pr-2 text-white text-xs font-semibold"
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
              <div className="bg-white rounded-xl shadow-organic p-8 text-center border border-stone-100">
                <div className="text-6xl mb-4">🔒</div>
                <h3 className="text-xl font-semibold text-stone-800 mb-2">
                  {t('noRecords')}
                </h3>
                <p className="text-stone-600">
                  {t('noRecordsDesc')}
                </p>
              </div>
            ) : (
              <>
                <div className="bg-[#F2E8CF]/30 border-l-4 border-primary p-4 rounded">
                  <p className="text-sm text-stone-700">
                    📊 {t('showing', { count: auditTrail.length })}
                  </p>
                </div>

                {auditTrail.map((log, index) => (
                  <div
                    key={index}
                    className="bg-white rounded-xl shadow-organic p-6 hover:shadow-lg transition-shadow border border-stone-100"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-2xl">
                            {log.action === 'DIAGNOSIS' ? '🩺' :
                              log.action === 'DATA_ACCESS' ? '🔍' :
                                log.action === 'PRESCRIPTION' ? '💊' : '📝'}
                          </span>
                          <h3 className="text-xl font-bold text-stone-800">
                            {log.action}
                          </h3>
                        </div>
                        <div className="text-sm text-stone-500">
                          {new Date(log.timestamp).toLocaleString()}
                        </div>
                      </div>
                      <div className="bg-primary/10 px-3 py-1 rounded-full text-primary font-semibold text-sm">
                        {t('block')} #{log.block_number}
                      </div>
                    </div>

                    {/* Show message content if available */}
                    {log.metadata && (log.metadata.message_preview || log.metadata.response_preview) && (
                      <div className="my-4 p-4 bg-[#F2E8CF]/20 rounded-lg border border-[#F2E8CF]">
                        {log.metadata.message_preview && (
                          <div className="mb-2">
                            <span className="font-semibold text-stone-700">💬 {t('msg')}: </span>
                            <span className="text-stone-800">{log.metadata.message_preview}</span>
                          </div>
                        )}
                        {log.metadata.response_preview && (
                          <div>
                            <span className="font-semibold text-stone-700">🤖 {t('response')}: </span>
                            <span className="text-stone-800">{log.metadata.response_preview}</span>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="space-y-2 text-sm">
                      <div className="flex gap-2">
                        <span className="font-semibold text-stone-600 w-32">
                          {t('blockHash')}:
                        </span>
                        <span className="font-mono text-xs text-stone-800 break-all">
                          {log.block_hash}
                        </span>
                      </div>
                      <div className="flex gap-2">
                        <span className="font-semibold text-stone-600 w-32">
                          {t('dataHash')}:
                        </span>
                        <span className="font-mono text-xs text-stone-800 break-all">
                          {log.data_hash}
                        </span>
                      </div>
                    </div>

                    {log.metadata && Object.keys(log.metadata).length > 0 && (
                      <details className="mt-4">
                        <summary className="cursor-pointer text-primary hover:text-primary-dark font-semibold text-sm">
                          📋 {t('viewMetadata')}
                        </summary>
                        <pre className="mt-2 p-3 bg-stone-50 rounded text-xs overflow-auto max-h-60">
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
