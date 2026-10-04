import React from 'react';
import {
  Filter,
  Fingerprint,
  FunctionSquare,
  Calendar,
  Type,
  GitMerge,
  PieChart,
  Workflow,
  SlidersHorizontal,
  Boxes,
  Combine,
  Split,
  Tag,
} from 'lucide-react';

export const CATEGORY_META = {
  'Filtragem': {
    icon: Filter,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-50 dark:bg-blue-950/60',
    border: 'border-blue-200 dark:border-blue-800/80',
    dot: 'bg-blue-500',
    displayName: 'Filtragem',
  },
  'Distintos': {
    icon: Fingerprint,
    color: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-950/60',
    border: 'border-emerald-200 dark:border-emerald-800/80',
    dot: 'bg-emerald-500',
    displayName: 'Distintos',
  },
  'Funções': {
    icon: FunctionSquare,
    color: 'text-violet-600 dark:text-violet-400',
    bg: 'bg-violet-50 dark:bg-violet-950/60',
    border: 'border-violet-200 dark:border-violet-800/80',
    dot: 'bg-violet-500',
    displayName: 'Funções',
  },
  'Datas': {
    icon: Calendar,
    color: 'text-teal-600 dark:text-teal-400',
    bg: 'bg-teal-50 dark:bg-teal-950/60',
    border: 'border-teal-200 dark:border-teal-800/80',
    dot: 'bg-teal-500',
    displayName: 'Datas',
  },
  'Texto': {
    icon: Type,
    color: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-950/60',
    border: 'border-amber-200 dark:border-amber-800/80',
    dot: 'bg-amber-500',
    displayName: 'Texto',
  },
  'JOINs': {
    icon: GitMerge,
    color: 'text-purple-600 dark:text-purple-400',
    bg: 'bg-purple-50 dark:bg-purple-950/60',
    border: 'border-purple-200 dark:border-purple-800/80',
    dot: 'bg-purple-500',
    displayName: 'JOINs',
  },
  'Agrupamento': {
    icon: PieChart,
    color: 'text-orange-600 dark:text-orange-400',
    bg: 'bg-orange-50 dark:bg-orange-950/60',
    border: 'border-orange-200 dark:border-orange-800/80',
    dot: 'bg-orange-500',
    displayName: 'Agrupamento',
  },
  'Subconsultas': {
    icon: Workflow,
    color: 'text-cyan-600 dark:text-cyan-400',
    bg: 'bg-cyan-50 dark:bg-cyan-950/60',
    border: 'border-cyan-200 dark:border-cyan-800/80',
    dot: 'bg-cyan-500',
    displayName: 'Subconsultas',
  },
  'Janelas': {
    icon: SlidersHorizontal,
    color: 'text-pink-600 dark:text-pink-400',
    bg: 'bg-pink-50 dark:bg-pink-950/60',
    border: 'border-pink-200 dark:border-pink-800/80',
    dot: 'bg-pink-500',
    displayName: 'Janelas',
  },
  'CTEs': {
    icon: Boxes,
    color: 'text-indigo-600 dark:text-indigo-400',
    bg: 'bg-indigo-50 dark:bg-indigo-950/60',
    border: 'border-indigo-200 dark:border-indigo-800/80',
    dot: 'bg-indigo-500',
    displayName: 'CTEs',
  },
  'Conjuntos': {
    icon: Combine,
    color: 'text-lime-600 dark:text-lime-400',
    bg: 'bg-lime-50 dark:bg-lime-950/60',
    border: 'border-lime-200 dark:border-lime-800/80',
    dot: 'bg-lime-500',
    displayName: 'Conjuntos',
  },
  'Condicional': {
    icon: Split,
    color: 'text-rose-600 dark:text-rose-400',
    bg: 'bg-rose-50 dark:bg-rose-950/60',
    border: 'border-rose-200 dark:border-rose-800/80',
    dot: 'bg-rose-500',
    displayName: 'Condicional',
  },
};

/**
 * Retorna os metadados visuais de uma categoria, garantindo:
 * - Ícone grande de alta relação semântica
 * - Nome estritamente de 1 palavra
 * - Cores e bordas harmônicas
 */
export function getCategoryMeta(name) {
  if (!name) {
    return {
      icon: Tag,
      color: 'text-slate-600 dark:text-slate-400',
      bg: 'bg-slate-100 dark:bg-[#252a35]',
      border: 'border-slate-200 dark:border-[#333a46]',
      dot: 'bg-slate-400',
      displayName: 'Geral',
    };
  }

  // Busca exata
  if (CATEGORY_META[name]) {
    return { ...CATEGORY_META[name] };
  }

  // Mapeamentos de compatibilidade para aliases antigos
  const clean = name.toLowerCase().trim();
  if (clean.includes('join')) return { ...CATEGORY_META['JOINs'] };
  if (clean.includes('agrup')) return { ...CATEGORY_META['Agrupamento'] };
  if (clean.includes('sub')) return { ...CATEGORY_META['Subconsultas'] };
  if (clean.includes('janela') || clean.includes('window')) return { ...CATEGORY_META['Janelas'] };
  if (clean.includes('cte') || clean.includes('with')) return { ...CATEGORY_META['CTEs'] };
  if (clean.includes('conjunt') || clean.includes('union')) return { ...CATEGORY_META['Conjuntos'] };
  if (clean.includes('cond') || clean.includes('case')) return { ...CATEGORY_META['Condicional'] };
  if (clean.includes('data') || clean.includes('date') || clean.includes('tempo')) return { ...CATEGORY_META['Datas'] };
  if (clean.includes('texto') || clean.includes('string')) return { ...CATEGORY_META['Texto'] };
  if (clean.includes('filt') || clean.includes('where')) return { ...CATEGORY_META['Filtragem'] };
  if (clean.includes('func') || clean.includes('matem')) return { ...CATEGORY_META['Funções'] };
  if (clean.includes('distin') || clean.includes('unic')) return { ...CATEGORY_META['Distintos'] };

  // Busca por chave parcial
  const matchedKey = Object.keys(CATEGORY_META).find((k) =>
    clean.includes(k.toLowerCase()) || k.toLowerCase().includes(clean)
  );

  if (matchedKey) {
    return { ...CATEGORY_META[matchedKey] };
  }

  // Fallback: limita ao primeiro termo
  const firstWord = name.split(' ')[0];
  return {
    icon: Tag,
    color: 'text-slate-600 dark:text-slate-400',
    bg: 'bg-slate-100 dark:bg-[#252a35]',
    border: 'border-slate-200 dark:border-[#333a46]',
    dot: 'bg-slate-400',
    displayName: firstWord,
  };
}
