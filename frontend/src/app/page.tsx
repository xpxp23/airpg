"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

export default function Home() {
  const { user } = useAuth();

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
      <div className="max-w-4xl mx-auto text-center">
        <div className="mb-8">
          <h1 className="text-6xl font-bold mb-4">
            <span className="bg-gradient-to-r from-fantasy-accent via-fantasy-gold to-fantasy-accent bg-clip-text text-transparent">
              AI 叙事跑团
            </span>
          </h1>
          <p className="text-xl text-fantasy-muted mb-2">
            Neverwinter Nights Async
          </p>
          <p className="text-lg text-fantasy-muted/80 max-w-2xl mx-auto">
            上传你的故事，AI 化身主持人，与好友一起在碎片化时间里体验沉浸式跑团冒险
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          <div className="bg-fantasy-card/50 backdrop-blur-sm p-6 rounded-xl border border-fantasy-accent/10 hover:border-fantasy-accent/30 transition-all">
            <div className="text-3xl mb-3"> </div>
            <h3 className="text-lg font-semibold text-fantasy-text mb-2">上传故事</h3>
            <p className="text-fantasy-muted text-sm">
              粘贴你喜欢的小说片段、原创剧情或世界观描述
            </p>
          </div>
          <div className="bg-fantasy-card/50 backdrop-blur-sm p-6 rounded-xl border border-fantasy-accent/10 hover:border-fantasy-accent/30 transition-all">
            <div className="text-3xl mb-3"> </div>
            <h3 className="text-lg font-semibold text-fantasy-text mb-2">AI 主持</h3>
            <p className="text-fantasy-muted text-sm">
              AI 自动解析故事，生成场景、角色和任务，担任你的专属 DM
            </p>
          </div>
          <div className="bg-fantasy-card/50 backdrop-blur-sm p-6 rounded-xl border border-fantasy-accent/10 hover:border-fantasy-accent/30 transition-all">
            <div className="text-3xl mb-3"> </div>
            <h3 className="text-lg font-semibold text-fantasy-text mb-2">协作冒险</h3>
            <p className="text-fantasy-muted text-sm">
              与好友异步行动，协作互助，共同推进故事走向结局
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          {user ? (
            <>
              <Link
                href="/games/new"
                className="bg-fantasy-accent hover:bg-fantasy-accent/80 text-white px-8 py-3 rounded-lg text-lg font-semibold transition-colors shadow-lg shadow-fantasy-accent/25"
              >
                创建新游戏
              </Link>
              <Link
                href="/games"
                className="border border-fantasy-accent/50 hover:bg-fantasy-accent/10 text-fantasy-text px-8 py-3 rounded-lg text-lg transition-colors"
              >
                进入游戏大厅
              </Link>
            </>
          ) : (
            <>
              <Link
                href="/register"
                className="bg-fantasy-accent hover:bg-fantasy-accent/80 text-white px-8 py-3 rounded-lg text-lg font-semibold transition-colors shadow-lg shadow-fantasy-accent/25"
              >
                开始冒险
              </Link>
              <Link
                href="/login"
                className="border border-fantasy-accent/50 hover:bg-fantasy-accent/10 text-fantasy-text px-8 py-3 rounded-lg text-lg transition-colors"
              >
                已有账号？登录
              </Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
