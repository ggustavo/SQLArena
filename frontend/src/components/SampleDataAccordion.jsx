import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Table } from 'lucide-react';

export default function SampleDataAccordion({ sampleTables = [] }) {
  const [expandedTables, setExpandedTables] = useState(() => {
    if (sampleTables.length > 0) {
      return { [sampleTables[0].name]: true };
    }
    return {};
  });

  const toggleTable = (tableName) => {
    setExpandedTables((prev) => ({
      ...prev,
      [tableName]: !prev[tableName],
    }));
  };

  const expandAll = () => {
    const all = {};
    sampleTables.forEach((t) => {
      all[t.name] = true;
    });
    setExpandedTables(all);
  };

  const collapseAll = () => {
    setExpandedTables({});
  };

  if (!sampleTables || sampleTables.length === 0) {
    return (
      <div className="p-8 text-center text-sm text-slate-500 bg-slate-50 dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800">
        Nenhum registro de exemplo cadastrado para esta questão.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="flex items-center justify-between text-sm text-slate-600 dark:text-slate-400 px-1 font-medium">
        <span>Tabelas de amostra (abra quantas quiser simultaneamente):</span>
        <div className="flex items-center gap-2 text-xs font-semibold">
          <button
            onClick={expandAll}
            className="text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            Abrir todas
          </button>
          <span>•</span>
          <button
            onClick={collapseAll}
            className="text-slate-500 hover:underline"
          >
            Fechar todas
          </button>
        </div>
      </div>

      {/* Accordions List */}
      <div className="space-y-3">
        {sampleTables.map((table) => {
          const isOpen = Boolean(expandedTables[table.name]);

          return (
            <div
              key={table.name}
              className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 overflow-hidden shadow-sm transition-all"
            >
              {/* Accordion Header */}
              <button
                type="button"
                onClick={() => toggleTable(table.name)}
                className="w-full flex items-center justify-between px-5 py-3.5 bg-slate-50 dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-900 text-left transition select-none"
              >
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-950/80 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                    <Table className="w-4 h-4" />
                  </div>
                  <span className="font-mono font-bold text-sm text-slate-900 dark:text-slate-100">
                    {table.name}
                  </span>
                  <span className="text-xs text-slate-500 font-medium">
                    ({table.rows?.length || 0} registros de exemplo)
                  </span>
                </div>

                <div className="text-slate-500">
                  {isOpen ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                </div>
              </button>

              {/* Accordion Content Table */}
              {isOpen && (
                <div className="border-t border-slate-200 dark:border-slate-800 p-4 bg-white dark:bg-slate-900 overflow-x-auto">
                  <table className="w-full text-left text-sm border-collapse">
                    <thead>
                      <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 font-semibold bg-slate-50 dark:bg-slate-950/50">
                        {table.columns.map((col) => (
                          <th key={col} className="py-2.5 px-3.5 font-mono text-xs sm:text-sm">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800 font-mono text-xs sm:text-sm text-slate-800 dark:text-slate-200">
                      {table.rows.map((row, rIdx) => (
                        <tr key={rIdx} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                          {table.columns.map((col) => (
                            <td key={col} className="py-2 px-3.5">
                              {String(row[col] ?? 'NULL')}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
