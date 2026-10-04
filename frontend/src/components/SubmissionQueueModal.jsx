import React, { useState, useEffect } from 'react';
import {
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  ArrowRight,
  Zap,
  Layers,
  X,
  FileCode,
} from 'lucide-react';
import { getRecentSubmissions } from '../services/submissionService';

export default function SubmissionQueueModal({ isOpen, onClose, onOpenHistory }) {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadRecent = async () => {
    try {
      const data = await getRecentSubmissions(5);
      setSubmissions(data);
    } catch (err) {
      console.error('Erro ao carregar fila de submissões:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadRecent();
    }
  }, [isOpen]);

  useEffect(() => {
    const handleUpdate = () => {
      loadRecent();
    };
    window.addEventListener('sqlarena:submission-updated', handleUpdate);
    return () => window.removeEventListener('sqlarena:submission-updated', handleUpdate);
  }, []);

  if (!isOpen) return null;

  const formatRelativeTime = (isoString) => {
    if (!isoString) return 'agora';
    const diffMs = Date.now() - new Date(isoString).getTime();
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 60) return `há ${diffSec}s`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `há ${diffMin} min`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `há ${diffHours}h`;
    return `há ${Math.floor(diffHours / 24)} dias`;
  };

  const getStatusBadge = (sub) => {
    if (sub.status === 'PROCESSING') {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 dark:bg-[#262b35] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-[#333a47]">
          <Loader2 className="w-3.5 h-3.5 animate-spin text-slate-500" />
          Processando...
        </span>
      );
    }
    if (sub.outcome === 'SUCCESS') {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          Sucesso
        </span>
      );
    }
    if (sub.outcome === 'WRONG_ANSWER') {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
          Divergente
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
        <XCircle className="w-3.5 h-3.5 text-rose-500" />
        Erro SQL
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end p-4 sm:p-6 lg:p-8 bg-black/50 backdrop-blur-xs animate-in fade-in duration-150">
      {/* Background click to close */}
      <div className="fixed inset-0 -z-10" onClick={onClose} />

      {/* Popover Card */}
      <div className="w-full max-w-md mt-14 sm:mt-16 rounded-3xl bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#323846] shadow-2xl overflow-hidden transition-all duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-[#2d3340] bg-slate-50/80 dark:bg-[#191c23]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-slate-100 dark:bg-[#282d37] border border-slate-200 dark:border-[#353d4d] flex items-center justify-center text-slate-700 dark:text-slate-300">
              <Layers className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 leading-tight">
                Fila de Submissões
              </h2>
              <p className="text-xs text-slate-500">Últimas 5 consultas avaliadas</p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282d37] transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* List of submissions */}
        <div className="p-3 divide-y divide-slate-100 dark:divide-[#2d3340] max-h-[460px] overflow-y-auto">
          {loading ? (
            <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
              <span className="text-sm">Carregando fila...</span>
            </div>
          ) : submissions.length === 0 ? (
            <div className="py-10 text-center text-slate-400 space-y-2">
              <FileCode className="w-8 h-8 mx-auto text-slate-300 dark:text-slate-600" />
              <div className="text-sm font-semibold">Nenhuma submissão recente</div>
              <div className="text-xs text-slate-500">
                Execute uma consulta na Arena para ver o status aqui.
              </div>
            </div>
          ) : (
            submissions.map((sub) => (
              <div
                key={sub.submissionId}
                className="p-3.5 rounded-2xl hover:bg-slate-50 dark:hover:bg-[#262b35] transition group space-y-2.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-sm text-slate-900 dark:text-slate-100 truncate">
                    #{sub.questionId}. {sub.questionTitle}
                  </span>
                  {getStatusBadge(sub)}
                </div>

                <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {formatRelativeTime(sub.createdAt)}
                  </span>

                  {sub.executionTimeMs && (
                    <span className="flex items-center gap-1 text-slate-600 dark:text-slate-400">
                      <Zap className="w-3.5 h-3.5 text-amber-500" />
                      {sub.executionTimeMs}ms
                    </span>
                  )}

                  {sub.pointsAwarded > 0 && (
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">
                      +{sub.pointsAwarded} XP
                    </span>
                  )}
                </div>

                {/* Query snippet preview */}
                <div className="bg-slate-100 dark:bg-[#17191f] rounded-xl p-2 font-mono text-xs text-slate-700 dark:text-slate-300 truncate border border-slate-200/80 dark:border-[#2d3340]">
                  {sub.query.split('\n')[0]}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer with button to open the full History Modal */}
        <div className="p-3 border-t border-slate-100 dark:border-[#2d3340] bg-slate-50/50 dark:bg-[#191c23]">
          <button
            type="button"
            onClick={() => {
              onClose();
              onOpenHistory();
            }}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-2xl bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-white text-white dark:text-slate-900 font-bold text-sm transition shadow-xs active:scale-98"
          >
            <span>Ver Histórico Completo de Submissões</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
