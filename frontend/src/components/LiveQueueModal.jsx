import React, { useState, useEffect } from 'react';
import {
  X,
  Layers,
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RefreshCw,
  GraduationCap,
  Calendar,
  Clock,
  Sparkles,
} from 'lucide-react';
import { getLiveQueue } from '../services/submissionService';
import UserAvatar from './UserAvatar';

export default function LiveQueueModal({ isOpen, onClose }) {
  const [queueData, setQueueData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastPolled, setLastPolled] = useState(null);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;

    async function fetchQueue() {
      try {
        const data = await getLiveQueue();
        if (isMounted) {
          setQueueData(data);
          setLastPolled(new Date());
          setLoading(false);
        }
      } catch (err) {
        console.error('Falha ao atualizar fila ao vivo:', err);
        if (isMounted) setLoading(false);
      }
    }

    // Carrega imediatamente ao abrir
    fetchQueue();

    // Polling a cada 1 segundo (1000ms)
    const interval = setInterval(fetchQueue, 1000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const stats = queueData?.queueStats || {
    approximateMessages: 0,
    inFlightMessages: 0,
    totalQueue: 0,
  };

  const items = queueData?.liveItems || [];

  const getDifficultyBadge = (diff) => {
    switch (diff?.toLowerCase()) {
      case 'fácil':
      case 'facil':
        return 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800';
      case 'difícil':
      case 'dificil':
        return 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-200 dark:border-rose-800';
      default:
        return 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800';
    }
  };

  const getStatusBadge = (status, outcome) => {
    if (status === 'Avaliando' || outcome === 'Avaliando' || status === 'PROCESSING' || status === 'QUEUED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800 animate-pulse">
          <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-600 dark:text-amber-400" />
          Avaliando
        </span>
      );
    }
    if (outcome === 'SUCCESS') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          Aprovado (+10 XP)
        </span>
      );
    }
    if (outcome === 'WRONG_ANSWER') {
      return (
        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
          <XCircle className="w-3.5 h-3.5 text-rose-500" />
          Resposta Divergente
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
        <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
        Erro SQL
      </span>
    );
  };

  // Formata data e hora completa: dd/mm/aaaa às HH:mm:ss
  const formatDateTime = (isoString) => {
    if (!isoString) return '--/--/---- --:--:--';
    try {
      const d = new Date(isoString);
      if (isNaN(d.getTime())) return isoString;
      const datePart = d.toLocaleDateString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      });
      const timePart = d.toLocaleTimeString('pt-BR', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
      return `${datePart} às ${timePart}`;
    } catch {
      return isoString;
    }
  };

  const formatRelativeTime = (isoString) => {
    if (!isoString) return '';
    const diffSeconds = Math.max(0, Math.floor((Date.now() - new Date(isoString).getTime()) / 1000));
    if (diffSeconds < 5) return 'há instantes';
    if (diffSeconds < 60) return `há ${diffSeconds}s`;
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `há ${diffMinutes}m`;
    const diffHours = Math.floor(diffMinutes / 60);
    return `há ${diffHours}h`;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-4xl max-h-[90vh] bg-white dark:bg-[#1b1e26] border border-slate-200 dark:border-[#2d3340] rounded-3xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-200 dark:border-[#2d3340] flex items-center justify-between bg-slate-50/70 dark:bg-[#212530]/70">
          <div className="flex items-center gap-3.5">
            <div className="relative flex items-center justify-center w-10 h-10 rounded-2xl bg-indigo-600 text-white shadow-md">
              <Activity className="w-5 h-5" />
              {/* Live Beacon Pulse */}
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="text-xl font-black text-slate-900 dark:text-white tracking-tight">
                  Fila de Submissões ao Vivo
                </h2>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  AO VIVO (1s)
                </span>
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-[#2d3340] transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Card de Destaque: Mensagens na Fila SQS */}
        <div className="p-6 pb-2">
          <div className="p-4 rounded-2xl bg-gradient-to-r from-amber-500/10 via-amber-500/5 to-transparent border border-amber-500/20 dark:border-amber-500/30 flex items-center justify-between">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400 flex items-center gap-2">
                <Layers className="w-4 h-4" />
                Mensagens na Fila SQS
              </div>
              <div className="text-4xl font-black text-slate-900 dark:text-white mt-1">
                {stats.approximateMessages}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 font-medium">
                {stats.approximateMessages === 0
                  ? 'Fila vazia (nenhuma mensagem aguardando no SQS)'
                  : `${stats.approximateMessages} mensagem(ns) aguardando processamento no Worker`}
              </div>
            </div>
            <div className="p-3.5 rounded-2xl bg-amber-500/20 text-amber-600 dark:text-amber-400">
              <Layers className="w-8 h-8" />
            </div>
          </div>
        </div>

        {/* Feed: Últimas 20 submissões no Fluxo */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-2.5">
          <div className="flex items-center justify-between text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider pb-1">
            <span>Últimas 20 submissões no Fluxo</span>
            <span className="text-[11px] font-normal lowercase flex items-center gap-1 text-slate-400">
              <RefreshCw className="w-3 h-3 animate-spin text-indigo-500" />
              atualizado {lastPolled ? lastPolled.toLocaleTimeString() : 'agora'}
            </span>
          </div>

          {loading && items.length === 0 ? (
            <div className="py-12 text-center text-slate-400 flex flex-col items-center justify-center gap-3">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
              <p className="text-sm font-semibold">Conectando ao canal SQS ao vivo...</p>
            </div>
          ) : items.length === 0 ? (
            <div className="py-12 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
              <Sparkles className="w-8 h-8 text-amber-500" />
              <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                Nenhuma submissão registrada recentemente.
              </p>
              <p className="text-xs text-slate-500">
                Envie uma consulta SQL no editor para acompanhar o processamento em tempo real aqui!
              </p>
            </div>
          ) : (
            items.map((sub, idx) => (
              <div
                key={sub.submissionId || idx}
                className="group flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-2xl bg-slate-50 dark:bg-[#222631] border border-slate-200 dark:border-[#303644] hover:border-indigo-400 dark:hover:border-indigo-500/50 transition-all duration-150"
              >
                {/* Aluno & Questão */}
                <div className="flex items-start gap-3 min-w-0 flex-1">
                  <UserAvatar
                    avatarUrl={sub.studentAvatar}
                    name={sub.studentName}
                    className="w-9 h-9 rounded-xl border border-slate-200 dark:border-[#353d4d]"
                    textClassName="text-sm font-bold"
                    fallbackBg="bg-indigo-600 text-white"
                  />

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold text-sm text-slate-900 dark:text-white truncate">
                        {sub.studentName}
                      </span>
                      {sub.studentUniversity && (
                        <span className="inline-flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400 truncate">
                          <GraduationCap className="w-3 h-3 text-indigo-400 shrink-0" />
                          {sub.studentUniversity}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span className="text-xs font-semibold text-slate-700 dark:text-slate-200 truncate">
                        {sub.questionTitle}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${getDifficultyBadge(
                          sub.difficulty
                        )}`}
                      >
                        {sub.difficulty || 'Médio'}
                      </span>
                    </div>

                    {/* Data e Hora de Envio da Mensagem */}
                    <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="w-3 h-3 text-slate-400" />
                        {formatDateTime(sub.createdAt)}
                      </span>
                      {sub.createdAt && (
                        <span className="text-slate-400 font-normal">
                          ({formatRelativeTime(sub.createdAt)})
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Status & Tempo de Execução */}
                <div className="flex items-center gap-3 justify-between sm:justify-end shrink-0 border-t sm:border-t-0 pt-2 sm:pt-0 border-slate-200 dark:border-[#2d3340]">
                  {getStatusBadge(sub.status, sub.outcome)}

                  {sub.executionTimeMs != null && (
                    <div className="text-right">
                      <div className="text-[11px] font-mono font-semibold text-slate-600 dark:text-slate-300">
                        {sub.executionTimeMs.toFixed(1)} ms
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
