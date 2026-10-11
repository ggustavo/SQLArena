import React, { useState, useRef } from 'react';
import {
  ArrowLeft,
  Save,
  UserRound,
  Mail,
  Lock,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Camera,
  Trash2,
  Building2,
  MapPin,
  Globe,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { updateProfile, uploadAvatar, deleteAvatar, deleteMyAccount } from '../services/authService';
import UserAvatar from '../components/UserAvatar';

export default function ProfilePage({ user, onBack, onUpdated, onAccountDeleted }) {
  const [name, setName] = useState(user.name || '');
  const [email, setEmail] = useState(user.email || '');
  const [university, setUniversity] = useState(user.university || '');
  const [city, setCity] = useState(user.city || '');
  const [state, setState] = useState(user.state || '');
  const [country, setCountry] = useState(user.country || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [password, setPassword] = useState('');

  const [saving, setSaving] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [deletingAvatar, setDeletingAvatar] = useState(false);
  const [deletingAccount, setDeletingAccount] = useState(false);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [avatarTimestamp, setAvatarTimestamp] = useState(Date.now());
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const fileInputRef = useRef(null);
  const isInstructor = user.role === 'INSTRUCTOR' || user.role === 'ADMIN';

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      setError('Por favor, selecione um arquivo de imagem válido (PNG, JPG, WEBP).');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError('A imagem excede o tamanho máximo permitido de 5MB.');
      return;
    }

    // Pré-visualização local instantânea antes do término do upload
    const localPreview = URL.createObjectURL(file);
    setPreviewUrl(localPreview);

    setUploadingAvatar(true);
    setError('');
    setMessage('');
    try {
      const updated = await uploadAvatar(file);
      onUpdated(updated);
      setAvatarTimestamp(Date.now());
      setPreviewUrl(null);
      setMessage('Foto de perfil redimensionada e salva no Amazon S3 com sucesso!');
    } catch (err) {
      setPreviewUrl(null);
      setError(err.response?.data?.detail || 'Erro ao enviar a imagem.');
    } finally {
      setUploadingAvatar(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  async function handleRemoveAvatar() {
    if (!window.confirm('Deseja realmente remover sua foto de perfil?')) return;
    setDeletingAvatar(true);
    setError('');
    setMessage('');
    try {
      const updated = await deleteAvatar();
      setPreviewUrl(null);
      setAvatarTimestamp(Date.now());
      onUpdated(updated);
      setMessage('Foto de perfil removida com sucesso.');
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao remover foto de perfil.');
    } finally {
      setDeletingAvatar(false);
    }
  }

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
        university: university.trim() || null,
        city: city.trim() || null,
        state: state.trim() || null,
        country: country.trim() || null,
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

  async function handleDeleteAccount() {
    const confirmed = window.confirm(
      'Atenção! Deseja realmente excluir sua conta? Esta ação removerá seus dados, pontuação e foto do Amazon S3 permanentemente.'
    );
    if (!confirmed) return;

    setDeletingAccount(true);
    setError('');
    try {
      await deleteMyAccount();
      if (onAccountDeleted) {
        onAccountDeleted();
      } else {
        window.location.reload();
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Não foi possível excluir sua conta.');
      setDeletingAccount(false);
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
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 pb-6 border-b border-slate-100 dark:border-[#2d3340]">
          <div className="flex items-center gap-5">
            {/* Avatar with image preview and upload trigger */}
            <div className="relative group">
              <div className="w-20 h-20 rounded-2xl overflow-hidden shadow-md shadow-indigo-600/20 border-2 border-indigo-200 dark:border-indigo-800">
                <UserAvatar
                  user={user}
                  avatarUrl={previewUrl || user.avatarUrl}
                  name={name}
                  timestamp={avatarTimestamp}
                  className="w-full h-full"
                  textClassName="text-2xl font-black"
                  fallbackBg="bg-indigo-600 dark:bg-indigo-500 text-white"
                />
              </div>

              {/* Upload Overlay Button */}
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingAvatar}
                title="Alterar foto de perfil"
                className="absolute -bottom-2 -right-2 p-2 rounded-xl bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 shadow-md hover:scale-105 transition cursor-pointer"
              >
                {uploadingAvatar ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Camera size={14} />
                )}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={handleFileChange}
              />
            </div>

            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white">
                  {name || 'Meu Perfil'}
                </h1>
              </div>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {email}
              </p>
              {(user.avatarUrl || previewUrl) && (
                <button
                  type="button"
                  onClick={handleRemoveAvatar}
                  disabled={deletingAvatar || uploadingAvatar}
                  className="mt-1.5 inline-flex items-center gap-1 text-xs text-rose-500 hover:text-rose-600 transition cursor-pointer"
                >
                  <Trash2 size={12} /> Remover foto de perfil
                </button>
              )}
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
          {/* Dados Pessoais */}
          <div className="space-y-4">
            <h2 className="text-base font-bold text-slate-900 dark:text-white">Dados Principais</h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
          </div>

          {/* Dados Acadêmicos & Localização (Campos Opcionais) */}
          <div className="pt-6 border-t border-slate-100 dark:border-[#2d3340] space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">Informações Acadêmicas & Localização</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Campos opcionais para personalizar seu perfil no ranking da plataforma.
              </p>
            </div>

            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                  Universidade / Instituição de Ensino
                </label>
                <div className="relative">
                  <Building2 size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    maxLength={120}
                    value={university}
                    onChange={(e) => setUniversity(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-200 dark:border-[#353d4d] bg-slate-50 dark:bg-[#16181e] text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
                    placeholder="Ex: Universidade Federal / PUC / USP"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                    Cidade
                  </label>
                  <div className="relative">
                    <MapPin size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      maxLength={80}
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-200 dark:border-[#353d4d] bg-slate-50 dark:bg-[#16181e] text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
                      placeholder="Ex: São Paulo"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                    Estado
                  </label>
                  <input
                    type="text"
                    maxLength={80}
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    className="w-full px-4 py-3 rounded-2xl border border-slate-200 dark:border-[#353d4d] bg-slate-50 dark:bg-[#16181e] text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
                    placeholder="Ex: SP"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
                    País
                  </label>
                  <div className="relative">
                    <Globe size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      maxLength={80}
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                      className="w-full pl-11 pr-4 py-3 rounded-2xl border border-slate-200 dark:border-[#353d4d] bg-slate-50 dark:bg-[#16181e] text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-600/20 transition"
                      placeholder="Ex: Brasil"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Alterar Senha */}
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

        {/* Zona de Perigo / Exclusão de Conta (CRUD DELETE) */}
        <div className="pt-6 border-t border-rose-200/60 dark:border-rose-950/60 space-y-4">
          <div className="flex items-center gap-2 text-rose-600 dark:text-rose-400">
            <AlertTriangle size={18} />
            <h2 className="text-base font-bold">Zona de Perigo</h2>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-2xl bg-rose-50/60 dark:bg-rose-950/20 border border-rose-200/80 dark:border-rose-900/40">
            <div>
              <div className="font-bold text-sm text-slate-900 dark:text-white">
                Excluir Minha Conta
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                Encerra permanentemente seu acesso e remove suas informações do banco de dados e arquivos do Amazon S3.
              </p>
            </div>
            <button
              type="button"
              onClick={handleDeleteAccount}
              disabled={deletingAccount}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs shadow-sm transition cursor-pointer disabled:opacity-50 shrink-0"
            >
              <Trash2 size={14} />
              {deletingAccount ? 'Excluindo...' : 'Excluir Conta'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
