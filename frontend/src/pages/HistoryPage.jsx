import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  Clock,
  Zap,
  Code2,
  Copy,
  Check,
  Play,
  RotateCcw,
  Terminal,
  Filter,
  Layers,
  Sparkles,
  ExternalLink,
  ChevronRight,
  X,
} from 'lucide-react';
import { getSubmissionsHistory } from '../services/submissionService';

export default function HistoryPage({ onBack, onOpenQuestion }) {
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await getSubmissionsHistory({
        search: searchTerm,
        status: selectedStatus,
      });
      setSubmissions(data);
    } catch (err) {
      console.error('Erro ao buscar histórico:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [searchTerm, selectedStatus]);

  // Atualiza automaticamente quando houver nova submissão
  useEffect(() => {
    const handleUpdate = () => fetchHistory();
    window.addEventListener('sqlarena:submission-updated', handleUpdate);
    return () => window.removeEventListener('sqlarena:submission-updated', handleUpdate);
  }, []);

  const handleCopySql = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Cálculos de métricas
  const totalSubmissions = submissions.length;
  const successCount = submissions.filter((s) => s.outcome === 'SUCCESS').length;
  const wrongCount = submissions.filter((s) => s.outcome === 'WRONG_ANSWER').length;
  const errorCount = submissions.filter((s) => s.outcome === 'ERROR').length;
  const successRate = totalSubmissions > 0 ? Math.round((successCount / totalSubmissions) * 100) : 0;

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
    <div className="w-full px-6 lg:px-12 py-8 space-y-8 animate-in fade-in duration-200">
      {/* Top Header & Breadcrumb */}
      <div className="w-full flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 text-slate-700 dark:text-slate-200 text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar ao Mural
          </button>

          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight flex items-center gap-3">
              <span>Histórico de Submissões</span>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                {totalSubmissions} execuções
              </span>
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Registro completo de consultas avaliadas no PostgreSQL, taxas de acerto e diagnósticos de erro.
            </p>
          </div>
        </div>

        <button
          onClick={onBack}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-md shadow-indigo-600/20 transition active:scale-98"
        >
          <Play className="w-4 h-4 fill-current" />
          Praticar Novas Questões
        </button>
      </div>

      {/* KPI Summary Cards */}
      <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Total */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-md hover:shadow-lg transition">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-500">Total de Envios</span>
            <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-950/80 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 dark:text-white mt-3">
            {totalSubmissions}
          </div>
          <div className="text-xs text-slate-500 mt-1">Registradas na sandbox de execução</div>
        </div>

        {/* Sucessos */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-md hover:shadow-lg transition">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
              Consultas Aceitas
            </span>
            <div className="w-10 h-10 rounded-2xl bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2 mt-3">
            <span className="text-3xl font-extrabold text-slate-900 dark:text-white">
              {successCount}
            </span>
            <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
              ({successRate}% de acerto)
            </span>
          </div>
          <div className="text-xs text-slate-500 mt-1">Gabarito 100% verificado via hash estrito</div>
        </div>

        {/* Resposta Divergente */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-md hover:shadow-lg transition">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-amber-600 dark:text-amber-400">
              Gabarito Divergente
            </span>
            <div className="w-10 h-10 rounded-2xl bg-amber-50 dark:bg-amber-950/80 border border-amber-200 dark:border-amber-800 flex items-center justify-center text-amber-600 dark:text-amber-400">
              <AlertTriangle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 dark:text-white mt-3">
            {wrongCount}
          </div>
          <div className="text-xs text-slate-500 mt-1">Divergência de ordem, colunas ou linhas</div>
        </div>

        {/* Erro PostgreSQL */}
        <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-md hover:shadow-lg transition">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold text-rose-600 dark:text-rose-400">
              Erros de Execução
            </span>
            <div className="w-10 h-10 rounded-2xl bg-rose-50 dark:bg-rose-950/80 border border-rose-200 dark:border-rose-800 flex items-center justify-center text-rose-600 dark:text-rose-400">
              <XCircle className="w-5 h-5" />
            </div>
          </div>
          <div className="text-3xl font-extrabold text-slate-900 dark:text-white mt-3">
            {errorCount}
          </div>
          <div className="text-xs text-slate-500 mt-1">Sintaxe inválida ou colunas inexistentes</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-5 sm:p-6 shadow-md space-y-4">
        <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
          {/* Search Box */}
          <div className="relative flex-1">
            <Search className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Buscar por título da questão, ID ou trecho da consulta SQL..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-10 py-3 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 text-sm text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-600 transition"
            />
            {searchTerm && (
              <button
                type="button"
                onClick={() => setSearchTerm('')}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* Status Filter Tabs */}
          <div className="flex flex-wrap items-center gap-2">
            {[
              { id: 'ALL', label: 'Todas' },
              { id: 'SUCCESS', label: '✓ Sucesso' },
              { id: 'WRONG_ANSWER', label: '⚠ Gabarito Divergente' },
              { id: 'ERROR', label: '✕ Erro SQL' },
              { id: 'PROCESSING', label: '⏳ Na Fila' },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedStatus(tab.id)}
                className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition border ${
                  selectedStatus === tab.id
                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-transparent hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Submissions List */}
      <div className="space-y-4">
        {loading ? (
          <div className="py-20 text-center text-slate-400 flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
            <span className="text-base font-semibold">Carregando histórico de submissões...</span>
          </div>
        ) : submissions.length === 0 ? (
          <div className="py-20 text-center rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-8 space-y-3">
            <Code2 className="w-12 h-12 mx-auto text-slate-300 dark:text-slate-700" />
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">
              Nenhuma submissão encontrada
            </h3>
            <p className="text-sm text-slate-500 max-w-md mx-auto">
              Nenhuma consulta corresponde aos filtros aplicados. Tente limpar a busca ou envie novas soluções na Arena.
            </p>
          </div>
        ) : (
          submissions.map((sub) => {
            const isSuccess = sub.outcome === 'SUCCESS';
            const isWrong = sub.outcome === 'WRONG_ANSWER';
            const isError = sub.outcome === 'ERROR';
            const isProcessing = sub.status === 'PROCESSING';

            return (
              <div
                key={sub.submissionId}
                className="w-full rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-md hover:shadow-lg transition-all duration-200 space-y-4 group"
              >
                {/* Row Header */}
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    {/* Status Badge */}
                    {isProcessing && (
                      <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Processando no PostgreSQL
                      </span>
                    )}
                    {isSuccess && (
                      <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                        Aceita (100% Correto)
                      </span>
                    )}
                    {isWrong && (
                      <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                        <AlertTriangle className="w-4 h-4 text-amber-500" />
                        Gabarito Divergente
                      </span>
                    )}
                    {isError && (
                      <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
                        <XCircle className="w-4 h-4 text-rose-500" />
                        Erro de Execução SQL
                      </span>
                    )}

                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                      Questão #{sub.questionId} — {sub.questionTitle}
                    </h3>
                  </div>

                  {/* Metadata Chips */}
                  <div className="flex items-center gap-3 text-xs font-semibold text-slate-500">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {formatDate(sub.createdAt)}
                    </span>

                    {sub.executionTimeMs && (
                      <span className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        <Zap className="w-3.5 h-3.5 text-amber-500" />
                        {sub.executionTimeMs}ms
                      </span>
                    )}

                    {sub.pointsAwarded > 0 && (
                      <span className="px-2.5 py-1 rounded-lg bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 font-bold">
                        +{sub.pointsAwarded} XP
                      </span>
                    )}
                  </div>
                </div>

                {/* SQL Code Preview Block */}
                <div className="relative rounded-2xl bg-slate-950 border border-slate-800 p-4 font-mono text-sm text-indigo-300 overflow-x-auto">
                  <pre className="whitespace-pre-wrap">{sub.query}</pre>
                </div>

                {/* Error Banner Preview if any */}
                {sub.errorMessage && (
                  <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-900/60 font-mono text-xs text-rose-700 dark:text-rose-300 flex items-start gap-2.5">
                    <Terminal className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{sub.errorMessage}</span>
                  </div>
                )}

                {/* Card Actions */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setSelectedSubmission(sub)}
                    className="flex items-center gap-2 text-sm font-bold text-indigo-600 dark:text-indigo-400 hover:underline"
                  >
                    <span>Ver Diagnóstico e Detalhes da Execução</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>

                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => handleCopySql(sub.query)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold transition"
                    >
                      {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copied ? 'Copiado!' : 'Copiar SQL'}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => onOpenQuestion(sub.questionId, sub.query)}
                      className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/80 hover:bg-indigo-100 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 text-xs font-bold transition"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      <span>Abrir na Arena</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Submission Deep Inspection Modal */}
      {selectedSubmission && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/70 backdrop-blur-sm animate-in fade-in duration-150">
          <div className="w-full max-w-3xl rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-7 py-5 border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
              <div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                  Diagnóstico da Submissão
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Questão #{selectedSubmission.questionId} • {selectedSubmission.questionTitle}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setSelectedSubmission(null)}
                className="p-2 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Scrollable Body */}
            <div className="p-7 space-y-6 overflow-y-auto">
              {/* Status Banner */}
              {selectedSubmission.outcome === 'SUCCESS' && (
                <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/80 border border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-200 space-y-1">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    <span>Resultado Correto (100% Strict Mode)</span>
                  </div>
                  <p className="text-xs leading-relaxed text-emerald-800 dark:text-emerald-300">
                    O hash canônico da sua consulta coincidiu perfeitamente com o gabarito oficial no PostgreSQL. Ponto consolidado com sucesso (+10 XP).
                  </p>
                </div>
              )}

              {selectedSubmission.outcome === 'WRONG_ANSWER' && (
                <div className="p-4 rounded-2xl bg-amber-50 dark:bg-amber-950/80 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-200 space-y-1">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <AlertTriangle className="w-5 h-5 text-amber-600" />
                    <span>Gabarito Divergente</span>
                  </div>
                  <p className="text-xs leading-relaxed text-amber-800 dark:text-amber-300">
                    {selectedSubmission.errorMessage || 'Os dados retornados ou a ordenação das linhas não coincidem com o gabarito canônico.'}
                  </p>
                </div>
              )}

              {selectedSubmission.outcome === 'ERROR' && (
                <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/80 border border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-200 space-y-2">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <Terminal className="w-5 h-5 text-rose-600" />
                    <span>Diagnóstico de Erro PostgreSQL</span>
                  </div>
                  <pre className="font-mono text-xs bg-slate-950 text-rose-300 p-3 rounded-xl overflow-x-auto">
                    {selectedSubmission.errorMessage}
                  </pre>
                </div>
              )}

              {/* Submitted SQL */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-bold text-slate-800 dark:text-slate-200">
                    Consulta SQL Enviada
                  </label>
                  <button
                    type="button"
                    onClick={() => handleCopySql(selectedSubmission.query)}
                    className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    {copied ? 'Copiado!' : 'Copiar'}
                  </button>
                </div>
                <pre className="p-4 rounded-2xl bg-slate-950 border border-slate-800 text-indigo-300 font-mono text-sm leading-relaxed overflow-x-auto">
                  {selectedSubmission.query}
                </pre>
              </div>

              {/* Execution Info */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                  <div className="text-slate-500 font-medium">Tempo de Execução</div>
                  <div className="text-base font-extrabold text-slate-900 dark:text-white mt-1">
                    {selectedSubmission.executionTimeMs || 0}ms
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                  <div className="text-slate-500 font-medium">Data do Envio</div>
                  <div className="text-xs font-bold text-slate-900 dark:text-white mt-1 truncate">
                    {formatDate(selectedSubmission.createdAt)}
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                  <div className="text-slate-500 font-medium">Pontuação</div>
                  <div className="text-base font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">
                    +{selectedSubmission.pointsAwarded || 0} XP
                  </div>
                </div>

                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                  <div className="text-slate-500 font-medium">Linhas Retornadas</div>
                  <div className="text-base font-extrabold text-slate-900 dark:text-white mt-1">
                    {selectedSubmission.rows?.length || 0} linhas
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between px-7 py-4 border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
              <button
                type="button"
                onClick={() => setSelectedSubmission(null)}
                className="px-5 py-2.5 rounded-xl border border-slate-300 dark:border-slate-800 text-slate-700 dark:text-slate-300 text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800 transition"
              >
                Fechar
              </button>

              <button
                type="button"
                onClick={() => {
                  const qId = selectedSubmission.questionId;
                  const sql = selectedSubmission.query;
                  setSelectedSubmission(null);
                  onOpenQuestion(qId, sql);
                }}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-sm shadow-md transition active:scale-98"
              >
                <RotateCcw className="w-4 h-4" />
                <span>Carregar e Editar na Arena</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
