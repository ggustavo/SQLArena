import React from 'react';
import { CheckCircle2, XCircle, AlertTriangle, Clock, Layers, Cpu, Server, Check, ArrowRight } from 'lucide-react';

export default function ResultPanel({ pollStage, result, error, isRunning }) {
  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden flex flex-col h-full shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-slate-950 border-b border-slate-800">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Console de Execução & Resultado
        </span>

        {result?.executionTimeMs && (
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <Clock className="w-3.5 h-3.5 text-indigo-400" />
            <span>Tempo: <strong className="text-slate-200">{result.executionTimeMs}ms</strong></span>
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-4 flex-1 overflow-y-auto space-y-4">
        {/* Polling / Asynchronous Worker Pipeline Indicator */}
        {isRunning && (
          <div className="p-4 rounded-xl bg-slate-950/70 border border-indigo-900/40 space-y-3">
            <div className="flex items-center justify-between text-xs font-medium text-indigo-300">
              <span className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-ping" />
                Pipeline Assíncrono em Execução (Requisito 9)
              </span>
              <span className="text-slate-400 font-mono text-[11px]">HTTP 202 Accepted</span>
            </div>

            {/* Stepper */}
            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div
                className={`p-2 rounded-lg border transition-all ${
                  pollStage === 'SQS_QUEUE'
                    ? 'bg-amber-950/40 border-amber-500/50 text-amber-200'
                    : 'bg-slate-900 border-slate-800 text-slate-500'
                }`}
              >
                <Layers className="w-4 h-4 mx-auto mb-1 text-amber-400" />
                <div className="font-semibold text-[11px]">1. Fila SQS</div>
                <div className="text-[10px] text-slate-400">Desacoplamento</div>
              </div>

              <div
                className={`p-2 rounded-lg border transition-all ${
                  pollStage === 'POSTGRES_EXECUTION'
                    ? 'bg-indigo-950/40 border-indigo-500/50 text-indigo-200'
                    : 'bg-slate-900 border-slate-800 text-slate-500'
                }`}
              >
                <Cpu className="w-4 h-4 mx-auto mb-1 text-indigo-400" />
                <div className="font-semibold text-[11px]">2. Worker EC2</div>
                <div className="text-[10px] text-slate-400">PostgreSQL Isolado</div>
              </div>

              <div className="p-2 rounded-lg border bg-slate-900 border-slate-800 text-slate-500">
                <Server className="w-4 h-4 mx-auto mb-1 text-emerald-400" />
                <div className="font-semibold text-[11px]">3. Validação Hash</div>
                <div className="text-[10px] text-slate-400">Redis + DynamoDB</div>
              </div>
            </div>
          </div>
        )}

        {/* Global Error Banner (e.g. Rate Limit 5s) */}
        {error && (
          <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-200 flex items-start gap-3 text-xs">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold mb-0.5">Operação Bloqueada</div>
              <p className="text-rose-300/90 leading-relaxed">{error}</p>
            </div>
          </div>
        )}

        {/* Evaluation Outcome Banner */}
        {result && (
          <div>
            {result.outcome === 'SUCCESS' && (
              <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-700/50 text-emerald-200 flex items-start gap-3 text-xs">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-sm text-emerald-300">Resposta Correta! (+1 Ponto)</div>
                  <p className="text-emerald-400/90 mt-0.5">
                    O Hash SHA-256 canônico gerado pela sua consulta coincidiu 100% com o gabarito no Redis (Strict Mode).
                  </p>
                </div>
              </div>
            )}

            {result.outcome === 'WRONG_ANSWER' && (
              <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-700/50 text-amber-200 flex items-start gap-3 text-xs">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-sm text-amber-300">Resposta Incorreta (Hash Divergente)</div>
                  <p className="text-amber-300/90 mt-0.5">
                    {result.errorMessage ||
                      'As colunas, valores ou ordenação retornados não coincidem com o gabarito canônico exigido.'}
                  </p>
                </div>
              </div>
            )}

            {result.outcome === 'ERROR' && (
              <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/70 text-rose-200 flex items-start gap-3 text-xs">
                <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div className="w-full">
                  <div className="font-bold text-sm text-rose-300">Erro de Execução no PostgreSQL</div>
                  <pre className="mt-2 p-2.5 rounded bg-black/50 border border-rose-900/40 font-mono text-[11px] text-rose-300 overflow-x-auto whitespace-pre-wrap">
                    {result.errorMessage}
                  </pre>
                </div>
              </div>
            )}

            {/* Results Table */}
            {result.rows && result.rows.length > 0 && (
              <div className="mt-3">
                <div className="text-xs font-semibold text-slate-400 mb-2">Dados Retornados ({result.rows.length} linhas):</div>
                <div className="overflow-x-auto rounded-lg border border-slate-800">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-300 font-semibold border-b border-slate-800">
                      <tr>
                        {result.columns.map((col) => (
                          <th key={col} className="py-2 px-3 font-mono">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50 font-mono text-[11px] text-slate-300">
                      {result.rows.map((row, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/40">
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
        )}

        {/* Empty state when nothing has run yet */}
        {!isRunning && !result && !error && (
          <div className="flex flex-col items-center justify-center py-12 text-center text-slate-500">
            <Server className="w-8 h-8 stroke-1 mb-2 text-slate-600" />
            <p className="text-xs">Nenhuma consulta executada ainda.</p>
            <p className="text-[11px] text-slate-600 mt-1">
              Escreva o código SQL e clique em <span className="text-emerald-400">Executar Consulta</span>.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
