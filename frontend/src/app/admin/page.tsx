"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { AdminSettings, AdminGameInfo } from "@/types";

const PROMPT_FIELDS = [
  {
    key: "PROMPT_PARSE_STORY" as const,
    label: "故事解析",
    desc: "AI 解析玩家上传的故事文本时使用的提示词",
  },
  {
    key: "PROMPT_EVALUATE_ACTION" as const,
    label: "行动评估",
    desc: "AI 评估玩家行动的等待时间、难度和风险时使用的提示词",
  },
  {
    key: "PROMPT_GENERATE_NARRATIVE" as const,
    label: "叙事生成",
    desc: "AI 生成行动结果叙事时使用的核心提示词（最重要）",
  },
  {
    key: "PROMPT_EVALUATE_COOPERATION" as const,
    label: "协作评估",
    desc: "AI 评估玩家间协作时使用的提示词",
  },
  {
    key: "PROMPT_COMPRESS_MEMORY" as const,
    label: "记忆压缩",
    desc: "AI 将游戏事件压缩为记忆摘要时使用的提示词",
  },
];

export default function AdminPage() {
  const [adminToken, setAdminToken] = useState<string | null>(null);
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Settings state
  const [settings, setSettings] = useState<AdminSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);

  // Prompt defaults
  const [defaultPrompts, setDefaultPrompts] = useState<Record<string, string>>({});
  const [expandedPrompt, setExpandedPrompt] = useState<string | null>(null);

  // Password change state
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  // Room management state
  const [games, setGames] = useState<AdminGameInfo[]>([]);
  const [loadingGames, setLoadingGames] = useState(false);
  const [gameActionLoading, setGameActionLoading] = useState<string | null>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem("admin_token");
    if (stored) {
      setAdminToken(stored);
    }
  }, []);

  useEffect(() => {
    if (adminToken) {
      loadSettings();
      loadDefaults();
      loadGames();
    }
  }, [adminToken]);

  async function loadSettings() {
    try {
      const data = await api.getAdminSettings();
      setSettings(data);
    } catch (err: any) {
      setError(err.message || "加载设置失败");
      if (err.message?.includes("401") || err.message?.includes("expired")) {
        handleLogout();
      }
    }
  }

  async function loadDefaults() {
    try {
      const data = await api.getAdminDefaultPrompts();
      setDefaultPrompts(data);
    } catch {
      // defaults not critical
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { token } = await api.adminVerify(password);
      sessionStorage.setItem("admin_token", token);
      setAdminToken(token);
      setPassword("");
    } catch (err: any) {
      setError(err.message || "验证失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!adminToken || !settings) return;
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const updated = await api.updateAdminSettings(adminToken, settings);
      setSettings(updated);
      setSuccess("设置已保存");
      setTimeout(() => setSuccess(""), 3000);
    } catch (err: any) {
      setError(err.message || "保存失败");
      if (err.message?.includes("401") || err.message?.includes("expired")) {
        handleLogout();
      }
    } finally {
      setSaving(false);
    }
  }

  function handleLogout() {
    sessionStorage.removeItem("admin_token");
    setAdminToken(null);
    setSettings(null);
    setPassword("");
  }

  function updateField(key: keyof AdminSettings, value: string | number | boolean) {
    if (!settings) return;
    setSettings({ ...settings, [key]: value });
  }

  function resetPrompt(key: string) {
    if (!settings || !defaultPrompts[key]) return;
    setSettings({ ...settings, [key]: defaultPrompts[key] });
  }

  async function loadGames() {
    if (!adminToken) return;
    setLoadingGames(true);
    try {
      const data = await api.adminListGames(adminToken);
      setGames(data);
    } catch (err: any) {
      console.error("Failed to load games:", err);
    } finally {
      setLoadingGames(false);
    }
  }

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault();
    setPasswordError("");
    setPasswordSuccess("");
    if (newPassword !== confirmPassword) {
      setPasswordError("两次输入的新密码不一致");
      return;
    }
    if (newPassword.length < 6) {
      setPasswordError("密码长度不能少于6位");
      return;
    }
    setChangingPassword(true);
    try {
      await api.changeAdminPassword(adminToken!, oldPassword, newPassword);
      setPasswordSuccess("密码修改成功，即将退出登录...");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setTimeout(() => {
        handleLogout();
      }, 2000);
    } catch (err: any) {
      setPasswordError(err.message || "修改失败");
    } finally {
      setChangingPassword(false);
    }
  }

  async function handleCloseGame(gameId: string, gameTitle: string) {
    if (!confirm(`确定要关闭「${gameTitle || '未命名游戏'}」吗？`)) return;
    setGameActionLoading(gameId);
    try {
      await api.adminCloseGame(adminToken!, gameId);
      loadGames();
    } catch (err: any) {
      alert(err.message || "关闭失败");
    } finally {
      setGameActionLoading(null);
    }
  }

  async function handleDeleteGame(gameId: string, gameTitle: string) {
    if (!confirm(`确定要删除「${gameTitle || '未命名游戏'}」吗？此操作不可撤销。`)) return;
    setGameActionLoading(gameId);
    try {
      await api.adminDeleteGame(adminToken!, gameId);
      loadGames();
    } catch (err: any) {
      alert(err.message || "废弃失败");
    } finally {
      setGameActionLoading(null);
    }
  }

  // Password gate
  if (!adminToken) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="bg-fantasy-card/80 backdrop-blur-sm rounded-2xl p-8 border border-fantasy-accent/10">
            <h1 className="text-3xl font-bold text-center mb-2 bg-gradient-to-r from-fantasy-accent to-fantasy-gold bg-clip-text text-transparent">
               管理设置
            </h1>
            <p className="text-fantasy-muted text-center mb-8">
              请输入管理密码以继续
            </p>

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-6 text-sm">
                {error}
              </div>
            )}

            <form onSubmit={handleVerify} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-fantasy-muted mb-2">
                  管理密码
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors"
                  placeholder="请输入管理密码"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-fantasy-accent hover:bg-fantasy-accent/80 disabled:bg-fantasy-accent/50 text-white py-3 rounded-lg font-semibold transition-colors"
              >
                {loading ? "验证中..." : "验证"}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // Settings form
  if (!settings) {
    return (
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center">
        <div className="text-fantasy-muted">加载中...</div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-fantasy-accent to-fantasy-gold bg-clip-text text-transparent">
           AI 设置
        </h1>
        <button
          onClick={handleLogout}
          className="text-fantasy-muted hover:text-fantasy-accent text-sm transition-colors"
        >
          退出管理
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-6 text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg mb-6 text-sm">
          {success}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-6">
        {/* API Configuration */}
        <div className="bg-fantasy-card/80 backdrop-blur-sm rounded-2xl p-6 border border-fantasy-accent/10 space-y-5">
          <h2 className="text-lg font-semibold text-fantasy-text border-b border-fantasy-accent/10 pb-3">
            API 配置
          </h2>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              AI 提供商
            </label>
            <select
              value={settings.AI_PROVIDER}
              onChange={(e) => updateField("AI_PROVIDER", e.target.value)}
              className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
            >
              <option value="openai">OpenAI 兼容</option>
              <option value="anthropic">Anthropic Claude</option>
              <option value="local">本地模型</option>
              <option value="custom">自定义</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              API Key
            </label>
            <div className="relative">
              <input
                type={showApiKey ? "text" : "password"}
                value={settings.AI_API_KEY}
                onChange={(e) => updateField("AI_API_KEY", e.target.value)}
                className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 pr-12 text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors"
                placeholder="sk-..."
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-fantasy-muted hover:text-fantasy-text text-sm"
              >
                {showApiKey ? "隐藏" : "显示"}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              API Base URL
            </label>
            <input
              type="text"
              value={settings.AI_BASE_URL}
              onChange={(e) => updateField("AI_BASE_URL", e.target.value)}
              className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors"
              placeholder="https://api.openai.com/v1"
            />
          </div>
        </div>

        {/* Model Configuration */}
        <div className="bg-fantasy-card/80 backdrop-blur-sm rounded-2xl p-6 border border-fantasy-accent/10 space-y-5">
          <h2 className="text-lg font-semibold text-fantasy-text border-b border-fantasy-accent/10 pb-3">
            模型配置
          </h2>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              默认模型
            </label>
            <input
              type="text"
              value={settings.AI_MODEL_DEFAULT}
              onChange={(e) => updateField("AI_MODEL_DEFAULT", e.target.value)}
              className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors"
              placeholder="gpt-4o-mini"
            />
            <p className="text-xs text-fantasy-muted mt-1">用于评估、压缩等低成本任务</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              高级模型
            </label>
            <input
              type="text"
              value={settings.AI_MODEL_PREMIUM}
              onChange={(e) => updateField("AI_MODEL_PREMIUM", e.target.value)}
              className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors"
              placeholder="gpt-4o"
            />
            <p className="text-xs text-fantasy-muted mt-1">用于叙事生成等高质量任务</p>
          </div>
        </div>

        {/* Token Limits */}
        <div className="bg-fantasy-card/80 backdrop-blur-sm rounded-2xl p-6 border border-fantasy-accent/10 space-y-5">
          <h2 className="text-lg font-semibold text-fantasy-text border-b border-fantasy-accent/10 pb-3">
            Token 限制
          </h2>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              故事解析 Max Tokens
            </label>
            <input
              type="number"
              value={settings.MAX_TOKENS}
              onChange={(e) => updateField("MAX_TOKENS", parseInt(e.target.value) || 0)}
              className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
              min={1000}
            />
            <p className="text-xs text-fantasy-muted mt-1">AI 解析故事文本时的最大输出 token 数</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              默认 Max Tokens
            </label>
            <input
              type="number"
              value={settings.MAX_TOKENS_DEFAULT}
              onChange={(e) => updateField("MAX_TOKENS_DEFAULT", parseInt(e.target.value) || 0)}
              className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
              min={500}
            />
            <p className="text-xs text-fantasy-muted mt-1">其他 AI 调用的最大输出 token 数</p>
          </div>
        </div>

        {/* Memory Compression */}
        <div className="bg-fantasy-card/80 backdrop-blur-sm rounded-2xl p-6 border border-fantasy-accent/10 space-y-5">
          <h2 className="text-lg font-semibold text-fantasy-text border-b border-fantasy-accent/10 pb-3">
            记忆压缩
          </h2>
          <p className="text-xs text-fantasy-muted/60">
            当游戏事件积累到一定程度时，AI 会自动压缩历史事件为记忆摘要，避免遗忘早期剧情。满足任一条件即触发压缩。
          </p>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              事件轮数阈值
            </label>
            <input
              type="number"
              value={settings.MEMORY_COMPRESS_EVENT_THRESHOLD}
              onChange={(e) => updateField("MEMORY_COMPRESS_EVENT_THRESHOLD", parseInt(e.target.value) || 0)}
              className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
              min={0}
            />
            <p className="text-xs text-fantasy-muted mt-1">未压缩事件达到此数量时触发压缩，设为 0 则禁用此条件</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              字数阈值
            </label>
            <input
              type="number"
              value={settings.MEMORY_COMPRESS_CHAR_THRESHOLD}
              onChange={(e) => updateField("MEMORY_COMPRESS_CHAR_THRESHOLD", parseInt(e.target.value) || 0)}
              className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
              min={0}
            />
            <p className="text-xs text-fantasy-muted mt-1">未压缩事件总字数达到此值时触发压缩，设为 0 则禁用此条件</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-fantasy-muted mb-2">
              保留最近事件数
            </label>
            <input
              type="number"
              value={settings.MEMORY_COMPRESS_KEEP_RECENT}
              onChange={(e) => updateField("MEMORY_COMPRESS_KEEP_RECENT", parseInt(e.target.value) || 1)}
              className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
              min={1}
            />
            <p className="text-xs text-fantasy-muted mt-1">压缩时保留最近 N 条事件作为短期记忆，不参与压缩</p>
          </div>
        </div>

        {/* Thinking Mode */}
        <div className="bg-fantasy-card/80 backdrop-blur-sm rounded-2xl p-6 border border-fantasy-accent/10 space-y-5">
          <h2 className="text-lg font-semibold text-fantasy-text border-b border-fantasy-accent/10 pb-3">
            思考模式
          </h2>

          <div className="flex items-center justify-between">
            <div>
              <label className="block text-sm font-medium text-fantasy-muted mb-1">
                启用思考模式
              </label>
              <p className="text-xs text-fantasy-muted/60">模型会先输出思维链再给出答案，提升叙事质量</p>
            </div>
            <button
              type="button"
              onClick={() => updateField("AI_THINKING_ENABLED", !settings.AI_THINKING_ENABLED)}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                settings.AI_THINKING_ENABLED ? "bg-fantasy-accent" : "bg-fantasy-bg/50 border border-fantasy-accent/20"
              }`}
            >
              <span
                className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform ${
                  settings.AI_THINKING_ENABLED ? "translate-x-6" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>

          {settings.AI_THINKING_ENABLED && (
            <div>
              <label className="block text-sm font-medium text-fantasy-muted mb-2">
                思考强度
              </label>
              <div className="flex gap-3">
                {(["high", "max"] as const).map((effort) => (
                  <button
                    key={effort}
                    type="button"
                    onClick={() => updateField("AI_THINKING_EFFORT", effort)}
                    className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                      settings.AI_THINKING_EFFORT === effort
                        ? "bg-fantasy-accent text-white"
                        : "bg-fantasy-bg/50 border border-fantasy-accent/20 text-fantasy-muted hover:text-fantasy-text"
                    }`}
                  >
                    {effort === "high" ? "高 (high)" : "最大 (max)"}
                  </button>
                ))}
              </div>
              <p className="text-xs text-fantasy-muted mt-2">高 = 平衡质量与速度；最大 = 最强推理能力，适合复杂剧情</p>
            </div>
          )}
        </div>

        {/* Prompt Configuration */}
        <div className="bg-fantasy-card/80 backdrop-blur-sm rounded-2xl p-6 border border-fantasy-accent/10 space-y-4">
          <h2 className="text-lg font-semibold text-fantasy-text border-b border-fantasy-accent/10 pb-3">
            提示词配置
          </h2>
          <p className="text-xs text-fantasy-muted/60">
            自定义 AI 主持人的行为提示词。修改后需保存生效。留空表示使用默认值。
          </p>

          {PROMPT_FIELDS.map(({ key, label, desc }) => {
            const isExpanded = expandedPrompt === key;
            const currentValue = (settings as any)[key] || "";
            const defaultValue = defaultPrompts[key] || "";
            const isModified = currentValue && currentValue !== defaultValue;

            return (
              <div
                key={key}
                className="bg-fantasy-bg/30 rounded-xl border border-fantasy-accent/5 overflow-hidden"
              >
                <button
                  type="button"
                  onClick={() => setExpandedPrompt(isExpanded ? null : key)}
                  className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-fantasy-accent/5 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-fantasy-accent text-sm">
                      {isExpanded ? "▼" : "▶"}
                    </span>
                    <div className="min-w-0">
                      <span className="text-sm font-medium text-fantasy-text">{label}</span>
                      {isModified && (
                        <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-fantasy-accent/20 text-fantasy-accent">
                          已修改
                        </span>
                      )}
                    </div>
                  </div>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 space-y-3">
                    <p className="text-xs text-fantasy-muted/60">{desc}</p>

                    <textarea
                      value={currentValue}
                      onChange={(e) => updateField(key as keyof AdminSettings, e.target.value)}
                      className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-sm text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors font-mono resize-y"
                      rows={12}
                      placeholder={defaultValue}
                    />

                    <div className="flex items-center justify-between">
                      <button
                        type="button"
                        onClick={() => resetPrompt(key)}
                        className="text-xs text-fantasy-muted hover:text-fantasy-accent transition-colors"
                      >
                        恢复默认
                      </button>
                      {currentValue ? (
                        <span className="text-[10px] text-fantasy-muted/40">
                          {currentValue.length} 字
                        </span>
                      ) : (
                        <span className="text-[10px] text-fantasy-muted/40">
                          使用默认值
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Password Change */}
        <div className="bg-fantasy-card/80 backdrop-blur-sm rounded-2xl p-6 border border-fantasy-accent/10 space-y-5">
          <button
            type="button"
            onClick={() => setShowPasswordChange(!showPasswordChange)}
            className="w-full flex items-center justify-between text-lg font-semibold text-fantasy-text"
          >
            <span>  修改管理密码</span>
            <span className="text-fantasy-muted text-sm">{showPasswordChange ? "▲" : "▼"}</span>
          </button>

          {showPasswordChange && (
            <form onSubmit={handlePasswordChange} className="space-y-4">
              {passwordError && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded-lg text-sm">
                  {passwordError}
                </div>
              )}
              {passwordSuccess && (
                <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-2 rounded-lg text-sm">
                  {passwordSuccess}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-fantasy-muted mb-2">当前密码</label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-fantasy-muted mb-2">新密码</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
                  minLength={6}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-fantasy-muted mb-2">确认新密码</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text focus:outline-none focus:border-fantasy-accent/50 transition-colors"
                  minLength={6}
                  required
                />
              </div>
              <button
                type="submit"
                disabled={changingPassword}
                className="bg-fantasy-accent hover:bg-fantasy-accent/80 disabled:bg-fantasy-accent/50 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition-colors"
              >
                {changingPassword ? "修改中..." : "修改密码"}
              </button>
            </form>
          )}
        </div>

        {/* Room Management */}
        <div className="bg-fantasy-card/80 backdrop-blur-sm rounded-2xl p-6 border border-fantasy-accent/10 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-fantasy-text">  房间管理</h2>
            <button
              type="button"
              onClick={loadGames}
              disabled={loadingGames}
              className="text-fantasy-muted hover:text-fantasy-accent text-sm transition-colors"
            >
              {loadingGames ? "刷新中..." : "刷新"}
            </button>
          </div>

          {games.length === 0 ? (
            <p className="text-fantasy-muted text-sm">暂无游戏房间</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-fantasy-muted/60 text-left border-b border-fantasy-accent/10">
                    <th className="pb-2 pr-3">标题</th>
                    <th className="pb-2 pr-3">状态</th>
                    <th className="pb-2 pr-3">玩家</th>
                    <th className="pb-2 pr-3">章节</th>
                    <th className="pb-2">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {games.map((g) => (
                    <tr key={g.id} className="border-b border-fantasy-accent/5">
                      <td className="py-2.5 pr-3 text-fantasy-text truncate max-w-[150px]">
                        {g.title || "未命名"}
                      </td>
                      <td className="py-2.5 pr-3">
                        <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                          g.status === "active" ? "bg-green-500/20 text-green-400"
                          : g.status === "lobby" ? "bg-blue-500/20 text-blue-400"
                          : g.status === "finished" ? "bg-gray-500/20 text-gray-400"
                          : "bg-yellow-500/20 text-yellow-400"
                        }`}>
                          {g.status === "active" ? "进行中" : g.status === "lobby" ? "大厅" : g.status === "finished" ? "已结束" : g.status === "abandoned" ? "已废弃" : g.status}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 text-fantasy-muted">{g.player_count}</td>
                      <td className="py-2.5 pr-3 text-fantasy-muted">第{g.current_chapter}章</td>
                      <td className="py-2.5">
                        <div className="flex gap-2">
                          {(g.status === "active" || g.status === "lobby" || g.status === "paused") && (
                            <button
                              onClick={() => handleCloseGame(g.id, g.title || "")}
                              disabled={gameActionLoading === g.id}
                              className="text-yellow-400 hover:text-yellow-300 text-xs disabled:opacity-50"
                            >
                              关闭
                            </button>
                          )}
                          {g.status !== "finished" && g.status !== "abandoned" && (
                            <button
                              onClick={() => handleDeleteGame(g.id, g.title || "")}
                              disabled={gameActionLoading === g.id}
                              className="text-red-400 hover:text-red-300 text-xs disabled:opacity-50"
                            >
                              删除
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-fantasy-accent hover:bg-fantasy-accent/80 disabled:bg-fantasy-accent/50 text-white py-3 rounded-lg font-semibold transition-colors"
        >
          {saving ? "保存中..." : "保存设置"}
        </button>
      </form>
    </div>
  );
}
