import React, { useState, useEffect, useRef } from 'react';
import { getQuestions, createQuestion, deleteQuestion, publishQuestion } from '../services/questionService';
import { getCategories } from '../services/categoryService';
import {
  PlusCircle,
  Trash2,
  ArrowLeft,
  Send,
  CheckCircle2,
  AlertCircle,
  Tag,
  Upload,
  FileCode,
  Code2,
  FolderUp,
  Eye,
  EyeOff,
  X,
  FileText,
} from 'lucide-react';

function errorText(err) {
  const detail = err.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(' ');
  return typeof detail === 'string' ? detail : err.message;
}

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

const readFileAsText = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = () => reject(new Error('Falha ao ler arquivo.'));
    reader.readAsText(file);
  });
};

export default function ProfessorPage({ onBack }) {
  const [questions, setQuestions] = useState([]);
  const [categoriesList, setCategoriesList] = useState([]);
  const [selectedCategories, setSelectedCategories] = useState(['JOINs']);
  const [loading, setLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pendingId, setPendingId] = useState(null);
  const [notification, setNotification] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  const [title, setTitle] = useState('');
  const [difficulty, setDifficulty] = useState('Médio');
  const [description, setDescription] = useState('');

  // Estados dos scripts SQL
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

  // Modos de entrada (digitar ou arquivo) e arquivos anexados
  const [schemaMode, setSchemaMode] = useState('type'); // 'type' | 'upload'
  const [schemaFile, setSchemaFile] = useState(null); // { name, size, fileObject }
  const [showSchemaEditor, setShowSchemaEditor] = useState(false);

  const [dataMode, setDataMode] = useState('type');
  const [dataFile, setDataFile] = useState(null);
  const [showDataEditor, setShowDataEditor] = useState(false);

  const [answerMode, setAnswerMode] = useState('type');
  const [answerFile, setAnswerFile] = useState(null);
  const [showAnswerEditor, setShowAnswerEditor] = useState(false);

  const batchInputRef = useRef(null);
  const schemaInputRef = useRef(null);
  const dataInputRef = useRef(null);
  const answerInputRef = useRef(null);

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
      setErrorMessage(errorText(err));
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

  // Processa arquivo .sql individual
  const handleSingleFileUpload = async (file, setSql, setFile, setMode) => {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.sql')) {
      setErrorMessage(`O arquivo "${file.name}" não é válido. Apenas arquivos com extensão .sql são permitidos.`);
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      setErrorMessage(`O arquivo "${file.name}" ultrapassa o limite de 2 MB.`);
      return;
    }

    try {
      const text = await readFileAsText(file);
      setSql(text);
      setFile({ name: file.name, size: file.size, fileObject: file });
      setMode('upload');
      setErrorMessage(null);
    } catch {
      setErrorMessage(`Não foi possível ler o arquivo ${file.name}.`);
    }
  };

  // Processa upload em lote de múltiplos arquivos .sql
  const handleBatchFiles = async (filesList) => {
    if (!filesList || filesList.length === 0) return;
    setErrorMessage(null);
    let mappedCount = 0;

    for (const file of Array.from(filesList)) {
      if (!file.name.toLowerCase().endsWith('.sql')) continue;
      const lower = file.name.toLowerCase();
      try {
        const text = await readFileAsText(file);
        const meta = { name: file.name, size: file.size, fileObject: file };

        if (lower.includes('schema') || lower.includes('ddl') || lower.includes('tabela')) {
          setSchemaSql(text);
          setSchemaFile(meta);
          setSchemaMode('upload');
          mappedCount++;
        } else if (lower.includes('data') || lower.includes('seed') || lower.includes('insert') || lower.includes('carga')) {
          setDataSql(text);
          setDataFile(meta);
          setDataMode('upload');
          mappedCount++;
        } else if (lower.includes('answer') || lower.includes('gabarito') || lower.includes('solution') || lower.includes('solucao')) {
          setAnswerSql(text);
          setAnswerFile(meta);
          setAnswerMode('upload');
          mappedCount++;
        }
      } catch {
        // Ignora erro de leitura em lote
      }
    }

    if (mappedCount > 0) {
      setNotification(`✓ ${mappedCount} arquivo(s) .sql identificado(s) e carregado(s) com sucesso!`);
    } else {
      setErrorMessage('Nenhum arquivo .sql correspondente a schema, data ou answer foi identificado. Verifique os nomes dos arquivos.');
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setErrorMessage(null);
    setNotification(null);
    setIsSubmitting(true);

    try {
      // Se houver algum arquivo físico carregado, enviamos via FormData
      const hasFiles = Boolean(schemaFile?.fileObject || dataFile?.fileObject || answerFile?.fileObject);

      let payloadOrFormData;
      if (hasFiles) {
        const fd = new FormData();
        fd.append('title', title);
        fd.append('difficulty', difficulty);
        fd.append('description', description);
        fd.append('categories', JSON.stringify(selectedCategories));
        fd.append('category', selectedCategories[0] || 'Geral');

        if (schemaFile?.fileObject) {
          fd.append('schema_file', schemaFile.fileObject);
        }
        fd.append('schema_sql', schemaSql);

        if (dataFile?.fileObject) {
          fd.append('data_file', dataFile.fileObject);
        }
        fd.append('data_sql', dataSql);

        if (answerFile?.fileObject) {
          fd.append('answer_file', answerFile.fileObject);
        }
        fd.append('answer_sql', answerSql);

        payloadOrFormData = fd;
      } else {
        payloadOrFormData = {
          title,
          difficulty,
          categories: selectedCategories,
          category: selectedCategories[0] || 'Geral',
          description,
          schemaSql,
          dataSql,
          answerSql,
        };
      }

      const created = await createQuestion(payloadOrFormData);

      setNotification(`Questão "${created.title}" cadastrada com sucesso!`);
      setTitle('');
      setDescription('');
      setSchemaFile(null);
      setDataFile(null);
      setAnswerFile(null);
      setSchemaMode('type');
      setDataMode('type');
      setAnswerMode('type');

      const updated = await getQuestions('INSTRUCTOR');
      setQuestions(updated);
    } catch (err) {
      setErrorMessage(errorText(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(`Deseja realmente remover a questão #${id}?`)) return;
    setPendingId(id);
    setErrorMessage(null);
    setNotification(null);
    try {
      await deleteQuestion(id);
      setNotification(`Questão #${id} removida com sucesso.`);
      const updated = await getQuestions('INSTRUCTOR');
      setQuestions(updated);
    } catch (err) {
      setErrorMessage(errorText(err));
      try {
        setQuestions(await getQuestions('INSTRUCTOR'));
      } catch {
        // Mantém a mensagem da operação que falhou.
      }
    } finally {
      setPendingId(null);
    }
  };

  const handlePublish = async (id) => {
    setPendingId(id);
    setErrorMessage(null);
    setNotification(null);
    try {
      await publishQuestion(id);
      setNotification(`Questão #${id} publicada com sucesso.`);
    } catch (err) {
      setErrorMessage(errorText(err));
    } finally {
      setPendingId(null);
    }
  };

  const renderSqlSection = ({
    title,
    badge,
    accentColor,
    sql,
    setSql,
    mode,
    setMode,
    file,
    setFile,
    showEditor,
    setShowEditor,
    fileInputRef,
  }) => {
    const isIndigo = accentColor === 'indigo';
    const accentText = isIndigo ? 'text-indigo-600 dark:text-indigo-400' : 'text-emerald-600 dark:text-emerald-400';

    return (
      <div className="space-y-3 p-4 sm:p-5 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800">
        {/* Header com Título, Badge e Alternador de Modo */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className={`font-mono text-sm font-bold ${accentText}`}>
              {title}
            </span>
            {badge && (
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                {badge}
              </span>
            )}
          </div>

          {/* Alternador de Modo: Digitar vs Arquivo */}
          <div className="flex items-center bg-slate-200 dark:bg-slate-800 p-0.5 rounded-xl text-xs font-semibold">
            <button
              type="button"
              onClick={() => setMode('type')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition ${
                mode === 'type'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <Code2 className="w-3.5 h-3.5" />
              Digitar Código
            </button>
            <button
              type="button"
              onClick={() => setMode('upload')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition ${
                mode === 'upload'
                  ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
              }`}
            >
              <Upload className="w-3.5 h-3.5" />
              Enviar Arquivo .sql
            </button>
          </div>
        </div>

        {/* Input oculto para o arquivo */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".sql"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.[0]) {
              handleSingleFileUpload(e.target.files[0], setSql, setFile, setMode);
            }
          }}
        />

        {/* Modo Upload de Arquivo */}
        {mode === 'upload' && (
          <div className="space-y-3">
            {!file ? (
              <div
                onClick={() => fileInputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  if (e.dataTransfer.files?.[0]) {
                    handleSingleFileUpload(e.dataTransfer.files[0], setSql, setFile, setMode);
                  }
                }}
                className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-indigo-500 dark:hover:border-indigo-500 rounded-xl p-6 text-center cursor-pointer transition bg-white dark:bg-slate-900/60 hover:bg-indigo-50/30 dark:hover:bg-indigo-950/20 group"
              >
                <div className="w-10 h-10 mx-auto mb-2 rounded-xl bg-indigo-100 dark:bg-indigo-950/80 flex items-center justify-center text-indigo-600 dark:text-indigo-400 group-hover:scale-110 transition">
                  <Upload className="w-5 h-5" />
                </div>
                <div className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  Arraste seu arquivo <span className="font-mono text-indigo-600 dark:text-indigo-400">.sql</span> aqui ou{' '}
                  <span className="text-indigo-600 dark:text-indigo-400 underline">clique para selecionar</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Extensão permitida: .sql (máx. 2 MB)
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {/* Card do arquivo carregado */}
                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3 shadow-sm">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-9 h-9 rounded-lg bg-emerald-100 dark:bg-emerald-950/80 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                      <FileCode className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-sm font-bold text-slate-900 dark:text-white truncate">
                        {file.name}
                      </div>
                      <div className="text-xs text-slate-500 flex items-center gap-2">
                        <span>{formatFileSize(file.size)}</span>
                        <span className="text-emerald-600 dark:text-emerald-400 font-semibold flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5 inline" /> Arquivo carregado
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => setShowEditor(!showEditor)}
                      className="px-2.5 py-1.5 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold flex items-center gap-1 transition"
                      title={showEditor ? 'Ocultar código' : 'Ver / Editar código'}
                    >
                      {showEditor ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      <span className="hidden sm:inline">{showEditor ? 'Ocultar' : 'Ver / Editar'}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="px-2.5 py-1.5 rounded-lg text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 text-xs font-semibold transition"
                      title="Substituir arquivo"
                    >
                      Trocar
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setFile(null);
                        setSql('');
                      }}
                      className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/50 transition"
                      title="Remover arquivo"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Pré-visualização / Edição quando showEditor for true */}
                {showEditor && (
                  <div className="space-y-1.5 animate-in fade-in duration-200">
                    <div className="text-xs text-slate-500 font-medium flex items-center justify-between">
                      <span>Conteúdo do script SQL carregado (editável):</span>
                      <span className="font-mono">{sql.length} caracteres</span>
                    </div>
                    <textarea
                      rows={6}
                      value={sql}
                      onChange={(e) => setSql(e.target.value)}
                      className="w-full font-mono bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl p-3 text-sm text-slate-900 dark:text-slate-100 leading-relaxed focus:outline-none focus:border-indigo-600"
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Modo Digitar Código */}
        {mode === 'type' && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              {file ? (
                <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <FileCode className="w-3.5 h-3.5" /> Vinculado ao arquivo: <strong>{file.name}</strong>
                </span>
              ) : (
                <span className="text-xs text-slate-500">
                  Digite ou cole os comandos SQL abaixo:
                </span>
              )}

              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 font-semibold"
              >
                <Upload className="w-3 h-3" />
                Carregar de arquivo .sql
              </button>
            </div>

            <textarea
              rows={5}
              value={sql}
              onChange={(e) => setSql(e.target.value)}
              className="w-full font-mono bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-xl p-3.5 text-sm text-slate-900 dark:text-slate-100 leading-relaxed focus:outline-none focus:border-indigo-600"
            />
          </div>
        )}
      </div>
    );
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
                  maxLength={200}
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
            <div className="space-y-6 pt-3 border-t border-slate-100 dark:border-slate-800">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wide">
                  Definições de Banco de Dados (PostgreSQL)
                </div>
                <div className="text-xs text-slate-500 font-medium">
                  Envie arquivos <strong className="font-mono text-indigo-600 dark:text-indigo-400">.sql</strong> ou digite o código em cada campo
                </div>
              </div>

              {/* Importação Rápida em Lote (.sql) */}
              <div
                onClick={() => batchInputRef.current?.click()}
                onDragOver={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  handleBatchFiles(e.dataTransfer.files);
                }}
                className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-indigo-50/60 via-purple-50/40 to-slate-50 dark:from-indigo-950/30 dark:via-purple-950/20 dark:to-slate-900/40 border border-dashed border-indigo-300 dark:border-indigo-800/60 hover:border-indigo-500 transition cursor-pointer flex flex-col sm:flex-row items-center gap-4 text-center sm:text-left group"
              >
                <input
                  ref={batchInputRef}
                  type="file"
                  accept=".sql"
                  multiple
                  className="hidden"
                  onChange={(e) => handleBatchFiles(e.target.files)}
                />
                <div className="w-12 h-12 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-md shadow-indigo-600/20 group-hover:scale-105 transition">
                  <FolderUp className="w-6 h-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                    Importação Rápida em Lote (.sql)
                  </h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                    Selecione ou arraste os 3 arquivos de uma vez (<span className="font-mono">schema.sql</span>,{' '}
                    <span className="font-mono">data.sql</span>, <span className="font-mono">answer.sql</span>).
                    O sistema identifica e preenche automaticamente cada campo abaixo!
                  </p>
                </div>
                <button
                  type="button"
                  className="px-3.5 py-2 rounded-xl bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400 text-xs font-bold shadow-sm hover:bg-indigo-50 dark:hover:bg-slate-800 transition shrink-0"
                >
                  Selecionar Arquivos...
                </button>
              </div>

              {/* 1. Estrutura das Tabelas (schema.sql) */}
              {renderSqlSection({
                id: 'schema',
                title: '1. Estrutura das Tabelas (schema.sql)',
                accentColor: 'indigo',
                sql: schemaSql,
                setSql: setSchemaSql,
                mode: schemaMode,
                setMode: setSchemaMode,
                file: schemaFile,
                setFile: setSchemaFile,
                showEditor: showSchemaEditor,
                setShowEditor: setShowSchemaEditor,
                fileInputRef: schemaInputRef,
              })}

              {/* 2. Carga de Dados de Exemplo (data.sql) */}
              {renderSqlSection({
                id: 'data',
                title: '2. Carga de Dados de Exemplo (data.sql)',
                accentColor: 'indigo',
                sql: dataSql,
                setSql: setDataSql,
                mode: dataMode,
                setMode: setDataMode,
                file: dataFile,
                setFile: setDataFile,
                showEditor: showDataEditor,
                setShowEditor: setShowDataEditor,
                fileInputRef: dataInputRef,
              })}

              {/* 3. Gabarito Oficial (answer.sql) */}
              {renderSqlSection({
                id: 'answer',
                title: '3. Gabarito Oficial (answer.sql)',
                badge: 'Obrigatório incluir ORDER BY',
                accentColor: 'emerald',
                sql: answerSql,
                setSql: setAnswerSql,
                mode: answerMode,
                setMode: setAnswerMode,
                file: answerFile,
                setFile: setAnswerFile,
                showEditor: showAnswerEditor,
                setShowEditor: setShowAnswerEditor,
                fileInputRef: answerInputRef,
              })}
            </div>

            <button
              type="submit"
              disabled={isSubmitting || loading}
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
                  Salvar Questão
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
            {loading && <p role="status">Carregando questões...</p>}
            {!loading && questions.length === 0 && <p>Nenhuma questão cadastrada.</p>}
            {questions.map((q) => {
              const qCategories = q.categories || (q.category ? [q.category] : []);

              return (
                <div
                  key={q.id}
                  className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 break-words">
                      <span className="text-xs font-mono text-slate-400 font-bold">QUESTÃO #{q.id}</span>
                      <h3 className="text-base font-bold text-slate-900 dark:text-white mt-0.5">
                        {q.title}
                      </h3>
                    </div>

                    <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 shrink-0">
                      {{ PUBLISHED: 'Publicada', READY: 'Pronta', DRAFT: 'Rascunho', DELETING: 'Exclusão pendente' }[q.publishedStatus] || q.publishedStatus}
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

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-slate-200 dark:border-slate-800 text-sm">
                    <span className="text-sm text-slate-600 dark:text-slate-400 font-medium">
                      Dificuldade: <strong className="text-slate-900 dark:text-slate-200">{q.difficulty}</strong>
                    </span>

                    {q.publishedStatus === 'READY' && (
                      <button
                        onClick={() => handlePublish(q.id)}
                        disabled={pendingId !== null}
                        title="Publicar questão"
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950 disabled:opacity-50"
                      >
                        <Send className="w-4 h-4" />
                        Publicar
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(q.id)}
                      disabled={pendingId !== null}
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
