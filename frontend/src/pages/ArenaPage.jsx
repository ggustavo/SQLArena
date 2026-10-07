import React, { useState, useEffect } from 'react';
import { ArrowLeft, BookOpen, Network, TableProperties, ChevronDown, ChevronUp, Tag } from 'lucide-react';
import SqlEditor from '../components/SqlEditor';
import RelationalDiagram from '../components/RelationalDiagram';
import SampleDataAccordion from '../components/SampleDataAccordion';
import ResultDrawer from '../components/ResultDrawer';
import { submitQuery, checkSubmissionStatus, fetchLastSubmittedSql } from '../services/submissionService';
import { getCategoryMeta } from '../utils/categoryMeta';

function extractErrorText(err) {
  const detail = err.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join(' ');
  }
  if (typeof detail === 'string') {
    return detail;
  }
  if (err.response?.status === 403) {
    return 'Esta questão precisa ser publicada pelo instrutor para que seja possível executá-la.';
  }
  return err.message || 'Erro inesperado ao executar a consulta.';
}

export default function ArenaPage({ question, onBack, user, onAddPoints, initialSql }) {
  const [code, setCode] = useState(() => initialSql || '');
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // Estados de colapso de cada seção de referência
  const [collapseMission, setCollapseMission] = useState(false);
  const [collapseModel, setCollapseModel] = useState(false);
  const [collapseSample, setCollapseSample] = useState(false);

  useEffect(() => {
    let isMounted = true;
    if (initialSql) {
      setCode(initialSql);
      return;
    }

    // Inicializa estritamente em branco para a nova questão
    setCode('');

    async function loadLastCode() {
      try {
        const remoteQuery = await fetchLastSubmittedSql(question?.id);
        if (isMounted) {
          setCode(remoteQuery || '');
        }
      } catch {
        if (isMounted) setCode('');
      }
    }

    if (question?.id) {
      loadLastCode();
    }

    return () => {
      isMounted = false;
    };
  }, [question?.id, initialSql]);

  const handleRunQuery = async () => {
    setIsRunning(true);
    setErrorMessage(null);
    setResult(null);

    try {
      const submissionResponse = await submitQuery({
        questionId: question.id,
        questionTitle: question.title,
        difficulty: question.difficulty,
        sqlQuery: code,
        userId: user?.id || 'user_101',
      });

      const submissionId = submissionResponse.submissionId;

      let pollAttempts = 0;
      const pollTimer = setInterval(async () => {
        try {
          pollAttempts += 1;
          const statusData = await checkSubmissionStatus(submissionId);

          if (statusData.status === 'DONE') {
            clearInterval(pollTimer);
            setIsRunning(false);
            setResult({
              ...statusData,
              pointsAwarded: statusData.pointsAwarded || 1,
            });

            if (statusData.outcome === 'SUCCESS' && onAddPoints) {
              onAddPoints(10);
            }
          } else if (pollAttempts > 35) {
            clearInterval(pollTimer);
            setIsRunning(false);
            setErrorMessage('Tempo limite excedido na execução da consulta.');
          }
        } catch (pollErr) {
          clearInterval(pollTimer);
          setIsRunning(false);
          setErrorMessage(extractErrorText(pollErr));
        }
      }, 700);
    } catch (err) {
      setIsRunning(false);
      setErrorMessage(extractErrorText(err));
    }
  };

  return (
    <div className="w-full flex flex-col transition-colors">
      {/* 
        STICKY QUESTION TOP BAR (Trava abaixo da Navbar)
        Navbar = top-0 z-40.
        Question Bar = top-[65px] z-30.
      */}
      <div className="sticky top-[65px] z-30 w-full bg-white/95 dark:bg-[#1b1e26]/95 backdrop-blur border-b border-slate-200 dark:border-[#2d3340] px-6 lg:px-12 py-3.5 shadow-xs transition-colors">
        <div className="w-full flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 dark:bg-[#252a35] hover:bg-slate-200 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#333a47] text-slate-700 dark:text-slate-200 text-xs sm:text-sm font-semibold transition"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Voltar ao Mural</span>
            </button>

            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
                Questão #{question.id}. {question.title}
              </h1>
              <span
                className={`text-xs font-bold px-3 py-1 rounded-full ${
                  question.difficulty === 'Fácil'
                    ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800'
                    : question.difficulty === 'Médio'
                    ? 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800'
                    : 'bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800'
                }`}
              >
                {question.difficulty}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs sm:text-sm font-semibold text-slate-500">
            <span>Tópicos:</span>
            <div className="flex flex-wrap gap-1.5">
              {[...(question?.categories || (question?.category ? [question.category] : ['Geral']))]
                .sort((a, b) => a.localeCompare(b, 'pt-BR'))
                .map((cat) => {
                  const meta = getCategoryMeta(cat);
                  const IconComp = meta.icon;
                  return (
                    <span
                      key={cat}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${meta.bg} ${meta.color} ${meta.border}`}
                    >
                      <IconComp className="w-3.5 h-3.5" />
                      <span>{meta.displayName || cat}</span>
                    </span>
                  );
                })}
            </div>
          </div>
        </div>
      </div>

      {/* Main Full-Width Content: Left Side (Scrolls) | Right Side (Sticky Editor) */}
      <div className="w-full px-6 lg:px-12 pt-3 pb-6">
        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Side: Enunciado, Modelo Relacional e Dados de Exemplo empilhados verticalmente */}
          <div className="lg:col-span-6 space-y-6">
            {/* 1. ENUNCIADO DA QUESTÃO */}
            <div className="rounded-3xl bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#2d3340] p-7 sm:p-8 shadow-sm space-y-4 transition">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-[#2a2f3a] pb-3">
                <div className="flex items-center gap-2.5 text-base font-bold text-slate-900 dark:text-slate-100">
                  <div className="w-8 h-8 rounded-xl bg-slate-100 dark:bg-[#282d37] border border-slate-200 dark:border-[#353d4d] flex items-center justify-center text-slate-700 dark:text-slate-300">
                    <BookOpen className="w-4 h-4" />
                  </div>
                  <span>1. Enunciado da Questão</span>
                </div>
                <button
                  type="button"
                  onClick={() => setCollapseMission(!collapseMission)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition"
                >
                  {collapseMission ? <ChevronDown className="w-5 h-5" /> : <ChevronUp className="w-5 h-5" />}
                </button>
              </div>

              {!collapseMission && (
                <div className="space-y-4">
                  <div className="whitespace-pre-line text-base text-slate-700 dark:text-slate-300 leading-relaxed">
                    {question.description}
                  </div>

                  {question.expectedColumns && (
                    <div className="pt-3 border-t border-slate-100 dark:border-[#2a2f3a] space-y-2">
                      <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        Colunas esperadas no retorno da sua consulta:
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {question.expectedColumns.map((c) => (
                          <code
                            key={c}
                            className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-[#262b35] border border-slate-200 dark:border-[#343b48] font-mono text-sm text-slate-800 dark:text-slate-200 font-semibold"
                          >
                            {c}
                          </code>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 2. MODELO RELACIONAL */}
            <div className="rounded-3xl bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#2d3340] p-7 sm:p-8 shadow-sm space-y-4 transition">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-[#2a2f3a] pb-3">
                <div className="flex items-center gap-2.5 text-base font-bold text-slate-900 dark:text-slate-100">
                  <div className="w-8 h-8 rounded-xl bg-slate-100 dark:bg-[#282d37] border border-slate-200 dark:border-[#353d4d] flex items-center justify-center text-slate-700 dark:text-slate-300">
                    <Network className="w-4 h-4" />
                  </div>
                  <span>2. Modelo Relacional</span>
                </div>
                <button
                  type="button"
                  onClick={() => setCollapseModel(!collapseModel)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition"
                >
                  {collapseModel ? <ChevronDown className="w-5 h-5" /> : <ChevronUp className="w-5 h-5" />}
                </button>
              </div>

              {!collapseModel && (
                <div>
                  <RelationalDiagram schemaSql={question.schemaSql} />
                </div>
              )}
            </div>

            {/* 3. DADOS DE EXEMPLO */}
            <div className="rounded-3xl bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#2d3340] p-7 sm:p-8 shadow-sm space-y-4 transition">
              <div className="flex items-center justify-between border-b border-slate-100 dark:border-[#2a2f3a] pb-3">
                <div className="flex items-center gap-2.5 text-base font-bold text-slate-900 dark:text-slate-100">
                  <div className="w-8 h-8 rounded-xl bg-slate-100 dark:bg-[#282d37] border border-slate-200 dark:border-[#353d4d] flex items-center justify-center text-slate-700 dark:text-slate-300">
                    <TableProperties className="w-4 h-4" />
                  </div>
                  <span>3. Dados de Exemplo</span>
                </div>
                <button
                  type="button"
                  onClick={() => setCollapseSample(!collapseSample)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition"
                >
                  {collapseSample ? <ChevronDown className="w-5 h-5" /> : <ChevronUp className="w-5 h-5" />}
                </button>
              </div>

              {!collapseSample && (
                <div>
                  <SampleDataAccordion sampleTables={question.sampleTables} />
                </div>
              )}
            </div>
          </div>

          {/* Right Side: Execution Result (above) & Monaco SQL Editor (Pinned/Sticky) */}
          <div className="lg:col-span-6 flex flex-col gap-2.5 lg:sticky lg:top-[132px] lg:h-[calc(100vh-165px)] transition-all">
            {(result || errorMessage || isRunning) && (
              <ResultDrawer
                result={result}
                error={errorMessage}
                isRunning={isRunning}
                onClose={() => {
                  setResult(null);
                  setErrorMessage(null);
                }}
              />
            )}

            <SqlEditor
              code={code}
              setCode={setCode}
              onRun={handleRunQuery}
              isRunning={isRunning}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
