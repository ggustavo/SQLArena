import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  RotateCw,
  Search,
  Database,
  Cpu,
  Zap,
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Copy,
  Check,
  Code2,
  ShieldCheck,
  Layers,
  ChevronDown,
  ChevronUp,
  FileText,
} from 'lucide-react';
import { getDynamoSubmissionLogs, getDynamoCrudLogs } from '../services/auditService';

function formatDate(isoStr) {
  if (!isoStr) return 'N/A';
  try {
    const d = new Date(isoStr);
    return d.toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return isoStr;
  }
}

export default function DynamoLogsPage({ onBack }) {
  const [activeTab, setActiveTab] = useState('submissions'); // 'submissions' | 'crud'
  const [submissionsLogs, setSubmissionsLogs] = useState([]);
  const [crudLogs, setCrudLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedId, setExpandedId] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [error, setError] = useState('');

  async function loadLogs(showRefreshAnim = false) {
    if (showRefreshAnim) setIsRefreshing(true);
    else setLoading(true);
    setError('');

    try {
      const [subData, crudData] = await Promise.all([
        getDynamoSubmissionLogs(30).catch(() => []),
        getDynamoCrudLogs(30).catch(() => []),
      ]);
      setSubmissionsLogs(Array.isArray(subData) ? subData : []);
      setCrudLogs(Array.isArray(crudData) ? crudData : []);
    } catch (err) {
      setError('Não foi possível carregar os registros do Amazon DynamoDB.');
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    loadLogs();
  }, []);

  function handleCopy(text, id) {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  const filteredSubmissions = submissionsLogs.filter((item) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const subId = String(item.submission_id || '').toLowerCase();
    const sName = String(item.student_name || '').toLowerCase();
    const sId = String(item.student_id || '').toLowerCase();
    const qTitle = String(item.question_title || '').toLowerCase();
    const query = String(item.query || '').toLowerCase();
    const status = String(item.status || '').toLowerCase();
    return (
      subId.includes(term) ||
      sName.includes(term) ||
      sId.includes(term) ||
      qTitle.includes(term) ||
      query.includes(term) ||
      status.includes(term)
    );
  });

  const filteredCrud = crudLogs.filter((item) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    const actType = String(item.action_type || '').toLowerCase();
    const uName = String(item.user_name || '').toLowerCase();
    const entity = String(item.entity || '').toLowerCase();
    const entityId = String(item.entity_id || '').toLowerCase();
    return (
      actType.includes(term) ||
      uName.includes(term) ||
      entity.includes(term) ||
      entityId.includes(term)
    );
  });

  return (
    <div className="w-full max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Top bar with Back Button */}
      <div>
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 dark:bg-[#252a35] hover:bg-slate-200 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#323946] text-slate-700 dark:text-slate-200 text-xs sm:text-sm font-semibold transition cursor-pointer"
        >
          <ArrowLeft size={16} /> Voltar ao Painel
        </button>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-indigo-600 dark:bg-indigo-500 text-white flex items-center justify-center shadow-md shadow-indigo-600/20">
              <Database className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 dark:text-white">
                  Logs do Amazon DynamoDB
                </h1>
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800">
                  <ShieldCheck size={13} /> Exclusivo Administrador
                </span>
              </div>
              <p className="mt-0.5 text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                Visualização interna dos últimos 30 registros NoSQL (métricas de CPU, latência e ações de CRUD).
              </p>
            </div>
          </div>
        </div>

        {/* Refresh & Controls */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => loadLogs(true)}
            disabled={isRefreshing || loading}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl bg-slate-100 dark:bg-[#252a35] hover:bg-slate-200 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#323946] text-slate-700 dark:text-slate-200 text-xs sm:text-sm font-semibold transition cursor-pointer disabled:opacity-50"
          >
            <RotateCw size={15} className={isRefreshing ? 'animate-spin text-indigo-500' : ''} />
            <span>Atualizar Logs</span>
          </button>
        </div>
      </div>

      {/* Tabs and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-[#2d3340] pb-4">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setActiveTab('submissions')}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition cursor-pointer ${
              activeTab === 'submissions'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/25'
                : 'bg-slate-100 dark:bg-[#252a35] text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Cpu size={16} />
            <span>Submissões & Consumo de CPU</span>
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                activeTab === 'submissions'
                  ? 'bg-indigo-500 text-white'
                  : 'bg-slate-200 dark:bg-[#323846] text-slate-700 dark:text-slate-300'
              }`}
            >
              {submissionsLogs.length}
            </span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('crud')}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-bold transition cursor-pointer ${
              activeTab === 'crud'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/25'
                : 'bg-slate-100 dark:bg-[#252a35] text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Layers size={16} />
            <span>Ações de CRUD</span>
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                activeTab === 'crud'
                  ? 'bg-indigo-500 text-white'
                  : 'bg-slate-200 dark:bg-[#323846] text-slate-700 dark:text-slate-300'
              }`}
            >
              {crudLogs.length}
            </span>
          </button>
        </div>

        {/* Filter Input */}
        <div className="relative w-full sm:w-72">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            placeholder={
              activeTab === 'submissions'
                ? 'Filtrar por aluno, ID, status ou SQL...'
                : 'Filtrar por ação ou usuário...'
            }
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-2xl border border-slate-200 dark:border-[#353d4d] bg-white dark:bg-[#1f232b] text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
          />
        </div>
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="py-24 text-center text-slate-500 dark:text-slate-400 space-y-3">
          <div className="w-8 h-8 mx-auto border-3 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-medium">Consultando registros no Amazon DynamoDB...</p>
        </div>
      ) : error ? (
        <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 text-sm font-medium">
          {error}
        </div>
      ) : activeTab === 'submissions' ? (
        /* TAB 1: Submissions Logs with CPU metric */
        filteredSubmissions.length === 0 ? (
          <div className="bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#323846] rounded-3xl p-12 text-center text-slate-500 dark:text-slate-400">
            <Cpu className="w-10 h-10 mx-auto text-slate-400 mb-2 opacity-50" />
            <p className="font-semibold text-base text-slate-800 dark:text-slate-200">
              Nenhuma submissão registrada no DynamoDB
            </p>
            <p className="text-xs mt-1">
              {searchTerm ? 'Tente ajustar o termo da busca.' : 'Submeta consultas na Arena para visualizá-las aqui.'}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 flex items-center justify-between px-2">
              <span>
                Exibindo <strong>{filteredSubmissions.length}</strong> de {submissionsLogs.length} registros mais recentes (Tabela: <code className="font-mono text-indigo-600 dark:text-indigo-400">sqlarena-submissions-log</code>)
              </span>
            </div>

            <div className="space-y-3">
              {filteredSubmissions.map((item) => {
                const subId = item.submission_id || 'N/A';
                const isExpanded = expandedId === subId;
                const isSuccess = item.status === 'SUCCESS' || item.is_correct === true;
                const isWrong = item.status === 'WRONG_ANSWER';
                const cpuVal = item.cpu_percent !== undefined && item.cpu_percent !== null ? item.cpu_percent : null;
                const execMs = item.execution_time_ms !== undefined && item.execution_time_ms !== null ? item.execution_time_ms : null;

                return (
                  <div
                    key={subId}
                    className="bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#323846] rounded-2xl p-5 shadow-xs transition hover:border-slate-300 dark:hover:border-slate-600 space-y-3"
                  >
                    {/* Header Row */}
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex flex-wrap items-center gap-2.5">
                        {/* Status Badge */}
                        {isSuccess ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                            <CheckCircle2 size={13} className="text-emerald-500" />
                            SUCCESS
                          </span>
                        ) : isWrong ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-200 border border-amber-200 dark:border-amber-800">
                            <AlertTriangle size={13} className="text-amber-500" />
                            WRONG_ANSWER
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
                            <XCircle size={13} className="text-rose-500" />
                            {item.status || 'ERROR'}
                          </span>
                        )}

                        {/* Submission ID with quick copy */}
                        <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-[#282d37] font-mono text-xs font-bold text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-[#353d4d]">
                          <span>{subId}</span>
                          <button
                            type="button"
                            onClick={() => handleCopy(subId, subId)}
                            title="Copiar ID da submissão"
                            className="text-slate-400 hover:text-slate-600 dark:hover:text-white transition ml-0.5 cursor-pointer"
                          >
                            {copiedId === subId ? <Check size={12} className="text-emerald-500" /> : <Copy size={12} />}
                          </button>
                        </div>

                        {/* Student and Question Info */}
                        <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                          <span>{item.student_name || item.student_id}</span>
                          <span className="mx-1.5 text-slate-400">•</span>
                          <span className="text-slate-500 dark:text-slate-400">{item.question_title || `Questão #${item.question_id}`}</span>
                        </div>
                      </div>

                      {/* Right chips: CPU, Execution Time, Date */}
                      <div className="flex flex-wrap items-center gap-2">
                        {/* CPU Linux Metric Chip */}
                        {cpuVal !== null ? (
                          <span
                            title="Consumo de CPU Linux capturado pelo Worker"
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 font-bold text-xs"
                          >
                            <Cpu size={13} className="text-indigo-500" />
                            CPU: {cpuVal}%
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-[#252a35] text-slate-400 text-xs">
                            <Cpu size={13} />
                            CPU: N/A
                          </span>
                        )}

                        {/* Execution Time */}
                        {execMs !== null && (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-[#282d37] text-slate-700 dark:text-slate-300 text-xs font-semibold">
                            <Zap size={13} className="text-amber-500" />
                            {execMs} ms
                          </span>
                        )}

                        {/* Date */}
                        <span className="inline-flex items-center gap-1 text-slate-500 dark:text-slate-400 text-xs font-medium">
                          <Clock size={12} />
                          {formatDate(item.created_at)}
                        </span>

                        {/* Toggle Expand SQL */}
                        <button
                          type="button"
                          onClick={() => setExpandedId(isExpanded ? null : subId)}
                          className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-[#282d37] text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer"
                          title={isExpanded ? 'Recolher detalhes' : 'Ver SQL e detalhes'}
                        >
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                      </div>
                    </div>

                    {/* SQL Preview (Always visible truncated or full when expanded) */}
                    <div className="relative rounded-xl bg-slate-900 border border-slate-800 p-3 font-mono text-xs text-slate-200 overflow-x-auto">
                      <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-slate-800 text-[11px] text-slate-400">
                        <span className="flex items-center gap-1">
                          <Code2 size={12} /> Consulta SQL Executada
                        </span>
                        <button
                          type="button"
                          onClick={() => handleCopy(item.query, `${subId}-sql`)}
                          className="hover:text-white transition inline-flex items-center gap-1 cursor-pointer"
                        >
                          {copiedId === `${subId}-sql` ? (
                            <>
                              <Check size={11} className="text-emerald-400" /> Copiado
                            </>
                          ) : (
                            <>
                              <Copy size={11} /> Copiar SQL
                            </>
                          )}
                        </button>
                      </div>
                      <pre className={`whitespace-pre-wrap ${!isExpanded ? 'line-clamp-2' : ''}`}>
                        {item.query || '-- (consulta vazia)'}
                      </pre>
                    </div>

                    {/* Expanded Extra Details */}
                    {isExpanded && (
                      <div className="pt-2 border-t border-slate-100 dark:border-[#2d3340] grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div>
                          <span className="font-bold text-slate-500 dark:text-slate-400 block mb-0.5">
                            Hash SHA-256 (Gabarito):
                          </span>
                          <code className="font-mono text-[11px] text-slate-800 dark:text-slate-200 break-all select-all">
                            {item.hash_result || 'N/A'}
                          </code>
                        </div>
                        {item.pg_error && (
                          <div className="p-2 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/40 text-rose-700 dark:text-rose-300">
                            <span className="font-bold block mb-0.5">Erro PostgreSQL Nativo:</span>
                            <pre className="font-mono text-[11px] whitespace-pre-wrap">{item.pg_error}</pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )
      ) : (
        /* TAB 2: CRUD Action Logs */
        filteredCrud.length === 0 ? (
          <div className="bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#323846] rounded-3xl p-12 text-center text-slate-500 dark:text-slate-400">
            <Layers className="w-10 h-10 mx-auto text-slate-400 mb-2 opacity-50" />
            <p className="font-semibold text-base text-slate-800 dark:text-slate-200">
              Nenhuma ação de CRUD registrada no DynamoDB
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 px-2">
              Exibindo <strong>{filteredCrud.length}</strong> de {crudLogs.length} ações de CRUD mais recentes (Tabela: <code className="font-mono text-indigo-600 dark:text-indigo-400">sqlarena-crud-actions-log</code>)
            </div>

            <div className="space-y-3">
              {filteredCrud.map((action, idx) => {
                const actId = action.action_id || `crud-${idx}`;
                const isExpanded = expandedId === actId;

                return (
                  <div
                    key={actId}
                    className="bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#323846] rounded-2xl p-5 shadow-xs transition hover:border-slate-300 dark:hover:border-slate-600 space-y-3"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5">
                        <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                          {action.action_type || 'AÇÃO'}
                        </span>
                        <div className="text-xs font-bold text-slate-900 dark:text-white">
                          <span>Entidade: {action.entity || 'N/A'}</span>
                          <span className="mx-1 text-slate-400">#</span>
                          <span>{action.entity_id || 'N/A'}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
                        <span>Autor: <strong>{action.user_name || action.user_id || 'sistema'}</strong></span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock size={12} />
                          {formatDate(action.created_at || action.timestamp)}
                        </span>
                        <button
                          type="button"
                          onClick={() => setExpandedId(isExpanded ? null : actId)}
                          className="p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-[#282d37] text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition cursor-pointer"
                        >
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </button>
                      </div>
                    </div>

                    {action.changed_data && (
                      <div className="rounded-xl bg-slate-50 dark:bg-[#181a20] border border-slate-200 dark:border-[#2d3340] p-3 text-xs font-mono text-slate-800 dark:text-slate-200 overflow-x-auto">
                        <div className="text-[11px] font-bold uppercase text-slate-400 mb-1">
                          Dados Alterados / Payload da Ação:
                        </div>
                        <pre className={`whitespace-pre-wrap ${!isExpanded ? 'line-clamp-3' : ''}`}>
                          {typeof action.changed_data === 'object'
                            ? JSON.stringify(action.changed_data, null, 2)
                            : String(action.changed_data)}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )
      )}
    </div>
  );
}
