import React, { useState } from 'react';
import Editor from '@monaco-editor/react';
import { Play, Maximize2, Minimize2, Terminal } from 'lucide-react';

export default function SqlEditor({ code, setCode, onRun, isRunning }) {
  const [isFullscreen, setIsFullscreen] = useState(false);

  const handleEditorDidMount = (editor, monaco) => {
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      onRun();
    });
  };

  return (
    <div
      className={`flex flex-col bg-white dark:bg-[#1f232b] rounded-3xl border border-slate-200 dark:border-[#2d3340] overflow-hidden shadow-sm transition-all ${
        isFullscreen
          ? 'fixed inset-4 z-50 shadow-2xl ring-2 ring-slate-400 dark:ring-slate-600'
          : 'relative w-full flex-1 min-h-0'
      }`}
    >
      {/* Editor Header Bar */}
      <div className="flex items-center justify-between px-6 py-3.5 bg-slate-50 dark:bg-[#1a1d24] border-b border-slate-200 dark:border-[#2d3340] select-none shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
              <Terminal className="w-4 h-4 text-slate-500 dark:text-slate-400" />
              Editor SQL (PostgreSQL 16)
            </span>
          </div>
          <span className="text-xs text-slate-500 hidden sm:inline">
            • <kbd className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-[#282d37] text-slate-700 dark:text-slate-300 font-mono text-xs border border-slate-300 dark:border-[#353d4d]">Ctrl + Enter</kbd> para rodar
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Fullscreen Toggle */}
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            title={isFullscreen ? 'Sair da tela cheia' : 'Expandir tela cheia'}
            className="p-2 rounded-xl bg-white dark:bg-[#262b35] border border-slate-200 dark:border-[#343b48] text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition"
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          {/* Run Button */}
          <button
            type="button"
            onClick={onRun}
            disabled={isRunning}
            className={`flex items-center gap-2 px-5 py-2 rounded-xl font-bold text-sm transition-all shadow-xs ${
              isRunning
                ? 'bg-slate-300 dark:bg-[#2e3442] text-slate-500 cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white active:scale-98'
            }`}
          >
            {isRunning ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Executando...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Executar Consulta</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Monaco Editor Body - Full Available Height with internal smooth scrolling */}
      <div className="w-full flex-1 min-h-0">
        <Editor
          height="100%"
          language="sql"
          theme="vs-dark"
          value={code}
          onChange={(val) => setCode(val || '')}
          onMount={handleEditorDidMount}
          options={{
            minimap: { enabled: false },
            fontSize: 16,
            lineHeight: 25,
            fontFamily: "'JetBrains Mono', monospace",
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 2,
            wordWrap: 'on',
            scrollbar: {
              vertical: 'visible',
              horizontal: 'auto',
              verticalScrollbarSize: 10,
              horizontalScrollbarSize: 10,
            },
            padding: { top: 16, bottom: 16 },
          }}
        />
      </div>
    </div>
  );
}
