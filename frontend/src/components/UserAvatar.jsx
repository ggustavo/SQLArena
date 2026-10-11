import React, { useState, useEffect } from 'react';
import { getAvatarUrl } from '../services/api';

/**
 * Componente resiliente para exibição do avatar de usuário.
 * - Converte URLs relativas do FastAPI em URLs completas do backend.
 * - Trata falhas de carregamento (onError) exibindo automaticamente a inicial do usuário.
 * - Evita ícones de imagem quebrada mesmo em caso de erro de rede ou 404 do S3.
 */
export default function UserAvatar({
  user,
  avatarUrl,
  name,
  timestamp,
  className = 'w-10 h-10 rounded-2xl',
  textClassName = 'text-sm font-bold',
  fallbackBg = 'bg-indigo-600 text-white',
  alt,
}) {
  const [imgError, setImgError] = useState(false);

  const rawUrl = avatarUrl !== undefined ? avatarUrl : (user?.avatarUrl || user?.avatar_url);
  const resolvedUrl = getAvatarUrl(rawUrl, timestamp);
  const displayName = name || user?.name || 'Usuário';
  const initial = displayName.trim().charAt(0).toUpperCase() || 'U';

  // Reseta estado de erro se a URL mudar (ex: após upload de nova foto)
  useEffect(() => {
    setImgError(false);
  }, [resolvedUrl]);

  if (resolvedUrl && !imgError) {
    return (
      <img
        src={resolvedUrl}
        alt={alt || displayName}
        onError={() => setImgError(true)}
        className={`${className} object-cover shrink-0`}
      />
    );
  }

  return (
    <div
      className={`${className} ${fallbackBg} flex items-center justify-center shrink-0 select-none shadow-xs`}
      title={displayName}
    >
      <span className={textClassName}>{initial}</span>
    </div>
  );
}
