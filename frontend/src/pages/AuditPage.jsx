import React, { useState, useEffect } from 'react';
import { getCrudAuditLogs } from '../services/auditService';
import { Activity, RefreshCw, ShieldAlert, Database, Server } from 'lucide-react';

export default function AuditPage() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const data = await getCrudAuditLogs(50);
      setLogs(data);
    } catch (err) {
      console.error('Falha ao buscar logs do DynamoDB:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  return (
    <div className="max-w-7xl mx-auto p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Activity className="w-5 h-5 text-indigo-400" />
            Auditoria & Histórico de CRUD (Amazon DynamoDB)
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Tabela <code className="text-indigo-300 font-mono">sqlarena-crud-actions-log</code> com GSI EntityIndex para rastreamento imutável de ações.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Atualizar Logs
        </button>
      </div>

      {/* Logs Table Card */}
      <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Action ID</th>
                <th className="py-3 px-4">Tipo de Ação</th>
                <th className="py-3 px-4">Entidade</th>
                <th className="py-3 px-4">Usuário</th>
                <th className="py-3 px-4">Data / Hora (UTC)</th>
                <th className="py-3 px-4">Detalhes da Execução</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-[11px] text-slate-300">
              {logs.length > 0 ? (
                logs.map((log) => (
                  <tr key={log.action_id} className="hover:bg-slate-800/40">
                    <td className="py-3 px-4 text-slate-500">{log.action_id}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-block px-2 py-0.5 rounded font-sans font-bold text-[10px] ${
                          log.action_type === 'CREATE_EXERCISE'
                            ? 'bg-blue-950 text-blue-300 border border-blue-800/60'
                            : log.action_type === 'SUBMIT_ANSWER'
                            ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/60'
                            : log.action_type === 'UPLOAD_DATASET_CSV'
                            ? 'bg-purple-950 text-purple-300 border border-purple-800/60'
                            : log.action_type === 'PUBLISH_EXERCISE'
                            ? 'bg-indigo-950 text-indigo-300 border border-indigo-800/60'
                            : 'bg-slate-800 text-slate-300'
                        }`}
                      >
                        {log.action_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">{log.entity_id}</td>
                    <td className="py-3 px-4 text-slate-300 font-sans">{log.user_id}</td>
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(log.created_at).toLocaleString('pt-BR')}
                    </td>
                    <td className="py-3 px-4 font-sans text-slate-300 max-w-xs truncate" title={log.details}>
                      {log.details}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-500 font-sans">
                    Nenhum log registrado na tabela DynamoDB até o momento.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
