"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { AdminSettings } from "@/types";

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
