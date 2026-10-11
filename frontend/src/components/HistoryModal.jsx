import React, { useState, useEffect } from 'react';
import {
  X,
  RotateCw,
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  Clock,
  Zap,
  Copy,
  Check,
  RotateCcw,
  Terminal,
  Layers,
  ChevronDown,
  ChevronUp,
  Filter,
} from 'lucide-react';
import { getSubmissionsHistory } from '../services/submissionService';

export default function HistoryModal({
  isOpen,
  onClose,
  onLoadSqlIntoEditor,
  currentQuestionId,
}) {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [onlyCurrentQuestion, setOnlyCurrentQuestion] = useState(false);
  const [expandedSubmissionId, setExpandedSubmissionId] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const fetchHistory = async (showRefreshSpin = false) => {
    try {
      if (showRefreshSpin) setIsRefreshing(true);
      else setLoading(true);

      const data = await getSubmissionsHistory({
        search: searchTerm,
        status: selectedStatus,
      });
      setSubmissions(data);
    } catch (err) {
      console.error('Erro ao buscar histórico:', err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    }
  }, [isOpen, searchTerm, selectedStatus]);

  // Fecha no ESC
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleCopySql = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const filteredSubmissions = submissions.filter((sub) => {
    if (onlyCurrentQuestion && currentQuestionId) {
      return Number(sub.questionId) === Number(currentQuestionId);
    }
    return true;
  });

  // Métricas
  const totalCount = filteredSubmissions.length;
  const successCount = filteredSubmissions.filter((s) => s.outcome === 'SUCCESS').length;
  const wrongCount = filteredSubmissions.filter((s) => s.outcome === 'WRONG_ANSWER').length;
  const errorCount = filteredSubmissions.filter((s) => s.outcome === 'ERROR').length;
  const successRate = totalCount > 0 ? Math.round((successCount / totalCount) * 100) : 0;

  const formatDate = (isoString) => {
    if (!isoString) return '-';
    const date = new Date(isoString);
    return date.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 lg:p-8 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      {/* Backdrop click to close */}
      <div className="fixed inset-0 -z-10" onClick={onClose} />

      {/* Modal Box */}
      <div className="w-full max-w-5xl h-[90vh] flex flex-col rounded-3xl bg-white dark:bg-[#1e222a] border border-slate-200 dark:border-[#323846] shadow-2xl overflow-hidden transition-colors">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-[#2d3340] bg-slate-50/80 dark:bg-[#191c23]/90">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-slate-200 dark:bg-[#282d37] border border-slate-300 dark:border-[#3a4150] flex items-center justify-center text-slate-800 dark:text-slate-200">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                  Histórico de Submissões
                </h2>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 dark:bg-[#272d37] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-[#333a47]">
                  {totalCount} registro(s)
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Consulte execuções anteriores, diagnósticos do PostgreSQL e recupere consultas para o editor.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Botão de Atualizar */}
            <button
              type="button"
              onClick={() => fetchHistory(true)}
              disabled={isRefreshing}
              title="Recarregar histórico"
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-[#282e39] dark:hover:bg-[#323946] border border-slate-300/80 dark:border-[#3a4150] text-slate-700 dark:text-slate-200 text-xs font-semibold transition"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Atualizar</span>
            </button>

            {/* Fechar */}
            <button
              type="button"
              onClick={onClose}
              title="Fechar (Esc)"
              className="p-2 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282e39] transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Sub-Header: Mini KPIs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 border-b border-slate-200 dark:border-[#2d3340] bg-slate-50/50 dark:bg-[#1a1d24]">
          <div className="p-3 rounded-2xl bg-white dark:bg-[#232732] border border-slate-200 dark:border-[#303644] text-center">
            <span className="text-xs text-slate-500 font-medium">Total de Envios</span>
            <div className="text-xl font-extrabold text-slate-900 dark:text-slate-100 mt-0.5">
              {totalCount}
            </div>
          </div>

          <div className="p-3 rounded-2xl bg-white dark:bg-[#232732] border border-slate-200 dark:border-[#303644] text-center">
            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium flex items-center justify-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Aceitas
            </span>
            <div className="text-xl font-extrabold text-slate-900 dark:text-slate-100 mt-0.5">
              {successCount} <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">({successRate}%)</span>
            </div>
          </div>

          <div className="p-3 rounded-2xl bg-white dark:bg-[#232732] border border-slate-200 dark:border-[#303644] text-center">
            <span className="text-xs text-amber-600 dark:text-amber-400 font-medium flex items-center justify-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              Divergentes
            </span>
            <div className="text-xl font-extrabold text-slate-900 dark:text-slate-100 mt-0.5">
              {wrongCount}
            </div>
          </div>

          <div className="p-3 rounded-2xl bg-white dark:bg-[#232732] border border-slate-200 dark:border-[#303644] text-center">
            <span className="text-xs text-rose-600 dark:text-rose-400 font-medium flex items-center justify-center gap-1">
              <XCircle className="w-3.5 h-3.5" />
              Erros SQL
            </span>
            <div className="text-xl font-extrabold text-slate-900 dark:text-slate-100 mt-0.5">
              {errorCount}
            </div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="p-4 border-b border-slate-200 dark:border-[#2d3340] flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar por questão, erro ou trecho SQL..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-100 dark:bg-[#262b35] border border-slate-300 dark:border-[#343b48] text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-slate-500 transition"
            />
          </div>

          {/* Quick Filter: Question only (if in Arena) */}
          {currentQuestionId && (
            <button
              type="button"
              onClick={() => setOnlyCurrentQuestion(!onlyCurrentQuestion)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold border transition ${
                onlyCurrentQuestion
                  ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 border-slate-900 dark:border-slate-100'
                  : 'bg-slate-100 dark:bg-[#262b35] text-slate-700 dark:text-slate-300 border-slate-300 dark:border-[#343b48]'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>Apenas Questão #{currentQuestionId}</span>
            </button>
          )}

          {/* Status Tabs */}
          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: 'ALL', label: 'Todas' },
              { id: 'SUCCESS', label: 'Sucesso' },
              { id: 'WRONG_ANSWER', label: 'Divergente' },
              { id: 'ERROR', label: 'Erro' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedStatus(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition border ${
                  selectedStatus === tab.id
                    ? 'bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 border-slate-800 dark:border-slate-200'
                    : 'bg-transparent text-slate-600 dark:text-slate-400 border-transparent hover:bg-slate-100 dark:hover:bg-[#272d37]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Scrollable Submissions List */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {loading ? (
            <div className="py-20 text-center text-slate-400 flex flex-col items-center gap-2">
              <Loader2 className="w-7 h-7 animate-spin text-slate-500" />
              <span className="text-sm font-semibold">Carregando histórico...</span>
            </div>
          ) : filteredSubmissions.length === 0 ? (
            <div className="py-16 text-center text-slate-400 space-y-2">
              <p className="text-base font-semibold text-slate-700 dark:text-slate-300">
                Nenhuma submissão encontrada
              </p>
              <p className="text-xs text-slate-500">
                Ajuste os filtros ou execute uma consulta na Arena.
              </p>
            </div>
          ) : (
            filteredSubmissions.map((sub) => {
              const isSuccess = sub.outcome === 'SUCCESS';
              const isWrong = sub.outcome === 'WRONG_ANSWER';
              const isError = sub.outcome === 'ERROR';
              const isExpanded = expandedSubmissionId === sub.submissionId;

              return (
                <div
                  key={sub.submissionId}
                  className="rounded-2xl bg-white dark:bg-[#232732] border border-slate-200 dark:border-[#323846] p-4 sm:p-5 shadow-xs hover:border-slate-400 dark:hover:border-slate-600 transition space-y-3"
                >
                  {/* Top Bar of Card */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      {/* Status Badge */}
                      {isSuccess && (
                        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                          Aceita
                        </span>
                      )}
                      {isWrong && (
                        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                          Gabarito Divergente
                        </span>
                      )}
                      {isError && (
                        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
                          <XCircle className="w-3.5 h-3.5 text-rose-500" />
                          Erro PostgreSQL
                        </span>
                      )}

                      <h4 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100">
                        Questão #{sub.questionId} — {sub.questionTitle}
                      </h4>
                    </div>

                    <div className="flex items-center gap-2.5 text-xs text-slate-500 font-medium">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        {formatDate(sub.createdAt)}
                      </span>
                      {sub.executionTimeMs && (
                        <span className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 dark:bg-[#1a1d24] text-slate-600 dark:text-slate-400">
                          <Zap className="w-3 h-3 text-amber-500" />
                          {sub.executionTimeMs}ms
                        </span>
                      )}
                    </div>
                  </div>

                  {/* SQL Code Preview */}
                  <div className="rounded-xl bg-slate-900 dark:bg-[#17191f] border border-slate-800 p-3 font-mono text-xs text-slate-200 overflow-x-auto">
                    <pre className="whitespace-pre-wrap">{sub.query}</pre>
                  </div>

                  {/* Error Snippet Preview */}
                  {sub.errorMessage && !isExpanded && (
                    <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/40 font-mono text-xs text-rose-700 dark:text-rose-300 truncate">
                      {sub.errorMessage}
                    </div>
                  )}

                  {/* Expanded Diagnostics Drawer */}
                  {isExpanded && (
                    <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#1a1d24] border border-slate-200 dark:border-[#323846] space-y-3">
                      <div className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
                        Diagnóstico Detalhado da Execução
                      </div>

                      {isSuccess && (
                        <div className="text-xs text-emerald-700 dark:text-emerald-300 flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                          <span>Strict Mode Hash validado com 100% de precisão no PostgreSQL. Pontuação consolidada (+10 XP).</span>
                        </div>
                      )}

                      {isWrong && (
                        <div className="text-xs text-amber-700 dark:text-amber-300 flex items-start gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                          <span>{sub.errorMessage || 'O hash do resultado diferiu do gabarito oficial.'}</span>
                        </div>
                      )}

                      {isError && (
                        <div className="space-y-1.5">
                          <div className="text-xs text-rose-600 font-semibold flex items-center gap-1.5">
                            <Terminal className="w-4 h-4" />
                            <span>Mensagem nativa do PostgreSQL:</span>
                          </div>
                          <pre className="p-3 rounded-lg bg-slate-950 text-rose-300 font-mono text-xs overflow-x-auto whitespace-pre-wrap border border-slate-800">
                            {sub.errorMessage}
                          </pre>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Card Bottom Actions */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-[#2d3340]">
                    <button
                      type="button"
                      onClick={() => setExpandedSubmissionId(isExpanded ? null : sub.submissionId)}
                      className="text-xs font-bold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white flex items-center gap-1 transition"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="w-3.5 h-3.5" />
                          <span>Recolher Diagnóstico</span>
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-3.5 h-3.5" />
                          <span>Ver Diagnóstico Completo</span>
                        </>
                      )}
                    </button>

                    <div className="flex items-center gap-2">
                      {/* Copiar SQL */}
                      <button
                        type="button"
                        onClick={() => handleCopySql(sub.submissionId, sub.query)}
                        className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-[#282d37] hover:bg-slate-200 dark:hover:bg-[#343b48] text-slate-700 dark:text-slate-200 text-xs font-semibold transition"
                      >
                        {copiedId === sub.submissionId ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-500" />
                            <span>Copiado!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copiar SQL</span>
                          </>
                        )}
                      </button>

                      {/* Carregar no Editor */}
                      <button
                        type="button"
                        onClick={() => {
                          onLoadSqlIntoEditor(sub.questionId, sub.query);
                          onClose();
                        }}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-slate-900 dark:bg-slate-100 hover:bg-slate-800 dark:hover:bg-white text-white dark:text-slate-900 text-xs font-bold transition shadow-xs active:scale-98"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Carregar no Editor</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200 dark:border-[#2d3340] bg-slate-50 dark:bg-[#191c23] flex items-center justify-between">
          <span className="text-xs text-slate-500">
            Dica: Carregar uma consulta no editor mantém seu ambiente aberto sem recarregar a página.
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-200 dark:bg-[#282d37] hover:bg-slate-300 dark:hover:bg-[#333947] text-slate-800 dark:text-slate-200 text-xs font-bold transition"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
}
