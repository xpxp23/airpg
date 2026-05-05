import { Token, Game, Character, GameAction, GameEvent, AdminSettings, AdminGameInfo } from "@/types";

const API_BASE = "/api/v1";

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem("token", token);
    } else {
      localStorage.removeItem("token");
    }
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = localStorage.getItem("token");
    }
    return this.token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  // Auth
  async register(username: string, email: string, password: string): Promise<Token> {
    return this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    });
  }

  async login(email: string, password: string): Promise<Token> {
    return this.request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async getMe(): Promise<any> {
    return this.request("/auth/me");
  }

  // Games
  async createGame(data: {
    story_text: string;
    duration_hint?: string;
    title?: string;
    max_players?: number;
    is_public?: boolean;
    game_mode?: string;
  }): Promise<Game> {
    return this.request("/games", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async listGames(scope: string = "public"): Promise<Game[]> {
    return this.request(`/games?scope=${scope}`);
  }

  async getGame(gameId: string): Promise<Game> {
    return this.request(`/games/${gameId}`);
  }

  async joinGame(gameId: string, characterId?: string): Promise<Character> {
    return this.request(`/games/${gameId}/join`, {
      method: "POST",
      body: JSON.stringify({ character_id: characterId }),
    });
  }

  async startGame(gameId: string): Promise<Game> {
    return this.request(`/games/${gameId}/start`, {
      method: "POST",
    });
  }

  async leaveGame(gameId: string): Promise<void> {
    return this.request(`/games/${gameId}/leave`, {
      method: "POST",
    });
  }

  async disbandGame(gameId: string): Promise<void> {
    return this.request(`/games/${gameId}/disband`, {
      method: "POST",
    });
  }

  async endGame(gameId: string): Promise<Game> {
    return this.request(`/games/${gameId}/end`, {
      method: "POST",
    });
  }

  async getEvents(gameId: string, since?: string, limit?: number): Promise<{ events: GameEvent[]; has_more: boolean }> {
    const params = new URLSearchParams();
    if (since) params.set("since", since);
    if (limit) params.set("limit", String(limit));
    const qs = params.toString();
    return this.request(`/games/${gameId}/events${qs ? `?${qs}` : ""}`);
  }

  async getCharacters(gameId: string): Promise<Character[]> {
    return this.request(`/games/${gameId}/characters`);
  }

  async createCharacter(
    gameId: string,
    data: { name: string; description?: string; background?: string }
  ): Promise<Character> {
    return this.request(`/games/${gameId}/characters`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Actions
  async submitAction(gameId: string, characterId: string, actionText: string): Promise<GameAction> {
    return this.request(`/games/${gameId}/actions`, {
      method: "POST",
      body: JSON.stringify({ character_id: characterId, action_text: actionText }),
    });
  }

  async getActions(gameId: string, status?: string): Promise<{ actions: GameAction[] }> {
    const params = status ? `?status=${status}` : "";
    return this.request(`/games/${gameId}/actions${params}`);
  }

  async cancelAction(gameId: string, actionId: string): Promise<void> {
    return this.request(`/games/${gameId}/actions/${actionId}`, {
      method: "DELETE",
    });
  }

  // Cooperation
  async submitCooperation(
    gameId: string,
    helperCharacterId: string,
    targetActionId: string,
    cooperationText: string
  ): Promise<GameAction> {
    return this.request(`/games/${gameId}/cooperation`, {
      method: "POST",
      body: JSON.stringify({
        helper_character_id: helperCharacterId,
        target_action_id: targetActionId,
        cooperation_text: cooperationText,
      }),
    });
  }

  // Parse
  async retryParse(gameId: string): Promise<Game> {
    return this.request(`/games/${gameId}/retry-parse`, {
      method: "POST",
    });
  }

  // Admin
  async adminVerify(password: string): Promise<{ token: string; expires_at: number }> {
    return this.request("/admin/verify", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
  }

  async getAdminSettings(): Promise<AdminSettings> {
    return this.request("/admin/settings");
  }

  async updateAdminSettings(adminToken: string, settings: Partial<AdminSettings>): Promise<AdminSettings> {
    return this.request("/admin/settings", {
      method: "PUT",
      body: JSON.stringify(settings),
      headers: { "X-Admin-Token": adminToken },
    });
  }

  async getAdminDefaultPrompts(): Promise<Record<string, string>> {
    return this.request("/admin/prompts/defaults");
  }

  async changeAdminPassword(adminToken: string, oldPassword: string, newPassword: string): Promise<{ message: string }> {
    return this.request("/admin/password", {
      method: "PUT",
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      headers: { "X-Admin-Token": adminToken },
    });
  }

  async adminListGames(adminToken: string): Promise<AdminGameInfo[]> {
    return this.request("/admin/games", {
      headers: { "X-Admin-Token": adminToken },
    });
  }

  async adminCloseGame(adminToken: string, gameId: string): Promise<{ message: string }> {
    return this.request(`/admin/games/${gameId}/close`, {
      method: "POST",
      headers: { "X-Admin-Token": adminToken },
    });
  }

  async adminDeleteGame(adminToken: string, gameId: string): Promise<void> {
    return this.request(`/admin/games/${gameId}`, {
      method: "DELETE",
      headers: { "X-Admin-Token": adminToken },
    });
  }

  async adminDeleteEndedGames(adminToken: string): Promise<{ deleted: number }> {
    return this.request("/admin/games/ended", {
      method: "DELETE",
      headers: { "X-Admin-Token": adminToken },
    });
  }
}

export const api = new ApiClient();
