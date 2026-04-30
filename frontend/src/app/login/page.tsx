"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || "登录失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-[calc(100dvh-4rem)] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-md">
        <div className="bg-fantasy-card/80 backdrop-blur-sm rounded-2xl p-5 sm:p-8 border border-fantasy-accent/10">
          <h1 className="text-2xl sm:text-3xl font-bold text-center mb-2 bg-gradient-to-r from-fantasy-accent to-fantasy-gold bg-clip-text text-transparent">
            欢迎回来
          </h1>
          <p className="text-fantasy-muted text-center mb-6 sm:mb-8 text-sm sm:text-base">
            登录你的账号，继续冒险
          </p>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-6 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6">
            <div>
              <label className="block text-sm font-medium text-fantasy-muted mb-2">
                邮箱
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors"
                placeholder="your@email.com"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-fantasy-muted mb-2">
                密码
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-fantasy-bg/50 border border-fantasy-accent/20 rounded-lg px-4 py-3 text-fantasy-text placeholder-fantasy-muted/50 focus:outline-none focus:border-fantasy-accent/50 transition-colors"
                placeholder="••••••••"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-fantasy-accent hover:bg-fantasy-accent/80 disabled:bg-fantasy-accent/50 text-white py-3 rounded-lg font-semibold transition-colors"
            >
              {loading ? "登录中..." : "登录"}
            </button>
          </form>

          <p className="text-center text-fantasy-muted text-sm mt-6">
            还没有账号？{" "}
            <Link href="/register" className="text-fantasy-accent hover:text-fantasy-accent/80">
              立即注册
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
