import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import QuestionDashboard from './pages/QuestionDashboard';
import ArenaPage from './pages/ArenaPage';
import ProfessorPage from './pages/ProfessorPage';
import HistoryModal from './components/HistoryModal';
import { getCurrentUser, logout } from './services/authService';
import { getQuestions } from './services/questionService';

export default function App() {
  const [user, setUser] = useState(() => getCurrentUser());
  // Padrão do sistema: tema branco como solicitado pelo usuário!
  const [theme, setTheme] = useState('light');
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard' | 'arena' | 'instructor'
  const [selectedQuestion, setSelectedQuestion] = useState(null);
  const [arenaInitialSql, setArenaInitialSql] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);

  // Aplica classe dark ou light no HTML com tons suaves de cinza (não preto absoluto)
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      document.body.className = 'bg-[#16181e] text-slate-100 antialiased min-h-screen';
    } else {
      document.documentElement.classList.remove('dark');
      document.body.className = 'bg-[#f8fafc] text-slate-900 antialiased min-h-screen';
    }
  }, [theme]);

  // Carrega as questões
  useEffect(() => {
    async function load() {
      const data = await getQuestions(user?.role || 'STUDENT');
      setQuestions(data);
    }
    if (currentView === 'dashboard') load().catch(() => setQuestions([]));
  }, [user, currentView]);

  const toggleTheme = () => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'));
  };

  const handleLoginSuccess = (authenticatedUser) => {
    setUser(authenticatedUser);
    setCurrentView('dashboard');
  };

  const handleLogout = async () => {
    await logout();
    setUser(null);
    setCurrentView('dashboard');
  };

  const handleSelectQuestion = (q, customSql = null) => {
    setSelectedQuestion(q);
    setArenaInitialSql(customSql || null);
    setCurrentView('arena');
  };

  // Carrega consulta do histórico diretamente no editor sem perder o contexto
  const handleLoadSqlIntoEditor = (questionId, customSql) => {
    const targetQ = questions.find((q) => q.id === Number(questionId));
    if (targetQ) {
      setSelectedQuestion(targetQ);
    }
    setArenaInitialSql(customSql);
    setCurrentView('arena');
    setIsHistoryModalOpen(false);
  };

  const handleAddPoints = (earnedPoints) => {
    setUser((prev) => ({
      ...prev,
      score: (prev.score || 0) + earnedPoints,
      solvedCount: (prev.solvedCount || 0) + 1,
    }));

    if (selectedQuestion) {
      setQuestions((prevList) =>
        prevList.map((item) =>
          item.id === selectedQuestion.id ? { ...item, status: 'SOLVED' } : item
        )
      );
    }
  };

  // Se não estiver autenticado, exibe a tela de Login
  if (!user) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen flex flex-col font-sans transition-colors duration-200">
      <Navbar
        user={user}
        theme={theme}
        onToggleTheme={toggleTheme}
        onLogout={handleLogout}
        onNavigateHome={() => setCurrentView('dashboard')}
        onOpenInstructorPanel={() => setCurrentView('instructor')}
        onOpenHistory={() => setIsHistoryModalOpen(true)}
      />

      <main className="flex-1 w-full">
        {currentView === 'dashboard' && (
          <QuestionDashboard
            user={user}
            questions={questions}
            onSelectQuestion={handleSelectQuestion}
          />
        )}

        {currentView === 'arena' && selectedQuestion && (
          <ArenaPage
            question={selectedQuestion}
            initialSql={arenaInitialSql}
            user={user}
            onBack={() => setCurrentView('dashboard')}
            onAddPoints={handleAddPoints}
          />
        )}

        {currentView === 'instructor' && (
          <ProfessorPage onBack={() => setCurrentView('dashboard')} />
        )}
      </main>

      {/* Modal de Histórico de Submissões: Abre sobre qualquer tela sem perder o contexto */}
      <HistoryModal
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        onLoadSqlIntoEditor={handleLoadSqlIntoEditor}
        currentQuestionId={currentView === 'arena' ? selectedQuestion?.id : null}
      />
    </div>
  );
}
