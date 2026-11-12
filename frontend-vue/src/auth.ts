import { reactive } from "vue";
import { OpenAPI } from "./api";
import type { AccountSummary, UserOut } from "./api";

// Shape of the signed-in user kept in localStorage. It is either the login
// summary or the full profile returned by the users endpoints.
export type SessionUser = AccountSummary | UserOut;

const getStoredUser = (): SessionUser | null => {
  const storedUser = localStorage.getItem("user");
  if (!storedUser) return null;

  try {
    return JSON.parse(storedUser) as SessionUser;
  } catch {
    localStorage.removeItem("user");
    return null;
  }
};

const storedToken = localStorage.getItem("token");
if (storedToken) {
  OpenAPI.TOKEN = storedToken;
}

export const authState = reactive({
  isLoggedIn: !!storedToken,
  user: getStoredUser(),

  setSession(token: string, user: SessionUser) {
    localStorage.setItem("token", token);
    localStorage.setItem("user", JSON.stringify(user));
    OpenAPI.TOKEN = token;

    this.isLoggedIn = true;
    this.user = user;
  },

  logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    OpenAPI.TOKEN = undefined;

    this.isLoggedIn = false;
    this.user = null;
  },
});
