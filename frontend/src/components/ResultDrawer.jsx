import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Clock, X } from 'lucide-react';

export default function ResultDrawer({ result, error, isRunning, onClose }) {
  if (!result && !error && !isRunning) return null;

  return (
    <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-xl transition-all">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-3">
          {isRunning ? (
            <div className="flex items-center gap-2.5 text-sm font-semibold text-indigo-600 dark:text-indigo-400">
              <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <span>Executando consulta no banco de dados...</span>
            </div>
          ) : result?.outcome === 'SUCCESS' ? (
            <div className="flex items-center gap-2 text-sm font-bold text-emerald-600 dark:text-emerald-400">
              <CheckCircle2 className="w-5 h-5" />
              <span>Consulta Correta! Resultado idêntico ao gabarito oficial.</span>
            </div>
          ) : result?.outcome === 'WRONG_ANSWER' ? (
            <div className="flex items-center gap-2 text-sm font-bold text-amber-600 dark:text-amber-400">
              <AlertTriangle className="w-5 h-5" />
              <span>Resposta Incorreta (Resultado diverge do gabarito)</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm font-bold text-rose-600 dark:text-rose-400">
              <XCircle className="w-5 h-5" />
              <span>Erro de Sintaxe ou Execução SQL</span>
            </div>
          )}
        </div>

        <div className="flex items-center gap-4">
          {result?.executionTimeMs && (
            <div className="text-xs text-slate-500 font-mono flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              {result.executionTimeMs}ms
            </div>
          )}

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 max-h-[350px] overflow-y-auto space-y-4">
        {error && (
          <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm font-mono leading-relaxed">
            {error}
          </div>
        )}

        {result?.errorMessage && (
          <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm font-mono whitespace-pre-wrap leading-relaxed">
            {result.errorMessage}
          </div>
        )}

        {result?.rows && result.rows.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              Registros retornados pela sua consulta ({result.rows.length}):
            </div>
            <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950">
              <table className="w-full text-left text-sm border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 font-bold bg-white dark:bg-slate-900">
                    {result.columns.map((col) => (
                      <th key={col} className="py-2.5 px-4 font-mono text-xs sm:text-sm">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono text-xs sm:text-sm text-slate-800 dark:text-slate-200">
                  {result.rows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-100/50 dark:hover:bg-slate-900/50">
                      {result.columns.map((col) => (
                        <td key={col} className="py-2 px-4">
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
