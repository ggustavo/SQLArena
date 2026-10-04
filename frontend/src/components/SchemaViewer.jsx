import React, { useState } from 'react';
import { Table, Columns, Eye, ChevronDown, ChevronRight, FileText } from 'lucide-react';

export default function SchemaViewer({ tables = [], expectedColumns = [] }) {
  const [activeTableIndex, setActiveTableIndex] = useState(0);
  const [showSampleData, setShowSampleData] = useState(false);

  if (!tables || tables.length === 0) {
    return (
      <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800 text-xs text-slate-500">
        Nenhum esquema relacional associado a esta questão.
      </div>
    );
  }

  const currentTable = tables[activeTableIndex] || tables[0];

  return (
    <div className="bg-slate-900 rounded-xl border border-slate-800 overflow-hidden">
      {/* Table Selector Tabs */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-950/80 border-b border-slate-800">
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {tables.map((t, idx) => (
            <button
              key={t.name}
              onClick={() => setActiveTableIndex(idx)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                activeTableIndex === idx
                  ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/50'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Table className="w-3.5 h-3.5" />
              <span>{t.name}</span>
            </button>
          ))}
        </div>

        <button
          onClick={() => setShowSampleData(!showSampleData)}
          className="flex items-center gap-1 text-[11px] font-medium px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 transition"
        >
          <Eye className="w-3 h-3" />
          {showSampleData ? 'Ver Estrutura' : 'Ver Dados Exemplo'}
        </button>
      </div>

      {/* Content */}
      <div className="p-3">
        {!showSampleData ? (
          // Columns View
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                  <th className="py-2 px-2.5">Coluna</th>
                  <th className="py-2 px-2.5">Tipo de Dado</th>
                  <th className="py-2 px-2.5">Descrição</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {currentTable.columns.map((col) => (
                  <tr key={col.name} className="hover:bg-slate-800/30">
                    <td className="py-2 px-2.5 font-mono text-indigo-300 font-medium">{col.name}</td>
                    <td className="py-2 px-2.5 font-mono text-amber-300/80 text-[11px]">{col.type}</td>
                    <td className="py-2 px-2.5 text-slate-400">{col.description || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          // Sample Data View
          <div className="overflow-x-auto">
            {currentTable.sampleRows && currentTable.sampleRows.length > 0 ? (
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-semibold bg-slate-950/40">
                    {currentTable.columns.map((col) => (
                      <th key={col.name} className="py-2 px-2.5 font-mono">
                        {col.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {currentTable.sampleRows.map((row, rIdx) => (
                    <tr key={rIdx} className="hover:bg-slate-800/30 font-mono text-[11px] text-slate-300">
                      {currentTable.columns.map((col) => (
                        <td key={col.name} className="py-1.5 px-2.5">
                          {String(row[col.name] ?? 'NULL')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-xs text-slate-500 py-3 text-center">Nenhum dado de exemplo disponível.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
