/**
 * Pozitron Market - Centralized Cloud API Client
 * Manages communication between the static frontend (GitHub Pages) and the cloud backend (Render / Railway / VPS).
 */

(function() {
  // Default cloud API endpoint (Can be overridden via localStorage or admin settings)
  const DEFAULT_CLOUD_API = "https://pozitron-market-api.onrender.com";

  class PozitronApiClient {
    constructor() {
      this.storageKey = 'pozitron_api_base_url';
      this.initUrl();
    }

    initUrl() {
      // 1. Check custom configured URL from localStorage
      const customUrl = localStorage.getItem(this.storageKey);
      if (customUrl && customUrl.trim()) {
        this.baseUrl = customUrl.trim().replace(/\/+$/, '');
        return;
      }

      // 2. Local development fallback
      const hostname = window.location.hostname;
      if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0') {
        const port = window.location.port;
        // If frontend is running on 8000 or 5000, use origin, otherwise default backend port 8000
        this.baseUrl = (port === '8000' || port === '5000') ? window.location.origin : 'http://localhost:8000';
        return;
      }

      // 3. In production (GitHub Pages or custom domain)
      // Default to the central cloud API service
      this.baseUrl = DEFAULT_CLOUD_API;
    }

    getBaseUrl() {
      return this.baseUrl || '';
    }

    setBaseUrl(url) {
      if (!url) {
        localStorage.removeItem(this.storageKey);
        this.initUrl();
      } else {
        const clean = url.trim().replace(/\/+$/, '');
        localStorage.setItem(this.storageKey, clean);
        this.baseUrl = clean;
      }
      return this.baseUrl;
    }

    getUrl(endpoint) {
      const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
      if (!this.baseUrl) return cleanEndpoint;
      return `${this.baseUrl}${cleanEndpoint}`;
    }

    async checkHealth() {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 4000);
        const res = await fetch(this.getUrl('/api/health'), {
          signal: controller.signal,
          headers: { 'Accept': 'application/json' }
        });
        clearTimeout(timeoutId);
        if (res.ok) {
          const data = await res.json();
          return { ok: true, data };
        }
        return { ok: false, status: res.status };
      } catch (err) {
        return { ok: false, error: err.message };
      }
    }

    /**
     * Unified fetch wrapper with API URL prefixing and JSON handling
     */
    async fetch(endpoint, options = {}) {
      const url = this.getUrl(endpoint);
      const defaultHeaders = {
        'Accept': 'application/json'
      };

      if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
        defaultHeaders['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
      }

      options.headers = {
        ...defaultHeaders,
        ...(options.headers || {})
      };

      return fetch(url, options);
    }

    /**
     * Authenticate or register Google user with centralized backend
     */
    async authGoogle(userData) {
      return this.fetch('/api/auth/google', {
        method: 'POST',
        body: userData
      });
    }

    /**
     * Fetch registered users for admin panel
     */
    async getAdminUsers() {
      const res = await this.fetch('/api/admin/users');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    }

    /**
     * Fetch orders for admin panel
     */
    async getAdminOrders() {
      const res = await this.fetch('/api/admin/orders');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    }
  }

  // Attach to global window
  window.PozitronAPI = new PozitronApiClient();

  // Transparent fetch interceptor: Automatically redirects relative /api/ calls
  // to the configured cloud backend when running in production / GitHub Pages
  if (typeof window.fetch === 'function') {
    const originalFetch = window.fetch;
    window.fetch = function(resource, init) {
      if (typeof resource === 'string' && resource.startsWith('/api/')) {
        const apiBase = window.PozitronAPI ? window.PozitronAPI.getBaseUrl() : '';
        if (apiBase) {
          resource = `${apiBase}${resource}`;
        }
      }
      return originalFetch.call(this, resource, init);
    };
  }
})();

