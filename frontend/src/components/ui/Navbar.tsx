"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

export function Navbar() {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <nav className="bg-fantasy-card/80 backdrop-blur-md border-b border-fantasy-accent/20 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-4 md:space-x-8">
            <Link href="/" className="flex items-center space-x-2 shrink-0">
              <span className="text-2xl"> </span>
              <span className="text-lg sm:text-xl font-bold bg-gradient-to-r from-fantasy-accent to-fantasy-gold bg-clip-text text-transparent">
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

          <div className="flex items-center space-x-3">
            {/* Desktop auth controls */}
            <div className="hidden sm:flex items-center space-x-4">
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
                <>
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
                </>
              )}
            </div>

            {/* Mobile hamburger button */}
            {user && (
              <button
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className="md:hidden p-2 text-fantasy-muted hover:text-fantasy-text transition-colors"
                aria-label="Toggle menu"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {mobileMenuOpen ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  )}
                </svg>
              </button>
            )}

            {/* Mobile auth (when no hamburger) */}
            {!user && (
              <div className="sm:hidden flex items-center space-x-2">
                <Link
                  href="/login"
                  className="text-fantasy-muted hover:text-fantasy-text transition-colors text-sm"
                >
                  登录
                </Link>
                <Link
                  href="/register"
                  className="bg-fantasy-accent hover:bg-fantasy-accent/80 text-white px-3 py-1.5 rounded-md text-sm transition-colors"
                >
                  注册
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile dropdown menu */}
      {mobileMenuOpen && user && (
        <div className="md:hidden border-t border-fantasy-accent/10 bg-fantasy-card/95 backdrop-blur-md">
          <div className="px-4 py-3 space-y-1">
            <Link
              href="/games"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2.5 rounded-lg text-fantasy-muted hover:text-fantasy-text hover:bg-fantasy-accent/10 transition-colors text-sm"
            >
                游戏大厅
            </Link>
            <Link
              href="/games/new"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2.5 rounded-lg text-fantasy-muted hover:text-fantasy-text hover:bg-fantasy-accent/10 transition-colors text-sm"
            >
               创建游戏
            </Link>
            <div className="border-t border-fantasy-accent/10 pt-2 mt-2">
              <div className="px-3 py-2 text-fantasy-muted text-xs">
                {user.username}
              </div>
              <button
                onClick={() => { logout(); setMobileMenuOpen(false); }}
                className="block w-full text-left px-3 py-2.5 rounded-lg text-fantasy-muted hover:text-fantasy-accent hover:bg-fantasy-accent/10 transition-colors text-sm"
              >
                 退出登录
              </button>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
