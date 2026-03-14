/**
 * API helpers — all calls return null on failure instead of throwing.
 * This prevents white screens when the backend is down.
 */

const api = {
  get: async (url) => {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("json")) throw new Error("Response not JSON");
      return await response.json();
    } catch (err) {
      console.warn(`API GET ${url}:`, err.message);
      return null;
    }
  },

  post: async (url, body) => {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (err) {
      console.warn(`API POST ${url}:`, err.message);
      return null;
    }
  },

  patch: async (url, body) => {
    try {
      const response = await fetch(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return response.ok;
    } catch {
      return false;
    }
  },

  del: async (url) => {
    try {
      const response = await fetch(url, { method: "DELETE" });
      return response.ok;
    } catch {
      return false;
    }
  },
};

export default api;