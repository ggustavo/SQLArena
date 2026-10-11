import React, { useState, useRef, useEffect } from 'react';
import {
  Sun,
  Moon,
  Database,
  ChevronDown,
  ShieldCheck,
  LogOut,
  BookOpen,
  Layers,
  History,
  Flame,
  Coins,
  Trophy,
  UserRound,
  UsersRound,
  Activity,
} from 'lucide-react';
import UserAvatar from './UserAvatar';

export default function Navbar({
  user,
  onLogout,
  onNavigateHome,
  onOpenInstructorPanel,
  onOpenHistory,
  onOpenProfile,
  onOpenUsers,
  onOpenRanking,
  onOpenDynamoLogs,
  theme,
  onToggleTheme,
}) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isInstructor = user?.role === 'INSTRUCTOR' || user?.role === 'ADMIN';

  return (
    <>
      <header className="sticky top-0 z-40 w-full border-b border-slate-200 dark:border-[#2d3340] bg-white/95 dark:bg-[#1b1e26]/95 backdrop-blur px-6 lg:px-12 py-3.5 transition-colors">
        <div className="w-full flex items-center justify-between">
          {/* Brand Logo: Apenas uma cor e SEM subtítulo conforme instrução */}
          <div
            onClick={onNavigateHome}
            className="flex items-center gap-3 cursor-pointer select-none group"
          >
            <div className="w-10 h-10 rounded-2xl bg-indigo-600 dark:bg-indigo-500 text-white flex items-center justify-center font-bold text-base shadow-sm group-hover:scale-105 transition-transform">
              <Database className="w-5 h-5 text-white" />
            </div>
            <div className="font-black text-2xl tracking-tight text-slate-900 dark:text-white">
              SQLArena
            </div>
          </div>

          {/* Right Section: Apenas os 3 itens solicitados e o menu de perfil */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* 1. Mural de Questões */}
            <button
              type="button"
              onClick={onNavigateHome}
              title="Mural de Questões"
              className="flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-slate-100 dark:bg-[#252a35] hover:bg-slate-200 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#323946] text-slate-700 dark:text-slate-200 text-xs sm:text-sm font-semibold transition cursor-pointer"
            >
              <BookOpen className="w-4 h-4 text-indigo-500" />
              <span className="hidden sm:inline">Mural de Questões</span>
            </button>

            {/* 2. Ranking */}
            <button
              type="button"
              onClick={onOpenRanking}
              title="Ranking Geral de Pontuação"
              className="flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-slate-100 dark:bg-[#252a35] hover:bg-slate-200 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#323946] text-slate-700 dark:text-slate-200 text-xs sm:text-sm font-semibold transition cursor-pointer"
            >
              <Trophy className="w-4 h-4 text-amber-500" />
              <span className="hidden sm:inline">Ranking</span>
            </button>

            {/* 3. Histórico de Submissões */}
            <button
              type="button"
              onClick={onOpenHistory}
              title="Histórico de Submissões Completo"
              className="flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-slate-100 dark:bg-[#252a35] hover:bg-slate-200 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#323946] text-slate-700 dark:text-slate-200 text-xs sm:text-sm font-semibold transition cursor-pointer"
            >
              <History className="w-4 h-4 text-slate-600 dark:text-slate-300" />
              <span className="hidden sm:inline">Histórico de Submissões</span>
            </button>

            {/* User Profile Dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-2.5 p-1.5 pr-3 rounded-2xl bg-slate-100/80 dark:bg-[#252a35] hover:bg-slate-200/80 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#323946] transition cursor-pointer"
              >
                <UserAvatar
                  user={user}
                  className="w-8 h-8 rounded-full border border-slate-200 dark:border-[#353d4d]"
                  textClassName="text-xs font-bold"
                  fallbackBg="bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900"
                />
                <div className="hidden md:block text-left">
                  <div className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100 leading-tight">
                    {user?.name || 'Usuário'}
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">
                    {isInstructor ? 'Instrutor' : 'Aluno'}
                  </div>
                </div>
                <ChevronDown className="w-4 h-4 text-slate-400" />
              </button>

              {/* Dropdown Menu */}
              {dropdownOpen && (
                <div className="absolute right-0 mt-2 w-72 rounded-3xl bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#323846] shadow-2xl p-2.5 z-50 text-sm space-y-1 divide-y divide-slate-100 dark:divide-[#2d3340] animate-in fade-in duration-100">
                  {/* User Info Header */}
                  <div className="p-3 flex items-start gap-3">
                    <UserAvatar
                      user={user}
                      className="w-10 h-10 rounded-xl border border-slate-200 dark:border-[#353d4d]"
                      textClassName="text-sm font-bold"
                      fallbackBg="bg-indigo-600 text-white"
                    />
                    <div className="min-w-0 flex-1">
                      <div className="font-bold text-slate-900 dark:text-white text-base truncate">
                        {user?.name}
                      </div>
                      <div className="text-xs text-slate-500 truncate">{user?.email}</div>
                      {user?.university && (
                        <div className="text-[11px] text-indigo-600 dark:text-indigo-400 font-medium truncate mt-0.5">
                          {user.university}
                        </div>
                      )}
                      <div className="mt-2">
                        <span className="inline-block px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 dark:bg-[#282d37] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-[#353d4d]">
                          {isInstructor ? 'Perfil: Instrutor' : 'Perfil: Aluno'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Navigation Links: sem duplicar Mural de Questões e Ranking */}
                  <div className="pt-2 space-y-1">
                    {isInstructor && (
                      <button
                        onClick={() => {
                          onOpenInstructorPanel();
                          setDropdownOpen(false);
                        }}
                        className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282d37] font-medium transition text-left cursor-pointer"
                      >
                        <ShieldCheck className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                        <span>Painel do Instrutor</span>
                      </button>
                    )}
                    {isInstructor && (
                      <button
                        type="button"
                        onClick={() => {
                          onOpenUsers();
                          setDropdownOpen(false);
                        }}
                        className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282d37] font-medium transition text-left cursor-pointer"
                      >
                        <UsersRound className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                        <span>Gestão de Usuários</span>
                      </button>
                    )}
                    {isInstructor && onOpenDynamoLogs && (
                      <button
                        type="button"
                        onClick={() => {
                          onOpenDynamoLogs();
                          setDropdownOpen(false);
                        }}
                        className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282d37] font-medium transition text-left cursor-pointer"
                      >
                        <Activity className="w-4 h-4 text-indigo-500" />
                        <span>Logs do DynamoDB</span>
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => {
                        onOpenProfile();
                        setDropdownOpen(false);
                      }}
                      className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282d37] font-medium transition text-left cursor-pointer"
                    >
                      <UserRound className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                      <span>Editar Perfil</span>
                    </button>
                  </div>

                  {/* Botão de Tema Escuro / Claro */}
                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={onToggleTheme}
                      className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282d37] font-medium transition text-left cursor-pointer"
                    >
                      <div className="flex items-center gap-3">
                        {theme === 'dark' ? (
                          <Sun className="w-4 h-4 text-amber-400" />
                        ) : (
                          <Moon className="w-4 h-4 text-slate-600" />
                        )}
                        <span>Tema da Interface</span>
                      </div>
                      <span className="text-xs px-2 py-0.5 rounded-md bg-slate-100 dark:bg-[#282d37] text-slate-600 dark:text-slate-300 font-semibold uppercase">
                        {theme === 'dark' ? 'Escuro' : 'Claro'}
                      </span>
                    </button>
                  </div>

                  {/* Logout */}
                  <div className="pt-2">
                    <button
                      onClick={() => {
                        onLogout();
                        setDropdownOpen(false);
                      }}
                      className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 font-semibold transition text-left cursor-pointer"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Sair da Conta</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>
    </>
  );
}
