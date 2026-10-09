import React, { useEffect, useState } from 'react';
import { Medal, Trophy } from 'lucide-react';
import { getRanking } from '../services/rankingService';

export default function RankingPage({ currentUser }) {
  const [ranking, setRanking] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    getRanking().then(data => { if (active) setRanking(data); })
      .catch(err => { if (active) setError(err.response?.data?.detail || 'Não foi possível carregar o ranking.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const medalColors = ['text-amber-500', 'text-slate-400', 'text-orange-600'];
  return <section className="w-full max-w-5xl mx-auto px-5 py-8 text-slate-900 dark:text-slate-100">
    <h1 className="flex items-center gap-3 text-2xl font-bold mb-6"><Trophy className="text-amber-500" /> Ranking geral</h1>
    {loading ? <p>Carregando ranking...</p> : error ? <p role="alert" className="text-rose-600">{error}</p> : ranking.length === 0 ? <p>Ainda não há participantes.</p> : <>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">{ranking.slice(0, 3).map((user, index) => <div key={user.id} className="border border-slate-200 dark:border-slate-700 rounded-md bg-white dark:bg-slate-800 p-5 text-center">
        <Medal size={30} className={`mx-auto mb-2 ${medalColors[index]}`} /><p className="font-bold text-lg break-words">{user.name}</p><p className="text-sm text-slate-500 dark:text-slate-300">{user.score} XP · {user.solvedCount} resolvidas</p>
      </div>)}</div>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="border-b border-slate-300 dark:border-slate-600"><tr><th className="py-3">Posição</th><th>Nome</th><th>XP</th><th>Resolvidas</th></tr></thead><tbody>{ranking.map(user => <tr key={user.id} className={`border-b border-slate-200 dark:border-slate-700 ${user.id === currentUser?.id ? 'bg-indigo-50 dark:bg-indigo-950/40' : ''}`}><td className="py-3 font-bold">#{user.position}</td><td className="pr-4">{user.name}</td><td className="font-semibold">{user.score}</td><td>{user.solvedCount}</td></tr>)}</tbody></table></div>
    </>}
  </section>;
}
