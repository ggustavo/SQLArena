import React, { useEffect, useState } from 'react';
import { Medal, Trophy, Crown, Sparkles, Award } from 'lucide-react';
import { getRanking } from '../services/rankingService';

export default function RankingPage({ currentUser }) {
  const [ranking, setRanking] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    getRanking()
      .then((data) => {
        if (active) setRanking(data);
      })
      .catch((err) => {
        if (active) setError(err.response?.data?.detail || 'Não foi possível carregar o ranking.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const top3 = ranking.slice(0, 3);

  const getPodiumBadge = (index) => {
    if (index === 0) {
      return {
        cardBg: 'bg-amber-500/10 dark:bg-amber-500/10 border-amber-300 dark:border-amber-600/50',
        badgeBg: 'bg-amber-500 text-white shadow-amber-500/30',
        icon: <Crown className="w-7 h-7 text-amber-500" />,
        label: '1º Lugar',
      };
    }
    if (index === 1) {
      return {
        cardBg: 'bg-slate-100 dark:bg-[#222731] border-slate-300 dark:border-slate-600/50',
        badgeBg: 'bg-slate-400 text-white shadow-slate-400/30',
        icon: <Medal className="w-7 h-7 text-slate-400" />,
        label: '2º Lugar',
      };
    }
    return {
      cardBg: 'bg-amber-700/10 dark:bg-amber-700/10 border-amber-600/30 dark:border-amber-700/50',
      badgeBg: 'bg-amber-700 text-white shadow-amber-700/30',
      icon: <Award className="w-7 h-7 text-amber-700" />,
      label: '3º Lugar',
    };
  };

  return (
    <div className="w-full max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-amber-500 text-white flex items-center justify-center shadow-md shadow-amber-500/20">
              <Trophy className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-slate-900 dark:text-white">
              Ranking Geral
            </h1>
          </div>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Acompanhe a pontuação e o progresso dos melhores participantes da plataforma
          </p>
        </div>
      </div>

      {loading ? (
        <div className="p-12 text-center text-slate-500 dark:text-slate-400">
          <div className="w-8 h-8 mx-auto border-3 border-indigo-600 border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-sm font-medium">Carregando classificação...</p>
        </div>
      ) : error ? (
        <div role="alert" className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 text-sm font-medium">
          {error}
        </div>
      ) : ranking.length === 0 ? (
        <div className="bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#323846] rounded-3xl p-12 text-center text-slate-500 dark:text-slate-400">
          <Sparkles className="w-10 h-10 mx-auto text-slate-400 mb-2 opacity-60" />
          <p className="font-semibold text-base text-slate-800 dark:text-slate-200">Nenhum participante ainda</p>
          <p className="text-sm">Resolva questões na Arena para ser o primeiro colocado!</p>
        </div>
      ) : (
        <>
          {/* Top 3 Podium Cards */}
          {top3.length > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {top3.map((user, index) => {
                const podium = getPodiumBadge(index);
                const isMe = user.id === currentUser?.id;

                return (
                  <div
                    key={user.id}
                    className={`relative rounded-3xl border p-6 text-center shadow-sm flex flex-col items-center justify-between transition hover:-translate-y-0.5 duration-200 ${podium.cardBg} ${
                      isMe ? 'ring-2 ring-indigo-500' : ''
                    }`}
                  >
                    <div className="space-y-3 w-full">
                      <div className="mx-auto flex items-center justify-center">
                        {podium.icon}
                      </div>

                      <div>
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold shadow-xs ${podium.badgeBg}`}>
                          {podium.label}
                        </span>
                      </div>

                      <div>
                        <h3 className="font-bold text-lg text-slate-900 dark:text-white truncate" title={user.name}>
                          {user.name}
                          {isMe && (
                            <span className="ml-1.5 text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                              (Você)
                            </span>
                          )}
                        </h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400">{user.email}</p>
                      </div>
                    </div>

                    <div className="mt-5 pt-4 border-t border-slate-200/60 dark:border-slate-700/60 w-full flex items-center justify-around text-xs">
                      <div>
                        <div className="font-extrabold text-base text-indigo-600 dark:text-indigo-400">
                          {user.score}
                        </div>
                        <div className="text-slate-500 dark:text-slate-400">Pontos (XP)</div>
                      </div>
                      <div className="h-6 w-px bg-slate-200 dark:bg-slate-700" />
                      <div>
                        <div className="font-extrabold text-base text-slate-800 dark:text-slate-200">
                          {user.solvedCount}
                        </div>
                        <div className="text-slate-500 dark:text-slate-400">Resolvidas</div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Leaderboard Table Card */}
          <div className="bg-white dark:bg-[#1f232b] border border-slate-200 dark:border-[#323846] rounded-3xl shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 dark:border-[#2d3340] flex items-center justify-between">
              <h2 className="font-bold text-base text-slate-900 dark:text-white">
                Tabela de Classificação
              </h2>
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                {ranking.length} participantes
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-[#2d3340] bg-slate-50/70 dark:bg-[#191c23]/60 text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wider font-bold">
                    <th className="py-3.5 px-6">Posição</th>
                    <th className="py-3.5 px-6">Participante</th>
                    <th className="py-3.5 px-6 text-center">Pontos (XP)</th>
                    <th className="py-3.5 px-6 text-center">Questões Resolvidas</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-[#2d3340]">
                  {ranking.map((user) => {
                    const isMe = user.id === currentUser?.id;

                    return (
                      <tr
                        key={user.id}
                        className={`transition ${
                          isMe
                            ? 'bg-indigo-50/60 dark:bg-indigo-950/40 font-medium'
                            : 'hover:bg-slate-50 dark:hover:bg-[#252a35]/50'
                        }`}
                      >
                        <td className="py-4 px-6">
                          <span
                            className={`inline-flex items-center justify-center w-7 h-7 rounded-xl font-bold text-xs ${
                              user.position === 1
                                ? 'bg-amber-100 dark:bg-amber-950/70 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700'
                                : user.position === 2
                                ? 'bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700'
                                : user.position === 3
                                ? 'bg-amber-900/10 dark:bg-amber-950/40 text-amber-800 dark:text-amber-400 border border-amber-800/30'
                                : 'text-slate-600 dark:text-slate-400'
                            }`}
                          >
                            #{user.position}
                          </span>
                        </td>
                        <td className="py-4 px-6">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 font-bold text-xs flex items-center justify-center shrink-0">
                              {user.name?.charAt(0).toUpperCase() || 'U'}
                            </div>
                            <div>
                              <div className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                <span>{user.name}</span>
                                {isMe && (
                                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-indigo-600 text-white">
                                    Você
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-slate-500 dark:text-slate-400">
                                {user.email}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-center font-bold text-indigo-600 dark:text-indigo-400">
                          {user.score} XP
                        </td>
                        <td className="py-4 px-6 text-center text-slate-700 dark:text-slate-300 font-medium">
                          {user.solvedCount}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
