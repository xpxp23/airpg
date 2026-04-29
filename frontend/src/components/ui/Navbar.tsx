"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

export function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav className="bg-fantasy-card/80 backdrop-blur-md border-b border-fantasy-accent/20 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link href="/" className="flex items-center space-x-2">
              <span className="text-2xl"> </span>
              <span className="text-xl font-bold bg-gradient-to-r from-fantasy-accent to-fantasy-gold bg-clip-text text-transparent">
                AI 叙事跑团
              </span>
            </Link>
            {user && (
              <div className="hidden md:flex space-x-4">
                <Link
                  href="/games"
                  className="text-fantasy-muted hover:text-fantasy-text transition-colors px-3 py-2 rounded-md text-sm"
                >
                  游戏大厅
                </Link>
                <Link
                  href="/games/new"
                  className="text-fantasy-muted hover:text-fantasy-text transition-colors px-3 py-2 rounded-md text-sm"
                >
                  创建游戏
                </Link>
              </div>
            )}
          </div>
          <div className="flex items-center space-x-4">
            {user ? (
              <>
                <span className="text-fantasy-muted text-sm">
                  {user.username}
                </span>
                <button
                  onClick={logout}
                  className="text-fantasy-muted hover:text-fantasy-accent transition-colors text-sm"
                >
                  退出
                </button>
              </>
            ) : (
              <div className="space-x-4">
                <Link
                  href="/login"
                  className="text-fantasy-muted hover:text-fantasy-text transition-colors text-sm"
                >
                  登录
                </Link>
                <Link
                  href="/register"
                  className="bg-fantasy-accent hover:bg-fantasy-accent/80 text-white px-4 py-2 rounded-md text-sm transition-colors"
                >
                  注册
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
