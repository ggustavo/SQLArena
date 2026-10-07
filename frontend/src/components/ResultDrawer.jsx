import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Clock, X } from 'lucide-react';

export default function ResultDrawer({ result, error, isRunning, onClose }) {
  if (!result && !error && !isRunning) return null;

  return (
    <div className="w-full bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-md transition-all flex flex-col h-[175px] shrink-0">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-2.5 bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 shrink-0">
        <div className="flex items-center gap-2.5">
          {isRunning ? (
            <div className="flex items-center gap-2 text-xs sm:text-sm font-semibold text-indigo-600 dark:text-indigo-400">
              <div className="w-3.5 h-3.5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <span>Executando consulta no banco de dados...</span>
            </div>
          ) : result?.outcome === 'SUCCESS' ? (
            <div className="flex items-center gap-1.5 text-xs sm:text-sm font-bold text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <span>Consulta Correta! Resultado idêntico ao gabarito oficial.</span>
            </div>
          ) : result?.outcome === 'WRONG_ANSWER' ? (
            <div className="flex items-center gap-1.5 text-xs sm:text-sm font-bold text-amber-600 dark:text-amber-400">
              <AlertTriangle className="w-4 h-4" />
              <span>Resposta Incorreta (Diverge do gabarito)</span>
            </div>
          ) : error ? (
            <div className="flex items-center gap-1.5 text-xs sm:text-sm font-bold text-rose-600 dark:text-rose-400">
              <XCircle className="w-4 h-4" />
              <span>{error.toLowerCase().includes('publicada') ? 'Questão Não Publicada' : 'Aviso de Execução'}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-xs sm:text-sm font-bold text-rose-600 dark:text-rose-400">
              <XCircle className="w-4 h-4" />
              <span>Erro de Sintaxe ou Execução SQL</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          {result?.executionTimeMs && (
            <div className="text-xs text-slate-500 font-mono flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {result.executionTimeMs}ms
            </div>
          )}

          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-3.5 flex-1 min-h-0 overflow-y-auto space-y-2.5">
        {error && (
          <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs sm:text-sm font-medium leading-relaxed flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {result?.errorMessage && (
          <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-mono whitespace-pre-wrap leading-relaxed">
            {result.errorMessage}
          </div>
        )}

        {result?.rows && result.rows.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Registros retornados ({result.rows.length}):
            </div>
            <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 font-bold bg-white dark:bg-slate-900">
                    {result.columns.map((col) => (
                      <th key={col} className="py-1.5 px-3 font-mono text-xs">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono text-xs text-slate-800 dark:text-slate-200">
                  {result.rows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-100/50 dark:hover:bg-slate-900/50">
                      {result.columns.map((col) => (
                        <td key={col} className="py-1.5 px-3">
                          {String(row[col] ?? 'NULL')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
