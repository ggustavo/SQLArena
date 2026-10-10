import React, { useState } from 'react';
import { ArrowLeft, Save, UserRound, Mail, Lock, ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';
import { updateProfile } from '../services/authService';

export default function ProfilePage({ user, onBack, onUpdated }) {
  const [name, setName] = useState(user.name || '');
  const [email, setEmail] = useState(user.email || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [password, setPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const isInstructor = user.role === 'INSTRUCTOR' || user.role === 'ADMIN';

  async function save(event) {
    event.preventDefault();
    setMessage('');
    setError('');
    if (!name.trim()) {
      setError('Informe seu nome.');
      return;
    }
    if (password && (!currentPassword || password.length < 8)) {
      setError('Informe a senha atual e uma nova senha com pelo menos 8 caracteres.');
      return;
    }
    setSaving(true);
    try {
      const updated = await updateProfile({
        name: name.trim(),
        email: email.trim(),
        ...(password ? { password, currentPassword } : {}),
      });
      onUpdated(updated);
      setCurrentPassword('');
      setPassword('');
      setMessage('Perfil atualizado com sucesso!');
    } catch (err) {
      setError(err.response?.data?.detail || 'Não foi possível atualizar o perfil.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="w-full max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Top bar with Back Button */}
      <div className="mb-6">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-100 dark:bg-[#252a35] hover:bg-slate-200 dark:hover:bg-[#2e3442] border border-slate-200 dark:border-[#323946] text-slate-700 dark:text-slate-200 text-xs sm:text-sm font-semibold transition cursor-pointer"
        >
          <ArrowLeft size={16} /> Voltar ao Painel
        </button>
      </div>

      {/* Main Profile Card */}
      <div className="bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#323846] rounded-3xl p-6 sm:p-10 shadow-sm space-y-8">
        {/* Header / Avatar info */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100 dark:border-[#2d3340]">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-indigo-600 dark:bg-indigo-500 text-white font-black text-2xl flex items-center justify-center shadow-md shadow-indigo-600/20">
              {name.charAt(0).toUpperCase() || 'U'}
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
                Meu Perfil
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Gerencie suas informações pessoais e credenciais de acesso
              </p>
            </div>
          </div>

          <div>
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200/80 dark:border-indigo-800/80">
              {isInstructor ? (
                <>
                  <ShieldCheck size={14} /> Instrutor
                </>
              ) : (
                <>
                  <UserRound size={14} /> Aluno
                </>
              )}
            </span>
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

        {message && (
          <div
            role="status"
            className="flex items-center gap-3 p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-900/60 text-emerald-800 dark:text-emerald-200 text-sm font-medium animate-in fade-in"
          >
            <CheckCircle2 size={18} className="shrink-0 text-emerald-600 dark:text-emerald-400" />
            <span>{message}</span>
          </div>
        )}

        <form onSubmit={save} className="space-y-6">
          <div className="space-y-4">
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Dados Pessoais</h2>

            <div className="space-y-1.5">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                Nome Completo
              </label>
              <div className="relative">
                <UserRound size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  required
                  maxLength={100}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-200 dark:border-[#353d4d] bg-slate-50 dark:bg-[#16181e] text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
                  placeholder="Seu nome"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                E-mail
              </label>
              <div className="relative">
                <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-200 dark:border-[#353d4d] bg-slate-50 dark:bg-[#16181e] text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
                  placeholder="seu.email@dominio.com"
                />
              </div>
            </div>
          </div>

          {/* Change password section */}
          <div className="pt-6 border-t border-slate-100 dark:border-[#2d3340] space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">Alterar Senha</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Deixe em branco se não desejar alterar sua senha atual.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                  Senha Atual
                </label>
                <div className="relative">
                  <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="password"
                    autoComplete="current-password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-200 dark:border-[#353d4d] bg-slate-50 dark:bg-[#16181e] text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                  Nova Senha
                </label>
                <div className="relative">
                  <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="password"
                    autoComplete="new-password"
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-200 dark:border-[#353d4d] bg-slate-50 dark:bg-[#16181e] text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
                    placeholder="Mínimo 8 caracteres"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="pt-4 flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-sm shadow-md shadow-indigo-600/25 transition cursor-pointer disabled:opacity-50"
            >
              <Save size={18} />
              {saving ? 'Salvando...' : 'Salvar Alterações'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
