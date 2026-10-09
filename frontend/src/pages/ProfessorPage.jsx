import React, { useState, useEffect } from 'react';
import { getQuestions, createQuestion, deleteQuestion } from '../services/questionService';
import { getCategories } from '../services/categoryService';
import { PlusCircle, Trash2, ArrowLeft, Database, CheckCircle2, AlertCircle, Tag } from 'lucide-react';

export default function ProfessorPage({ onBack }) {
  const [questions, setQuestions] = useState([]);
  const [categoriesList, setCategoriesList] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState(['JOINs']);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const [title, setTitle] = useState('');
  const [difficulty, setDifficulty] = useState('Médio');
  const [description, setDescription] = useState('');
  const [schemaSql, setSchemaSql] = useState(`CREATE TABLE autores (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL
);

CREATE TABLE livros (
    id SERIAL PRIMARY KEY,
    autor_id INT REFERENCES autores(id),
    titulo VARCHAR(120) NOT NULL,
    vendas INT DEFAULT 0
);`);
  const [dataSql, setDataSql] = useState(`INSERT INTO autores (nome) VALUES ('Machado de Assis'), ('Clarice Lispector');
INSERT INTO livros (autor_id, titulo, vendas) VALUES (1, 'Dom Casmurro', 15000), (2, 'A Hora da Estrela', 8900);`);
  const [answerSql, setAnswerSql] = useState(`SELECT a.nome, SUM(l.vendas) as total_vendas
FROM autores a
JOIN livros l ON l.autor_id = a.id
GROUP BY a.id, a.nome
ORDER BY total_vendas DESC;`);

  const fetchInitialData = async () => {
    try {
      setLoading(true);
      const [questionsData, categoriesData] = await Promise.all([
        getQuestions('INSTRUCTOR'),
        getCategories(),
      ]);
      setQuestions(questionsData);
      setCategoriesList(categoriesData);
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInitialData();
  }, []);

  const toggleCategory = (catName) => {
    if (selectedCategories.includes(catName)) {
      if (selectedCategories.length > 1) {
        setSelectedCategories(selectedCategories.filter((c) => c !== catName));
      }
    } else {
      setSelectedCategories([...selectedCategories, catName]);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setErrorMessage(null);
    setNotification(null);
    setIsSubmitting(true);

    try {
      const created = await createQuestion({
        title,
        difficulty,
        categories: selectedCategories,
        category: selectedCategories[0] || 'Geral',
        description,
        schemaSql,
        dataSql,
        answerSql,
      });

      setNotification(`Questão "${created.title}" cadastrada com sucesso!`);
      setTitle('');
      setDescription('');
      const updated = await getQuestions('INSTRUCTOR');
      setQuestions(updated);
    } catch (err) {
      setErrorMessage(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(`Deseja realmente remover a questão #${id}?`)) return;
    try {
      await deleteQuestion(id);
      setNotification(`Questão #${id} removida com sucesso.`);
      const updated = await getQuestions('INSTRUCTOR');
      setQuestions(updated);
    } catch (err) {
      setErrorMessage(err.message);
    }
  };

  return (
    <div className="w-full px-6 lg:px-12 py-8 space-y-8">
      {/* Top Header */}
      <div className="w-full flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 text-slate-700 dark:text-slate-200 text-sm font-semibold hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          >
            <ArrowLeft className="w-4 h-4" />
            Voltar ao Mural
          </button>
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Painel do Instrutor // Cadastro de Questões
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Crie novas questões práticas de SQL e vincule às categorias pré-definidas.
            </p>
          </div>
        </div>
      </div>

      {notification && (
        <div className="w-full p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-sm font-medium flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <span>{notification}</span>
          </div>
          <button onClick={() => setNotification(null)} className="underline text-sm font-semibold">
            Fechar
          </button>
        </div>
      )}

      {errorMessage && (
        <div className="w-full p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/60 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300 text-sm font-medium flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* 100% FULL-WIDTH GRID (7 cols Form | 5 cols Questões Cadastradas) */}
      <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left: Formulário de Criação (7 cols) */}
        <div className="lg:col-span-7 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 sm:p-10 shadow-lg space-y-6">
          <div className="flex items-center gap-3 text-lg font-bold text-slate-900 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-4">
            <PlusCircle className="w-6 h-6 text-indigo-600" />
            Cadastrar Nova Questão SQL
          </div>

          <form onSubmit={handleCreate} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
              <div className="sm:col-span-2 space-y-2">
                <label className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  Título da Questão
                </label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Top 5 Clientes com Maior Faturamento"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl p-3.5 text-base text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  Dificuldade
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl p-3.5 text-base text-slate-900 dark:text-slate-100 font-semibold focus:outline-none focus:border-indigo-600"
                >
                  <option value="Fácil">Fácil</option>
                  <option value="Médio">Médio</option>
                  <option value="Difícil">Difícil</option>
                </select>
              </div>
            </div>

            {/* Predefined Categories Multi-Selector */}
            <div className="space-y-2.5">
              <label className="text-sm font-semibold text-slate-800 dark:text-slate-200 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Tag className="w-4 h-4 text-indigo-600" />
                  Categorias Pré-definidas (selecione uma ou mais):
                </span>
                <span className="text-xs text-indigo-600 dark:text-indigo-400 font-bold">
                  {selectedCategories.length} selecionada(s)
                </span>
              </label>

              <div className="flex flex-wrap gap-2 p-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-2xl">
                {categoriesList.map((cat) => {
                  const isSelected = selectedCategories.includes(cat.name);
                  return (
                    <button
                      key={cat.id}
                      type="button"
                      onClick={() => toggleCategory(cat.name)}
                      className={`px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-semibold transition border ${
                        isSelected
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                          : 'bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-300 dark:border-slate-800 hover:border-indigo-500'
                      }`}
                    >
                      {isSelected ? `✓ ${cat.name}` : `+ ${cat.name}`}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                Enunciado & Instruções do Problema
              </label>
              <textarea
                rows={4}
                required
                placeholder="Descreva o cenário de negócio e o que a consulta do aluno deve resolver..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl p-3.5 text-base text-slate-900 dark:text-slate-100 leading-relaxed focus:outline-none focus:border-indigo-600"
              />
            </div>

            {/* SQL Scripts Definition */}
            <div className="space-y-5 pt-3 border-t border-slate-100 dark:border-slate-800">
              <div className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
                Definições de Banco de Dados (PostgreSQL)
              </div>

              <div className="space-y-2">
                <span className="font-mono text-sm text-indigo-600 dark:text-indigo-400 font-bold">
                  1. Estrutura das Tabelas (schema.sql)
                </span>
                <textarea
                  rows={4}
                  value={schemaSql}
                  onChange={(e) => setSchemaSql(e.target.value)}
                  className="w-full font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl p-3 text-sm text-slate-900 dark:text-slate-100 leading-relaxed"
                />
              </div>

              <div className="space-y-2">
                <span className="font-mono text-sm text-indigo-600 dark:text-indigo-400 font-bold">
                  2. Carga de Dados de Exemplo (data.sql)
                </span>
                <textarea
                  rows={4}
                  value={dataSql}
                  onChange={(e) => setDataSql(e.target.value)}
                  className="w-full font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl p-3 text-sm text-slate-900 dark:text-slate-100 leading-relaxed"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm text-emerald-600 dark:text-emerald-400 font-bold">
                    3. Gabarito Oficial (answer.sql)
                  </span>
                  <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">
                    Obrigatório incluir ORDER BY
                  </span>
                </div>
                <textarea
                  rows={4}
                  value={answerSql}
                  onChange={(e) => setAnswerSql(e.target.value)}
                  className="w-full font-mono bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl p-3 text-sm text-slate-900 dark:text-slate-100 leading-relaxed"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-base transition shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Salvando Questão...
                </>
              ) : (
                <>
                  <PlusCircle className="w-5 h-5" />
                  Salvar e Disponibilizar Questão
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right: Questões Cadastradas (5 cols) */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 sm:p-10 shadow-lg space-y-6">
          <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
            <span className="text-lg font-bold text-slate-900 dark:text-white">
              Questões Cadastradas
            </span>
            <span className="text-sm font-semibold text-slate-500 font-mono">
              {questions.length} no total
            </span>
          </div>

          <div className="space-y-4 max-h-[800px] overflow-y-auto pr-1">
            {questions.map((q) => {
              const qCategories = q.categories || (q.category ? [q.category] : []);

              return (
                <div
                  key={q.id}
                  className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <span className="text-xs font-mono text-slate-400 font-bold">QUESTÃO #{q.id}</span>
                      <h3 className="text-base font-bold text-slate-900 dark:text-white mt-0.5">
                        {q.title}
                      </h3>
                    </div>

                    <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 shrink-0">
                      Publicada
                    </span>
                  </div>

                  {/* Multi-Categories Tags */}
                  <div className="flex flex-wrap gap-1.5">
                    {qCategories.map((cat) => (
                      <span
                        key={cat}
                        className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/60"
                      >
                        {cat}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-slate-200 dark:border-slate-800 text-sm">
                    <span className="text-sm text-slate-600 dark:text-slate-400 font-medium">
                      Dificuldade: <strong className="text-slate-900 dark:text-slate-200">{q.difficulty}</strong>
                    </span>

                    <button
                      onClick={() => handleDelete(q.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-sm font-semibold transition"
                      title="Excluir questão"
                    >
                      <Trash2 className="w-4 h-4" />
                      Excluir
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
