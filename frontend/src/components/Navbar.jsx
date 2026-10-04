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
} from 'lucide-react';
import SubmissionQueueModal from './SubmissionQueueModal';

export default function Navbar({
  user,
  onLogout,
  onNavigateHome,
  onOpenInstructorPanel,
  onOpenHistory,
  theme,
  onToggleTheme,
}) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [queueModalOpen, setQueueModalOpen] = useState(false);
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

          {/* Right Section: Instructor Link, Queue Modal Trigger, User Profile */}
          <div className="flex items-center gap-3 sm:gap-4">
            {/* Quick link to Instructor Panel if user has instructor role */}
            {isInstructor && (
              <button
                onClick={onOpenInstructorPanel}
                className="hidden sm:flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 dark:bg-[#252a35] border border-slate-300/80 dark:border-[#353d4d] text-slate-700 dark:text-slate-200 font-semibold text-xs sm:text-sm hover:bg-slate-200 dark:hover:bg-[#2e3442] transition"
              >
                <ShieldCheck className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                <span>Painel do Instrutor</span>
              </button>
            )}

            {/* BOTÃO DA FILA DE SUBMISSÕES (À esquerda do perfil do usuário) */}
            <button
              type="button"
              onClick={() => setQueueModalOpen(true)}
              title="Fila de Submissões Recentes"
              className="relative flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-slate-100 dark:bg-[#252a35] hover:bg-slate-200 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#323946] text-slate-700 dark:text-slate-200 transition group"
            >
              <div className="relative">
                <Layers className="w-4 h-4 text-slate-600 dark:text-slate-300 group-hover:rotate-12 transition-transform" />
                {/* Indicador sutil de atividade */}
                <span className="absolute -top-1 -right-1 flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
              </div>
              <span className="text-xs sm:text-sm font-semibold hidden md:inline">
                Fila de Submissões
              </span>
            </button>

            {/* Pílulas integradas de Streak e XP ao lado do perfil */}
            <div className="hidden sm:flex items-center gap-2">
              {/* Streak Pill */}
              <div
                title="Sequência de dias praticando"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-50 dark:bg-amber-950/60 border border-amber-200/90 dark:border-amber-800/80 text-amber-800 dark:text-amber-200 text-xs font-bold shadow-2xs"
              >
                <Flame className="w-3.5 h-3.5 fill-amber-500 text-amber-500 animate-pulse" />
                <span>{user?.streakDays || 4} dias</span>
              </div>

              {/* Pontos Pill */}
              <div
                title="Pontos acumulados na plataforma"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200/90 dark:border-indigo-800/80 text-indigo-800 dark:text-indigo-200 text-xs font-bold shadow-2xs"
              >
                <Coins className="w-3.5 h-3.5 text-indigo-500" />
                <span>{user?.score || 180} pontos</span>
              </div>
            </div>

            {/* User Profile Dropdown */}
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setDropdownOpen(!dropdownOpen)}
                className="flex items-center gap-2.5 p-1.5 pr-3 rounded-2xl bg-slate-100/80 dark:bg-[#252a35] hover:bg-slate-200/80 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#323946] transition"
              >
                <div className="w-8 h-8 rounded-full bg-slate-800 dark:bg-slate-200 text-white dark:text-slate-900 font-bold flex items-center justify-center text-xs shadow-xs">
                  {user?.name?.charAt(0) || 'G'}
                </div>
                <div className="hidden md:block text-left">
                  <div className="text-xs sm:text-sm font-bold text-slate-900 dark:text-slate-100 leading-tight">
                    {user?.name || 'Gustavo Santos'}
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
                  <div className="p-3">
                    <div className="font-bold text-slate-900 dark:text-white text-base">
                      {user?.name}
                    </div>
                    <div className="text-xs text-slate-500 truncate">{user?.email}</div>
                    <div className="mt-2.5">
                      <span className="inline-block px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-100 dark:bg-[#282d37] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-[#353d4d]">
                        {isInstructor ? 'Perfil: Instrutor' : 'Perfil: Aluno'}
                      </span>
                    </div>
                  </div>

                  {/* Navigation Links */}
                  <div className="pt-2 space-y-1">
                    <button
                      onClick={() => {
                        onNavigateHome();
                        setDropdownOpen(false);
                      }}
                      className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282d37] font-medium transition text-left"
                    >
                      <BookOpen className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                      <span>Mural de Questões</span>
                    </button>

                    <button
                      onClick={() => {
                        onOpenHistory();
                        setDropdownOpen(false);
                      }}
                      className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282d37] font-medium transition text-left"
                    >
                      <History className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                      <span>Histórico de Submissões</span>
                    </button>

                    {isInstructor && (
                      <button
                        onClick={() => {
                          onOpenInstructorPanel();
                          setDropdownOpen(false);
                        }}
                        className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282d37] font-medium transition text-left"
                      >
                        <ShieldCheck className="w-4 h-4 text-slate-500 dark:text-slate-400" />
                        <span>Painel do Instrutor</span>
                      </button>
                    )}
                  </div>

                  {/* Botão de Tema Escuro / Claro */}
                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={onToggleTheme}
                      className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-[#282d37] font-medium transition text-left"
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
                      className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 font-semibold transition text-left"
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

      {/* Popover / Modal da Fila de Submissões */}
      <SubmissionQueueModal
        isOpen={queueModalOpen}
        onClose={() => setQueueModalOpen(false)}
        onOpenHistory={() => {
          setQueueModalOpen(false);
          onOpenHistory();
        }}
      />
    </>
  );
}
