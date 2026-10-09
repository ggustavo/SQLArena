import React, { useState } from 'react';
import { ArrowLeft, Save } from 'lucide-react';
import { updateProfile } from '../services/authService';

export default function ProfilePage({ user, onBack, onUpdated }) {
  const [name, setName] = useState(user.name);
  const [email, setEmail] = useState(user.email);
  const [currentPassword, setCurrentPassword] = useState('');
  const [password, setPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  async function save(event) {
    event.preventDefault();
    setMessage('');
    setError('');
    if (!name.trim()) { setError('Informe seu nome.'); return; }
    if (password && (!currentPassword || password.length < 8)) {
      setError('Informe a senha atual e uma nova senha com pelo menos 8 caracteres.');
      return;
    }
    setSaving(true);
    try {
      const updated = await updateProfile({
        name: name.trim(), email: email.trim(),
        ...(password ? { password, currentPassword } : {}),
      });
      onUpdated(updated);
      setCurrentPassword('');
      setPassword('');
      setMessage('Perfil atualizado.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Não foi possível atualizar o perfil.');
    } finally {
      setSaving(false);
    }
  }

  return <section className="w-full max-w-2xl mx-auto px-5 py-8 text-slate-900 dark:text-slate-100">
    <button type="button" onClick={onBack} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 mb-6"><ArrowLeft size={18} /> Voltar</button>
    <h1 className="text-2xl font-bold mb-6">Editar perfil</h1>
    <form onSubmit={save} className="space-y-5">
      <label className="block text-sm font-medium">Nome<input type="text" required maxLength={100} value={name} onChange={e => setName(e.target.value)} className="mt-1 block w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 p-3" /></label>
      <label className="block text-sm font-medium">E-mail<input type="email" required value={email} onChange={e => setEmail(e.target.value)} className="mt-1 block w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 p-3" /></label>
      <div className="border-t border-slate-200 dark:border-slate-700 pt-5 space-y-5">
        <h2 className="font-semibold">Alterar senha</h2>
        <label className="block text-sm font-medium">Senha atual<input type="password" autoComplete="current-password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} className="mt-1 block w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 p-3" /></label>
        <label className="block text-sm font-medium">Nova senha<input type="password" autoComplete="new-password" minLength={8} value={password} onChange={e => setPassword(e.target.value)} className="mt-1 block w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 p-3" /></label>
      </div>
      {error && <p role="alert" className="text-sm text-rose-600">{error}</p>}
      {message && <p role="status" className="text-sm text-emerald-700">{message}</p>}
      <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded bg-indigo-600 px-4 py-2.5 font-semibold text-white disabled:opacity-60"><Save size={18} />{saving ? 'Salvando...' : 'Salvar alterações'}</button>
    </form>
  </section>;
}
