import React, { useEffect, useState } from 'react';
import { ArrowLeft, Search } from 'lucide-react';
import { getUsers, setUserRole } from '../services/userService';

export default function UserManagementPage({ currentUser, onBack }) {
  const [search, setSearch] = useState('');
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const results = await getUsers(search);
        if (active) { setUsers(results); setError(''); }
      } catch (err) {
        if (active) setError(err.response?.data?.detail || 'Não foi possível carregar os usuários.');
      } finally {
        if (active) setLoading(false);
      }
    }, 250);
    return () => { active = false; clearTimeout(timer); };
  }, [search]);

  async function changeRole(user) {
    const role = user.role === 'INSTRUCTOR' ? 'STUDENT' : 'INSTRUCTOR';
    setBusyId(user.id);
    setError('');
    try {
      const updated = await setUserRole(user.id, role);
      setUsers(items => items.map(item => item.id === updated.id ? updated : item));
    } catch (err) {
      setError(err.response?.data?.detail || 'Não foi possível alterar a permissão.');
    } finally {
      setBusyId(null);
    }
  }

  return <section className="w-full max-w-6xl mx-auto px-5 py-8 text-slate-900 dark:text-slate-100">
    <button type="button" onClick={onBack} className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-300 mb-6"><ArrowLeft size={18} /> Voltar</button>
    <div className="flex flex-wrap items-center justify-between gap-4 mb-6"><h1 className="text-2xl font-bold">Gestão de usuários</h1>
      <label className="relative w-full sm:w-72"><Search size={18} className="absolute left-3 top-3 text-slate-500" /><input type="search" aria-label="Buscar por nome ou e-mail" placeholder="Buscar usuário" value={search} onChange={e => setSearch(e.target.value)} className="w-full rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 py-2.5 pl-10 pr-3" /></label>
    </div>
    {error && <p role="alert" className="mb-4 text-sm text-rose-600">{error}</p>}
    {loading ? <p>Carregando usuários...</p> : users.length === 0 ? <p>Nenhum usuário encontrado.</p> :
      <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-slate-300 dark:border-slate-600"><tr><th className="py-3 pr-4">Nome</th><th className="py-3 pr-4">E-mail</th><th className="py-3 pr-4">Papel</th><th className="py-3">Permissão</th></tr></thead><tbody>{users.map(user => <tr key={user.id} className="border-b border-slate-200 dark:border-slate-700"><td className="py-3 pr-4 font-medium">{user.name}</td><td className="py-3 pr-4">{user.email}</td><td className="py-3 pr-4">{user.role === 'INSTRUCTOR' ? 'Instrutor' : 'Aluno'}</td><td className="py-3"><button type="button" disabled={busyId === user.id || user.id === currentUser.id} onClick={() => changeRole(user)} className="text-indigo-700 dark:text-indigo-300 font-semibold disabled:text-slate-400" title={user.id === currentUser.id ? 'Você não pode remover sua própria permissão' : undefined}>{busyId === user.id ? 'Salvando...' : user.role === 'INSTRUCTOR' ? 'Revogar' : 'Conceder'}</button></td></tr>)}</tbody></table></div>}
  </section>;
}
