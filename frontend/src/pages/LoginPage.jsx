import React, { useState } from 'react';
import { Database, Lock, Mail, ArrowRight, ShieldCheck, GraduationCap, UserRound } from 'lucide-react';
import { login, register } from '../services/authService';

export default function LoginPage({ onLoginSuccess }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [registerMode, setRegisterMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    if (!email.trim() || !password || (registerMode && !name.trim())) {
      setError('Preencha todos os campos.');
      return;
    }
    if (registerMode && password.length < 8) {
      setError('A senha deve ter pelo menos 8 caracteres.');
      return;
    }
    setError(null);
    setLoading(true);

    try {
      const result = registerMode
        ? await register(name.trim(), email.trim(), password)
        : await login(email, password);
      onLoginSuccess(result.user);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Não foi possível continuar.');
    } finally {
      setLoading(false);
    }
  };

  const fillAccount = (selectedEmail) => {
    setEmail(selectedEmail);
    setPassword('123456');
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-6 bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100">
      <div className="w-full max-w-lg space-y-8">
        {/* Brand Header */}
        <div className="text-center space-y-3">
          <div className="inline-flex w-16 h-16 rounded-3xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-amber-500 text-white items-center justify-center shadow-xl shadow-indigo-600/25">
            <Database className="w-8 h-8" />
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-slate-900 dark:text-white">
            SQLArena
          </h1>
          <p className="text-base text-slate-600 dark:text-slate-400">
            Ambiente prático para aprendizado e avaliação de consultas SQL
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 sm:p-10 shadow-xl space-y-6">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="flex border-b border-slate-200 dark:border-slate-700" role="tablist" aria-label="Acesso">
              <button type="button" role="tab" aria-selected={!registerMode} onClick={() => { setRegisterMode(false); setError(null); }} className={`flex-1 py-2 text-sm font-semibold ${!registerMode ? 'border-b-2 border-indigo-600 text-indigo-700 dark:text-indigo-300' : 'text-slate-500'}`}>Entrar</button>
              <button type="button" role="tab" aria-selected={registerMode} onClick={() => { setRegisterMode(true); setError(null); }} className={`flex-1 py-2 text-sm font-semibold ${registerMode ? 'border-b-2 border-indigo-600 text-indigo-700 dark:text-indigo-300' : 'text-slate-500'}`}>Criar nova conta</button>
            </div>
            {error && (
              <div className="p-4 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-sm font-medium">
                {error}
              </div>
            )}

            {registerMode && <div className="space-y-2">
              <label htmlFor="register-name" className="text-sm font-semibold text-slate-800 dark:text-slate-200">Nome</label>
              <div className="relative">
                <UserRound className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
                <input id="register-name" type="text" required maxLength={100} autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} className="w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl" />
              </div>
            </div>}

            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                E-mail
              </label>
              <div className="relative">
                <Mail className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  placeholder="seu.email@sqlarena.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl text-base text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                Senha
              </label>
              <div className="relative">
                <Lock className="w-5 h-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  minLength={registerMode ? 8 : undefined}
                  autoComplete={registerMode ? 'new-password' : 'current-password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-xl text-base text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-base transition shadow-md shadow-indigo-600/25 flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  {registerMode ? 'Criar conta' : 'Entrar na Plataforma'}
                  <ArrowRight className="w-5 h-5" />
                </>
              )}
            </button>
          </form>

          {/* Quick Credential Pre-fill Helpers */}
          {!registerMode && <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider text-center">
              Preencher dados para teste:
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => fillAccount('aluno@sqlarena.com')}
                className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-indigo-500 bg-slate-50 dark:bg-slate-950 text-left transition"
              >
                <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 font-semibold text-xs mb-1">
                  <GraduationCap className="w-4 h-4" />
                  <span>Aluno</span>
                </div>
                <div className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">
                  aluno@sqlarena.com
                </div>
              </button>

              <button
                type="button"
                onClick={() => fillAccount('instrutor@sqlarena.com')}
                className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-purple-500 bg-slate-50 dark:bg-slate-950 text-left transition"
              >
                <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400 font-semibold text-xs mb-1">
                  <ShieldCheck className="w-4 h-4" />
                  <span>Instrutor / Criador</span>
                </div>
                <div className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">
                  instrutor@sqlarena.com
                </div>
              </button>
            </div>
          </div>}
        </div>

        <div className="text-center text-sm text-slate-500">
          SQLArena
        </div>
      </div>
    </div>
  );
}
