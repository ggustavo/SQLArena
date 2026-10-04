import React, { useState, useMemo, useRef } from 'react';
import { ZoomIn, ZoomOut, Maximize2, Move, Database } from 'lucide-react';

export function parseSqlSchema(sqlText = '') {
  if (!sqlText) return { tables: [], relations: [] };

  const tables = [];
  const relations = [];

  const tableRegex = /CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-zA-Z0-9_]+)\s*\(([\s\S]*?)\);/gi;
  let match;

  while ((match = tableRegex.exec(sqlText)) !== null) {
    const tableName = match[1].toLowerCase();
    const body = match[2];

    const lines = body.split(',\n').map(l => l.trim()).filter(Boolean);
    const columns = [];

    lines.forEach((line) => {
      if (/^(CONSTRAINT|PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE)/i.test(line)) {
        const fkMatch = line.match(/FOREIGN\s+KEY\s*\(([a-zA-Z0-9_]+)\)\s*REFERENCES\s+([a-zA-Z0-9_]+)\s*\(([a-zA-Z0-9_]+)\)/i);
        if (fkMatch) {
          relations.push({
            fromTable: tableName,
            fromCol: fkMatch[1].toLowerCase(),
            toTable: fkMatch[2].toLowerCase(),
            toCol: fkMatch[3].toLowerCase(),
          });
        }
        return;
      }

      const parts = line.split(/\s+/);
      if (parts.length >= 2) {
        const colName = parts[0].replace(/["`]/g, '').toLowerCase();
        const colType = parts[1].toUpperCase();

        const isPk = /PRIMARY\s+KEY/i.test(line) || colName === 'id';
        const isFk = /REFERENCES/i.test(line);

        const refMatch = line.match(/REFERENCES\s+([a-zA-Z0-9_]+)\s*(?:\(([a-zA-Z0-9_]+)\))?/i);
        if (refMatch) {
          relations.push({
            fromTable: tableName,
            fromCol: colName,
            toTable: refMatch[1].toLowerCase(),
            toCol: (refMatch[2] || 'id').toLowerCase(),
          });
        }

        columns.push({
          name: colName,
          type: colType,
          isPk,
          isFk: Boolean(refMatch) || isFk,
        });
      }
    });

    tables.push({
      name: tableName,
      columns,
    });
  }

  return { tables, relations };
}

export default function RelationalDiagram({ schemaSql }) {
  const { tables, relations } = useMemo(() => parseSqlSchema(schemaSql), [schemaSql]);

  const [positions, setPositions] = useState(() => {
    const initial = {};
    tables.forEach((t, i) => {
      initial[t.name] = {
        x: 30 + (i % 2) * 320,
        y: 30 + Math.floor(i / 2) * 260,
      };
    });
    return initial;
  });

  const [scale, setScale] = useState(1);
  const [draggingTable, setDraggingTable] = useState(null);
  const dragStartRef = useRef({ mouseX: 0, mouseY: 0, tableX: 0, tableY: 0 });
  const [selectedTable, setSelectedTable] = useState(null);

  const handleMouseDown = (e, tableName) => {
    e.stopPropagation();
    setDraggingTable(tableName);
    setSelectedTable(tableName);
    dragStartRef.current = {
      mouseX: e.clientX,
      mouseY: e.clientY,
      tableX: positions[tableName]?.x || 0,
      tableY: positions[tableName]?.y || 0,
    };
  };

  const handleMouseMove = (e) => {
    if (!draggingTable) return;
    const deltaX = (e.clientX - dragStartRef.current.mouseX) / scale;
    const deltaY = (e.clientY - dragStartRef.current.mouseY) / scale;

    setPositions((prev) => ({
      ...prev,
      [draggingTable]: {
        x: Math.max(10, dragStartRef.current.tableX + deltaX),
        y: Math.max(10, dragStartRef.current.tableY + deltaY),
      },
    }));
  };

  const handleMouseUp = () => {
    setDraggingTable(null);
  };

  const handleResetZoom = () => {
    setScale(1);
    const initial = {};
    tables.forEach((t, i) => {
      initial[t.name] = {
        x: 30 + (i % 2) * 320,
        y: 30 + Math.floor(i / 2) * 260,
      };
    });
    setPositions(initial);
  };

  if (tables.length === 0) {
    return (
      <div className="p-8 text-center text-sm text-slate-500 bg-slate-50 dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800">
        Nenhum esquema relacional detectado no script SQL.
      </div>
    );
  }

  return (
    <div
      className="relative w-full h-[520px] bg-slate-50 dark:bg-slate-950 rounded-3xl border border-slate-200 dark:border-slate-800 overflow-hidden select-none shadow-inner"
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    >
      {/* Subtle Dot Grid */}
      <div
        className="absolute inset-0 opacity-20 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(circle, #6366f1 1.5px, transparent 1.5px)',
          backgroundSize: '24px 24px',
        }}
      />

      {/* Control Overlay Bar */}
      <div className="absolute top-4 right-4 z-20 flex items-center gap-2 bg-white/90 dark:bg-slate-900/90 backdrop-blur border border-slate-200 dark:border-slate-800 p-2 rounded-2xl shadow-md">
        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 px-2 flex items-center gap-1.5">
          <Move className="w-4 h-4 text-indigo-600" /> Arraste para mover
        </span>
        <div className="h-4 w-px bg-slate-300 dark:bg-slate-700 mx-1" />
        <button
          onClick={() => setScale((s) => Math.min(1.5, s + 0.15))}
          title="Aumentar zoom"
          className="p-1.5 rounded-lg text-slate-700 dark:text-slate-300 hover:text-indigo-600 transition"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
        <button
          onClick={() => setScale((s) => Math.max(0.6, s - 0.15))}
          title="Diminuir zoom"
          className="p-1.5 rounded-lg text-slate-700 dark:text-slate-300 hover:text-indigo-600 transition"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <button
          onClick={handleResetZoom}
          title="Redefinir visualização"
          className="p-1.5 rounded-lg text-slate-700 dark:text-slate-300 hover:text-indigo-600 transition"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      {/* Canvas Area */}
      <div
        className="w-full h-full relative transform-gpu origin-top-left transition-transform duration-75"
        style={{ transform: `scale(${scale})` }}
      >
        {/* SVG Connector Lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
          <defs>
            <marker
              id="arrowhead-clean"
              markerWidth="9"
              markerHeight="7"
              refX="8"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 9 3.5, 0 7" fill="#6366f1" />
            </marker>
          </defs>
          {relations.map((rel, idx) => {
            const fromPos = positions[rel.fromTable];
            const toPos = positions[rel.toTable];
            if (!fromPos || !toPos) return null;

            const x1 = fromPos.x + 130;
            const y1 = fromPos.y + 60;
            const x2 = toPos.x + 130;
            const y2 = toPos.y + 60;
            const dx = (x2 - x1) * 0.5;

            return (
              <g key={idx}>
                <path
                  d={`M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`}
                  fill="none"
                  stroke="#6366f1"
                  strokeWidth="2.5"
                  strokeDasharray="5 3"
                  markerEnd="url(#arrowhead-clean)"
                  opacity="0.85"
                />
              </g>
            );
          })}
        </svg>

        {/* Draggable Table Cards */}
        {tables.map((table) => {
          const pos = positions[table.name] || { x: 30, y: 30 };
          const isSelected = selectedTable === table.name;

          return (
            <div
              key={table.name}
              onMouseDown={(e) => handleMouseDown(e, table.name)}
              style={{
                transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
                cursor: draggingTable === table.name ? 'grabbing' : 'grab',
              }}
              className={`absolute top-0 left-0 w-64 rounded-2xl border bg-white dark:bg-slate-900 shadow-xl overflow-hidden z-10 select-none ${
                isSelected
                  ? 'border-indigo-600 ring-2 ring-indigo-600/30'
                  : 'border-slate-200 dark:border-slate-800'
              }`}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 bg-slate-100 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-white">
                  <Database className="w-4 h-4 text-indigo-600" />
                  <span>{table.name}</span>
                </div>
                <span className="text-xs text-slate-500 font-medium">
                  {table.columns.length} colunas
                </span>
              </div>

              {/* Columns */}
              <div className="p-3 space-y-2 divide-y divide-slate-100 dark:divide-slate-800">
                {table.columns.map((col) => (
                  <div
                    key={col.name}
                    className="flex items-center justify-between pt-1.5 text-sm font-mono"
                  >
                    <div className="flex items-center gap-2 truncate">
                      {col.isPk ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 font-bold border border-amber-300 dark:border-amber-800">
                          PK
                        </span>
                      ) : col.isFk ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-300 font-bold border border-indigo-300 dark:border-indigo-800">
                          FK
                        </span>
                      ) : (
                        <span className="w-2.5 h-2.5 rounded-full bg-slate-300 dark:bg-slate-700 inline-block" />
                      )}
                      <span className={col.isPk ? 'font-bold text-amber-700 dark:text-amber-300' : 'text-slate-800 dark:text-slate-200'}>
                        {col.name}
                      </span>
                    </div>

                    <span className="text-xs text-slate-400 font-sans">
                      {col.type}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
