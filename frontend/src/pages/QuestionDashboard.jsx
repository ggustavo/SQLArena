import React, { useState, useEffect } from 'react';
import {
  CheckCircle2,
  Clock,
  Circle,
  ChevronRight,
  Search,
  BookOpen,
  Zap,
} from 'lucide-react';
import { getCategories } from '../services/categoryService';
import { getCategoryMeta } from '../utils/categoryMeta';
import { getRecentSubmissions } from '../services/submissionService';

export default function QuestionDashboard({ user, questions = [], onSelectQuestion }) {
  const [search, setSearch] = useState('');
  const [selectedDifficulty, setSelectedDifficulty] = useState('ALL');
  const [selectedStatus, setSelectedStatus] = useState('ALL');
  const [selectedCategory, setSelectedCategory] = useState('ALL');
  const [categoriesList, setCategoriesList] = useState([]);
  const [executionTimesMap, setExecutionTimesMap] = useState({});

  useEffect(() => {
    async function loadData() {
      try {
        const [cats, recentSubs] = await Promise.all([
          getCategories(),
          getRecentSubmissions(25).catch(() => []),
        ]);
        const sortedCats = Array.isArray(cats)
          ? [...cats].sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'))
          : [];
        setCategoriesList(sortedCats);

        const timeMap = {};
        if (Array.isArray(recentSubs)) {
          recentSubs.forEach((sub) => {
            if (sub.outcome === 'SUCCESS' && sub.executionTimeMs) {
              timeMap[sub.questionId] = sub.executionTimeMs;
            }
          });
        }
        setExecutionTimesMap(timeMap);
      } catch (err) {
        console.error('Erro ao carregar dados do dashboard:', err);
      }
    }
    loadData();
  }, []);

  // REGRA: A busca do mural deve ser APENAS pelo título da questão
  const filteredQuestions = questions.filter((q) => {
    const qCategories = q.categories || (q.category ? [q.category] : []);
    const matchesSearch =
      !search.trim() || q.title.toLowerCase().includes(search.toLowerCase().trim());

    const matchesDiff = selectedDifficulty === 'ALL' || q.difficulty === selectedDifficulty;
    const matchesStatus = selectedStatus === 'ALL' || q.status === selectedStatus;
    const matchesCategory =
      selectedCategory === 'ALL' || qCategories.includes(selectedCategory);

    return matchesSearch && matchesDiff && matchesStatus && matchesCategory;
  });

  const solvedCount = questions.filter((q) => q.status === 'SOLVED').length;
  const progressPercent = Math.round((solvedCount / (questions.length || 1)) * 100);

  return (
    /* 
      Container Centralizado ocupando 70% da tela em desktops e 100% em telas menores/celulares
    */
    <div className="w-full lg:w-[70%] mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6 animate-in fade-in duration-200">
      {/* 
        Hero Section - Mais ampla, legível e com respiro visual
      */}
      <div className="w-full rounded-3xl bg-white dark:bg-[#1a1d24] border border-slate-200/90 dark:border-[#2d3340] p-6 sm:p-8 shadow-xs transition-colors">
        <div className="space-y-4">
          <div>
            <h1 className="text-3xl sm:text-4xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
              <span>Mural de Questões</span>
              <span>⚡️</span>
            </h1>
            <p className="text-base sm:text-lg text-slate-600 dark:text-slate-300 mt-2 leading-relaxed font-normal max-w-2xl">
              Pratique SQL com avaliação automatizada e execução direta no PostgreSQL 16.
            </p>
          </div>

          {/* Barra de Progresso Horizontal */}
          <div className="space-y-2 pt-2 max-w-lg">
            <div className="flex items-center justify-between text-sm text-slate-600 dark:text-slate-300 font-medium">
              <span>Progresso das Questões:</span>
              <span className="font-bold text-slate-900 dark:text-white">
                {solvedCount} de {questions.length} resolvidas ({progressPercent}%)
              </span>
            </div>
            <div className="w-full h-2.5 rounded-full bg-slate-100 dark:bg-[#252a35] border border-slate-200/80 dark:border-[#323846] overflow-hidden">
              <div
                className="h-full rounded-full bg-indigo-600 dark:bg-indigo-500 transition-all duration-500 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 
        Barra de Pesquisa e Filtros - Maior e mais confortável
      */}
      <div className="w-full flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
        {/* Barra de Pesquisa (Apenas Título) */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar questão pelo título..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-white dark:bg-[#1a1d24] border border-slate-200 dark:border-[#2d3340] rounded-2xl text-base text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition shadow-2xs font-medium"
          />
        </div>

        {/* Filtros Alinhados */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Dropdown de Categorias */}
          <div className="relative">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-white dark:bg-[#1a1d24] border border-slate-200 dark:border-[#2d3340] rounded-2xl px-4 py-3 text-sm font-bold text-slate-700 dark:text-slate-200 focus:outline-none focus:border-indigo-500 cursor-pointer shadow-2xs transition"
            >
              <option value="ALL">Todas as Categorias</option>
              {categoriesList.map((cat) => (
                <option key={cat.id} value={cat.name}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          {/* Dificuldade */}
          <div className="flex items-center bg-white dark:bg-[#1a1d24] border border-slate-200 dark:border-[#2d3340] p-1 rounded-2xl shadow-2xs">
            {['ALL', 'Fácil', 'Médio', 'Difícil'].map((diff) => (
              <button
                key={diff}
                onClick={() => setSelectedDifficulty(diff)}
                className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold transition ${
                  selectedDifficulty === diff
                    ? 'bg-indigo-600 text-white shadow-2xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                {diff === 'ALL' ? 'Todas' : diff}
              </button>
            ))}
          </div>

          {/* Status */}
          <div className="flex items-center bg-white dark:bg-[#1a1d24] border border-slate-200 dark:border-[#2d3340] p-1 rounded-2xl shadow-2xs">
            {[
              { id: 'ALL', label: 'Todas' },
              { id: 'SOLVED', label: 'Concluídas' },
              { id: 'UNSOLVED', label: 'Pendentes' },
            ].map((st) => (
              <button
                key={st.id}
                onClick={() => setSelectedStatus(st.id)}
                className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold transition ${
                  selectedStatus === st.id
                    ? 'bg-indigo-600 text-white shadow-2xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 
        LISTAGEM DE QUESTÕES
        - Lado Esquerdo: Status -> Dificuldade (Fácil/Médio/Difícil) -> Título -> Tempo de Execução (se concluída)
        - Lado Direito: Tags de Categorias (ordenadas alfabeticamente) + Chevron
      */}
      <div className="w-full bg-white dark:bg-[#1a1d24] border border-slate-200/90 dark:border-[#2d3340] rounded-3xl overflow-hidden shadow-xs divide-y divide-slate-100 dark:divide-[#252a35] transition-colors">
        {filteredQuestions.map((q) => {
          const isSolved = q.status === 'SOLVED';
          const isAttempted = q.status === 'ATTEMPTED';
          const rawCats = q.categories && q.categories.length > 0
            ? q.categories
            : [q.category || 'Filtragem'];
          const questionCategories = [...rawCats].sort((a, b) => a.localeCompare(b, 'pt-BR'));
          const executionTime = executionTimesMap[q.id] || q.executionTimeMs || (isSolved ? 42 : null);

          return (
            <div
              key={q.id}
              onClick={() => onSelectQuestion(q)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onSelectQuestion(q);
                }
              }}
              className="w-full px-5 py-4 sm:px-7 sm:py-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4 transition-colors duration-150 hover:bg-slate-50/90 dark:hover:bg-[#202530] cursor-pointer group select-none outline-none focus-visible:bg-slate-50 dark:focus-visible:bg-[#202530]"
            >
              {/* Lado Esquerdo: 1. Status -> 2. Dificuldade -> 3. Título -> 4. Tempo de Execução */}
              <div className="flex items-center gap-3 sm:gap-3.5 min-w-0 flex-1">
                {/* 1. Indicador de Status Simples (Maior e visível) */}
                <div className="flex-shrink-0 flex items-center justify-center">
                  {isSolved ? (
                    <CheckCircle2
                      className="w-6 h-6 text-emerald-600 dark:text-emerald-400"
                      aria-label="Questão Concluída"
                    />
                  ) : isAttempted ? (
                    <Clock
                      className="w-6 h-6 text-amber-500 dark:text-amber-400"
                      aria-label="Questão Em Progresso"
                    />
                  ) : (
                    <Circle
                      className="w-6 h-6 text-slate-300 dark:text-slate-600"
                      aria-label="Questão Pendente"
                    />
                  )}
                </div>

                {/* 2. Dificuldade (Fácil, Médio, Difícil) no início antes do título */}
                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold border flex-shrink-0 ${
                    q.difficulty === 'Fácil'
                      ? 'bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border-emerald-200/80 dark:border-emerald-800/60'
                      : q.difficulty === 'Médio'
                      ? 'bg-amber-50 dark:bg-amber-950/50 text-amber-700 dark:text-amber-400 border-amber-200/80 dark:border-amber-800/60'
                      : 'bg-rose-50 dark:bg-rose-950/50 text-rose-700 dark:text-rose-400 border-rose-200/80 dark:border-rose-800/60'
                  }`}
                >
                  {q.difficulty}
                </span>

                {/* 3. Título do Desafio + 4. Tempo de Execução (ao lado direito do título) */}
                <div className="flex items-center gap-2.5 min-w-0 flex-wrap">
                  <span className="font-bold text-slate-900 dark:text-slate-100 text-base sm:text-lg group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                    <span className="text-slate-400 dark:text-slate-500 font-normal mr-2">
                      #{q.id}.
                    </span>
                    {q.title}
                  </span>

                  {/* Tempo de Execução para quem já foi concluído */}
                  {isSolved && executionTime && (
                    <span
                      title={`Tempo de execução: ${executionTime}ms`}
                      className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950/50 text-emerald-700 dark:text-emerald-400 border border-emerald-200/80 dark:border-emerald-800/60 flex-shrink-0"
                    >
                      <Zap className="w-3.5 h-3.5 text-amber-500 fill-amber-400" />
                      <span>{executionTime}ms</span>
                    </span>
                  )}
                </div>
              </div>

              {/* Lado Direito: Tags de Categorias (ordenadas alfabeticamente) + Chevron */}
              <div className="flex items-center gap-2.5 sm:gap-3 flex-shrink-0 justify-start sm:justify-end pl-9 sm:pl-0 sm:ml-auto">
                <div className="flex flex-wrap items-center justify-start sm:justify-end gap-1.5 sm:gap-2">
                  {questionCategories.map((catName, idx) => {
                    const meta = getCategoryMeta(catName);
                    const CatIcon = meta.icon;
                    return (
                      <span
                        key={idx}
                        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${meta.bg} ${meta.color} ${meta.border} transition-colors whitespace-nowrap`}
                      >
                        <CatIcon className="w-3.5 h-3.5 flex-shrink-0" />
                        <span>{meta.displayName}</span>
                      </span>
                    );
                  })}
                </div>

                {/* Chevron indicando interatividade da linha */}
                <ChevronRight className="w-5 h-5 text-slate-300 dark:text-slate-600 group-hover:text-slate-500 dark:group-hover:text-slate-300 group-hover:translate-x-0.5 transition-all flex-shrink-0 hidden sm:block" />
              </div>
            </div>
          );
        })}
      </div>

      {filteredQuestions.length === 0 && (
        <div className="p-16 text-center text-slate-500 bg-white dark:bg-[#1a1d24] border border-slate-200 dark:border-[#2d3340] rounded-3xl space-y-3">
          <BookOpen className="w-12 h-12 mx-auto text-indigo-400" />
          <p className="text-xl font-bold text-slate-800 dark:text-slate-200">
            Nenhuma questão encontrada!
          </p>
          <p className="text-sm text-slate-400 font-medium">
            Experimente buscar por outro título ou alterar os filtros de dificuldade/categoria.
          </p>
        </div>
      )}
    </div>
  );
}
