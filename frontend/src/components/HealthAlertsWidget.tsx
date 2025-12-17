
"use client";

import { useEffect, useState } from 'react';
import { AlertCircle, ExternalLink, Activity, X } from 'lucide-react';
import { useTranslations } from 'next-intl';

type Alert = {
  title: string;
  url: string;
  source: string;
  publishedAt: string;
  description?: string;
};

interface HealthAlertsWidgetProps {
  isOpen: boolean;
  onClose: () => void;
  onAskMore: (alert: Alert) => void;
}

export default function HealthAlertsWidget({ isOpen, onClose, onAskMore }: HealthAlertsWidgetProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const t = useTranslations('Alerts');

  useEffect(() => {
    if (isOpen) {
      fetchAlerts();
    }
  }, [isOpen]);

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/alerts');
      if (res.ok) {
        const data = await res.json();
        setAlerts(data.alerts || []);
      }
    } catch (error) {
      console.error("Failed to fetch alerts", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className={`
        fixed inset-y-0 right-0 z-50 w-80 bg-white/90 backdrop-blur-md shadow-2xl transform transition-transform duration-300 ease-in-out border-l border-stone-200
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}
      `}
    >
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="p-5 border-b border-stone-200 flex items-center justify-between bg-red-50/50">
          <div className="flex items-center gap-2 text-red-700">
            <Activity className="w-5 h-5 animate-pulse" />
            <span className="font-bold font-serif text-lg">{t('sentinel')}</span>
          </div>
          <button
            onClick={onClose}
            className="text-stone-500 hover:text-stone-800 transition-colors bg-white rounded-full p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-40 text-stone-400 space-y-2">
              <Activity className="w-6 h-6 animate-spin" />
              <span className="text-xs">{t('scanning')}</span>
            </div>
          ) : alerts.length === 0 ? (
            <div className="text-center text-stone-500 py-10 px-4">
              <p className="text-sm">{t('noAlerts')}</p>
            </div>
          ) : (
            alerts.map((alert, idx) => (
              <div
                key={idx}
                className="bg-white border border-stone-200 rounded-xl p-4 shadow-sm hover:shadow-md hover:border-red-200 transition-all"
              >
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-stone-800 leading-tight mb-1">
                      {alert.title}
                    </h4>
                    <div className="flex items-center justify-between mt-2 mb-3">
                      <span className="text-[10px] uppercase font-bold text-stone-400 bg-stone-100 px-1.5 py-0.5 rounded">
                        {alert.source}
                      </span>
                      <a
                        href={alert.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-stone-400 hover:text-red-500 transition-colors"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <button
                      onClick={() => {
                        onAskMore(alert);
                        onClose();
                      }}
                      className="w-full text-xs font-medium text-[#3A5A40] bg-emerald-50 hover:bg-emerald-100 px-3 py-2 rounded-lg transition-colors flex items-center justify-center gap-1.5"
                    >
                      <span>💬</span>
                      <span>{t('askMore')}</span>
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="p-4 border-t border-stone-200 bg-stone-50 text-[10px] text-stone-400 text-center">
          {t('footer')}
        </div>
      </div>
    </div >
  );
}
