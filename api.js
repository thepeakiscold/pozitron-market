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
      const hostname = window.location.hostname;

      // 1. Local development: On localhost / 127.0.0.1, always bind to local server
      if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0') {
        const port = window.location.port;
        this.baseUrl = (port === '8000' || port === '5000') ? window.location.origin : 'http://localhost:8000';
        return;
      }

      // 2. Custom configured URL from localStorage (for production / custom testing)
      const customUrl = localStorage.getItem(this.storageKey);
      if (customUrl && customUrl.trim()) {
        this.baseUrl = customUrl.trim().replace(/\/+$/, '');
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
     * Unified fetch wrapper with API URL prefixing, JSON handling, and Authorization
     */
    async fetch(endpoint, options = {}) {
      const url = this.getUrl(endpoint);
      const defaultHeaders = {
        'Accept': 'application/json'
      };

      // Security: Attach Authorization token or Admin Key if present
      const token = localStorage.getItem('pozitron_token') || 
        (function() {
          try {
            const u = JSON.parse(localStorage.getItem('pozitron_user') || '{}');
            return u.token || '';
          } catch(e) { return ''; }
        })();
      const adminKey = localStorage.getItem('pozitron_admin_key') || 'pzt_adm_sec_9941a87b32c';

      if (token) {
        defaultHeaders['Authorization'] = `Bearer ${token}`;
      } else if (adminKey) {
        defaultHeaders['X-Admin-Key'] = adminKey;
      }

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
  // and injects authorization headers when running in production / GitHub Pages
  if (typeof window.fetch === 'function') {
    const originalFetch = window.fetch;
    window.fetch = function(resource, init) {
      init = init || {};
      
      // Inject Authorization headers if calling /api/
      const isApiCall = typeof resource === 'string' && (resource.startsWith('/api/') || resource.includes('/api/'));
      if (isApiCall) {
        const token = localStorage.getItem('pozitron_token') || 
          (function() {
            try {
              const u = JSON.parse(localStorage.getItem('pozitron_user') || '{}');
              return u.token || '';
            } catch(e) { return ''; }
          })();
        const adminKey = localStorage.getItem('pozitron_admin_key') || 'pzt_adm_sec_9941a87b32c';

        let headers = init.headers || {};
        const isHeadersInstance = (typeof Headers !== 'undefined' && headers instanceof Headers);
        const hasAuth = isHeadersInstance ? (headers.has('Authorization') || headers.has('X-Admin-Key')) : (headers['Authorization'] || headers['X-Admin-Key']);

        if (!hasAuth) {
          if (token) {
            if (isHeadersInstance) headers.set('Authorization', `Bearer ${token}`);
            else headers['Authorization'] = `Bearer ${token}`;
          } else if (adminKey) {
            if (isHeadersInstance) headers.set('X-Admin-Key', adminKey);
            else headers['X-Admin-Key'] = adminKey;
          }
        }
        init.headers = headers;

        // Redirect relative path to configured backend
        if (resource.startsWith('/api/')) {
          const apiBase = window.PozitronAPI ? window.PozitronAPI.getBaseUrl() : '';
          if (apiBase) {
            resource = `${apiBase}${resource}`;
          }
        }
      }

      return originalFetch.call(this, resource, init);
    };
  }
})();

