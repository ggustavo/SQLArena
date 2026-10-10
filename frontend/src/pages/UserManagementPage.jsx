import React, { useEffect, useState } from 'react';
import { ArrowLeft, Search, ShieldCheck, UserRound, UsersRound, AlertCircle, CheckCircle2 } from 'lucide-react';
import { getUsers, setUserRole } from '../services/userService';

export default function UserManagementPage({ currentUser, onBack }) {
  const [search, setSearch] = useState('');
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    let active = true;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const results = await getUsers(search);
        if (active) {
          setUsers(results);
          setError('');
        }
      } catch (err) {
        if (active) setError(err.response?.data?.detail || 'Não foi possível carregar os usuários.');
      } finally {
        if (active) setLoading(false);
      }
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [search]);

  async function changeRole(user) {
    const nextRole = user.role === 'INSTRUCTOR' ? 'STUDENT' : 'INSTRUCTOR';
    setBusyId(user.id);
    setError('');
    setSuccessMsg('');
    try {
      const updated = await setUserRole(user.id, nextRole);
      setUsers((items) => items.map((item) => (item.id === updated.id ? updated : item)));
      setSuccessMsg(
        `Permissão de ${updated.name} alterada para ${
          updated.role === 'INSTRUCTOR' ? 'Instrutor' : 'Aluno'
        }.`
      );
    } catch (err) {
      setError(err.response?.data?.detail || 'Não foi possível alterar a permissão.');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="w-full max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Back button */}
      <div>
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 dark:bg-[#252a35] hover:bg-slate-200 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#323946] text-slate-700 dark:text-slate-200 text-xs sm:text-sm font-semibold transition cursor-pointer"
        >
          <ArrowLeft size={16} /> Voltar ao Painel
        </button>
      </div>

      {/* Header with Title and Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-indigo-600 dark:bg-indigo-500 text-white flex items-center justify-center shadow-md shadow-indigo-600/20">
              <UsersRound className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 dark:text-white">
              Gestão de Usuários
            </h1>
          </div>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Gerencie os acessos e permissões de alunos e instrutores na plataforma
          </p>
        </div>

        {/* Search bar */}
        <div className="relative w-full sm:w-80">
          <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            aria-label="Buscar por nome ou e-mail"
            placeholder="Buscar por nome ou e-mail..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-2xl border border-slate-200 dark:border-[#353d4d] bg-white dark:bg-[#1f232b] text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition shadow-2xs"
          />
        </div>
      </div>

      {/* Feedback Alerts */}
      {error && (
        <div
          role="alert"
          className="flex items-center gap-3 p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 text-sm font-medium animate-in fade-in"
        >
          <AlertCircle size={18} className="shrink-0 text-rose-600 dark:text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div
          role="status"
          className="flex items-center gap-3 p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-900/60 text-emerald-800 dark:text-emerald-200 text-sm font-medium animate-in fade-in"
        >
          <CheckCircle2 size={18} className="shrink-0 text-emerald-600 dark:text-emerald-400" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Users Table Card */}
      <div className="bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#323846] rounded-3xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-slate-500 dark:text-slate-400">
            <div className="w-8 h-8 mx-auto border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm font-medium">Buscando usuários...</p>
          </div>
        ) : users.length === 0 ? (
          <div className="p-12 text-center text-slate-500 dark:text-slate-400">
            <p className="font-semibold text-base text-slate-800 dark:text-slate-200">
              Nenhum usuário encontrado
            </p>
            <p className="text-sm mt-1">
              {search ? 'Tente buscar com outro termo.' : 'Cadastre novos alunos para gerenciá-los.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-[#2d3340] bg-slate-50/70 dark:bg-[#191c23]/60 text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wider font-bold">
                  <th className="py-3.5 px-6">Usuário</th>
                  <th className="py-3.5 px-6">E-mail</th>
                  <th className="py-3.5 px-6">Perfil Atual</th>
                  <th className="py-3.5 px-6 text-right">Permissões</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-[#2d3340]">
                {users.map((user) => {
                  const isCurrent = user.id === currentUser?.id;
                  const isInstructor = user.role === 'INSTRUCTOR' || user.role === 'ADMIN';

                  return (
                    <tr
                      key={user.id}
                      className={`transition ${
                        isCurrent
                          ? 'bg-indigo-50/50 dark:bg-indigo-950/30'
                          : 'hover:bg-slate-50 dark:hover:bg-[#252a35]/50'
                      }`}
                    >
                      <td className="py-4 px-6">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-2xl bg-indigo-100 dark:bg-indigo-950/80 text-indigo-700 dark:text-indigo-300 font-bold text-xs flex items-center justify-center shrink-0 border border-indigo-200/60 dark:border-indigo-800/60">
                            {user.name?.charAt(0).toUpperCase() || 'U'}
                          </div>
                          <div>
                            <div className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                              <span>{user.name}</span>
                              {isCurrent && (
                                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-600 text-white">
                                  Você
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-slate-500 dark:text-slate-400">
                              ID: #{user.id}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-6 text-slate-600 dark:text-slate-300 font-medium">
                        {user.email}
                      </td>

                      <td className="py-4 px-6">
                        <span
                          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border ${
                            isInstructor
                              ? 'bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800/80'
                              : 'bg-slate-100 dark:bg-[#252a35] text-slate-700 dark:text-slate-300 border-slate-200 dark:border-[#353d4d]'
                          }`}
                        >
                          {isInstructor ? (
                            <>
                              <ShieldCheck size={13} className="text-purple-600 dark:text-purple-400" />
                              Instrutor
                            </>
                          ) : (
                            <>
                              <UserRound size={13} className="text-slate-500" />
                              Aluno
                            </>
                          )}
                        </span>
                      </td>

                      <td className="py-4 px-6 text-right">
                        {isCurrent ? (
                          <span
                            className="text-xs font-semibold text-slate-400 cursor-not-allowed"
                            title="Você não pode alterar seu próprio perfil"
                          >
                            Não editável
                          </span>
                        ) : (
                          <button
                            type="button"
                            disabled={busyId === user.id}
                            onClick={() => changeRole(user)}
                            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer disabled:opacity-50 ${
                              isInstructor
                                ? 'bg-rose-50 hover:bg-rose-100 dark:bg-rose-950/60 dark:hover:bg-rose-900/60 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-900/60'
                                : 'bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/60 dark:hover:bg-indigo-900/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/80'
                            }`}
                          >
                            {busyId === user.id
                              ? 'Salvando...'
                              : isInstructor
                              ? 'Tornar Aluno'
                              : 'Promover a Instrutor'}
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
