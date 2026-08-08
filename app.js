/**
 * Pozitron Market - Minimalist Client Application Engine
 */

class PozitronApp {
  constructor() {
    this.apiBase = '/api';
    this.currency = localStorage.getItem('pozitron_currency') || 'TRY';
    this.cart = JSON.parse(localStorage.getItem('pozitron_cart') || '[]');
    this.user = JSON.parse(localStorage.getItem('pozitron_user') || 'null');
    this.appliedCoupon = null;
    this.categories = [];
    this.brands = [];
    
    // Query Filters State
    this.filters = {
      q: '',
      category: 'all',
      brand: 'all',
      voltage: 'all',
      in_stock: '1',
      bestseller: '0',
      min_price: '',
      max_price: '',
      sort: 'popular',
      page: 1,
      limit: 24
    };

    // Drone Builder Selection State
    this.builderParts = {
      motor: null,
      esc: null,
      prop: null,
      battery: null
    };

    this.pendingOrderData = null;

    this.init();
  }

  async init() {
    // 1. Initialize i18n
    window.i18n.updateDom();

    // 2. Setup Event Listeners
    this.bindEvents();

    // 3. Load Initial Data
    await this.loadCategories();
    await this.loadBrands();
    this.updateUserUI();
    this.updateCartUI();

    // 4. Parse URL Hash on Load (e.g. #category=motors or #q=speedybee)
    this.handleHashChange();

    // 5. Initial Product Fetch
    await this.fetchProducts();

    // 6. Listen for hash changes
    window.addEventListener('hashchange', () => this.handleHashChange());
    window.addEventListener('languageChanged', () => {
      this.renderCategoriesPills();
      this.renderCategorySidebar();
      this.fetchProducts();
      this.updateDynamicSeoMeta();
    });
  }

  handleHashChange() {
    const hash = window.location.hash.replace(/^#/, '');
    if (!hash) return;

    if (hash.startsWith('category=')) {
      const cat = hash.split('=')[1];
      this.filters.category = cat;
      this.filters.page = 1;
    } else if (hash.startsWith('q=')) {
      const query = decodeURIComponent(hash.split('=')[1]);
      this.filters.q = query;
      const searchInput = document.getElementById('search-input');
      if (searchInput) searchInput.value = query;
      this.filters.page = 1;
    } else if (hash.startsWith('product=')) {
      const prodSlug = hash.split('=')[1];
      this.openProductModal(prodSlug);
    } else if (hash === 'builder') {
      this.openBuilderModal();
    }
  }

  updateDynamicSeoMeta() {
    const lang = window.i18n.currentLang;
    const catObj = this.categories.find(c => c.id === this.filters.category);
    let title = "Pozitron Market | 500+ Drone & FPV Donanım Parçası";

    if (this.filters.q) {
      title = `${this.filters.q} - Drone Parçaları | Pozitron Market`;
    } else if (catObj) {
      const catName = lang === 'tr' ? catObj.name_tr : catObj.name_en;
      title = `${catName} | Pozitron Market (500+ Parça)`;
    }

    document.title = title;
  }

  bindEvents() {
    // Language Toggle
    const langBtn = document.getElementById('lang-btn');
    if (langBtn) {
      langBtn.addEventListener('click', () => {
        const nextLang = window.i18n.currentLang === 'tr' ? 'en' : 'tr';
        window.i18n.setLanguage(nextLang);
      });
    }

    // Currency Switcher
    document.querySelectorAll('.curr-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const curr = e.currentTarget.getAttribute('data-currency');
        this.setCurrency(curr);
      });
    });

    // Search Input & Live Suggestion
    const searchInput = document.getElementById('search-input');
    const searchClear = document.getElementById('search-clear-btn');
    const searchForm = document.getElementById('search-form');

    if (searchInput) {
      let debounceTimer = null;
      searchInput.addEventListener('input', (e) => {
        const val = e.target.value.trim();
        searchClear.style.display = val ? 'block' : 'none';
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          this.handleLiveSearch(val);
        }, 220);
      });

      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.filters.q = searchInput.value.trim();
          this.filters.page = 1;
          this.hideSuggestions();
          this.fetchProducts();
        }
      });
    }

    if (searchClear) {
      searchClear.addEventListener('click', () => {
        searchInput.value = '';
        searchClear.style.display = 'none';
        this.filters.q = '';
        this.hideSuggestions();
        this.fetchProducts();
      });
    }

    // Close suggestions on outside click
    document.addEventListener('click', (e) => {
      if (!e.target.closest('.header-search-wrap')) {
        this.hideSuggestions();
      }
      if (!e.target.closest('#user-auth-wrap')) {
        const drop = document.getElementById('user-dropdown-menu');
        if (drop) drop.style.display = 'none';
      }
    });

    // Cart Drawer Toggle
    const cartDrawerBtn = document.getElementById('cart-drawer-btn');
    const closeCartBtn = document.getElementById('close-cart-btn');
    const cartBackdrop = document.getElementById('cart-backdrop');

    if (cartDrawerBtn) {
      cartDrawerBtn.addEventListener('click', () => this.openCartDrawer());
    }
    if (closeCartBtn) {
      closeCartBtn.addEventListener('click', () => this.closeCartDrawer());
    }
    if (cartBackdrop) {
      cartBackdrop.addEventListener('click', (e) => {
        if (e.target === cartBackdrop) this.closeCartDrawer();
      });
    }

    // Sorting Dropdown
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
      sortSelect.addEventListener('change', (e) => {
        this.filters.sort = e.target.value;
        this.filters.page = 1;
        this.fetchProducts();
      });
    }

    // Reset Filters Button
    const resetBtn = document.getElementById('btn-reset-filters');
    const resetEmptyBtn = document.getElementById('btn-reset-empty');
    const handleReset = () => {
      this.filters = {
        q: '',
        category: 'all',
        brand: 'all',
        voltage: 'all',
        in_stock: '1',
        bestseller: '0',
        min_price: '',
        max_price: '',
        sort: 'popular',
        page: 1,
        limit: 24
      };
      if (searchInput) searchInput.value = '';
      if (searchClear) searchClear.style.display = 'none';
      document.getElementById('filter-in-stock').checked = true;
      document.getElementById('filter-bestseller').checked = false;
      document.getElementById('min-price-input').value = '';
      document.getElementById('max-price-input').value = '';
      this.renderCategoriesPills();
      this.renderCategorySidebar();
      this.renderBrandSidebar();
      this.fetchProducts();
    };

    if (resetBtn) resetBtn.addEventListener('click', handleReset);
    if (resetEmptyBtn) resetEmptyBtn.addEventListener('click', handleReset);

    // Price Filter Apply
    const btnApplyPrice = document.getElementById('btn-apply-price');
    if (btnApplyPrice) {
      btnApplyPrice.addEventListener('click', () => {
        this.filters.min_price = document.getElementById('min-price-input').value;
        this.filters.max_price = document.getElementById('max-price-input').value;
        this.filters.page = 1;
        this.fetchProducts();
      });
    }

    // In Stock / Bestseller Checkboxes
    const inStockChk = document.getElementById('filter-in-stock');
    if (inStockChk) {
      inStockChk.addEventListener('change', (e) => {
        this.filters.in_stock = e.target.checked ? '1' : '0';
        this.filters.page = 1;
        this.fetchProducts();
      });
    }

    const bestsellerChk = document.getElementById('filter-bestseller');
    if (bestsellerChk) {
      bestsellerChk.addEventListener('change', (e) => {
        this.filters.bestseller = e.target.checked ? '1' : '0';
        this.filters.page = 1;
        this.fetchProducts();
      });
    }

    // Voltage Filter Pills
    document.querySelectorAll('#voltage-filter-list .v-pill').forEach(pill => {
      pill.addEventListener('click', (e) => {
        document.querySelectorAll('#voltage-filter-list .v-pill').forEach(p => p.classList.remove('active'));
        e.currentTarget.classList.add('active');
        this.filters.voltage = e.currentTarget.getAttribute('data-voltage');
        this.filters.page = 1;
        this.fetchProducts();
      });
    });

    // Hero CTA Buttons
    const heroExpBtn = document.getElementById('hero-explore-btn');
    if (heroExpBtn) {
      heroExpBtn.addEventListener('click', () => {
        document.getElementById('catalog-section').scrollIntoView({ behavior: 'smooth' });
      });
    }

    const heroBldBtn = document.getElementById('hero-builder-btn');
    const openBldBtn = document.getElementById('open-builder-btn');
    const footerBldLink = document.getElementById('footer-builder-link');
    [heroBldBtn, openBldBtn, footerBldLink].forEach(el => {
      if (el) el.addEventListener('click', (e) => {
        e.preventDefault();
        this.openBuilderModal();
      });
    });

    // Modals Close Buttons
    const closeProdModal = document.getElementById('close-product-modal');
    if (closeProdModal) closeProdModal.addEventListener('click', () => this.closeProductModal());

    const closeBldModal = document.getElementById('close-builder-modal');
    if (closeBldModal) closeBldModal.addEventListener('click', () => this.closeBuilderModal());

    const closeAuthModal = document.getElementById('close-auth-modal');
    if (closeAuthModal) closeAuthModal.addEventListener('click', () => this.closeAuthModal());

    const closeChkModal = document.getElementById('close-checkout-modal');
    if (closeChkModal) closeChkModal.addEventListener('click', () => this.closeCheckoutModal());

    // User Auth Button & Tabs
    const authBtn = document.getElementById('auth-btn');
    if (authBtn) {
      authBtn.addEventListener('click', () => {
        if (this.user) {
          const drop = document.getElementById('user-dropdown-menu');
          drop.style.display = drop.style.display === 'none' ? 'block' : 'none';
        } else {
          this.openAuthModal();
        }
      });
    }

    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    if (tabLogin && tabRegister) {
      tabLogin.addEventListener('click', () => {
        tabLogin.classList.add('active');
        tabRegister.classList.remove('active');
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
      });
      tabRegister.addEventListener('click', () => {
        tabRegister.classList.add('active');
        tabLogin.classList.remove('active');
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
      });
    }

    // Google Sign In Simulation
    const googleLoginBtn = document.getElementById('google-login-btn');
    if (googleLoginBtn) {
      googleLoginBtn.addEventListener('click', () => this.handleGoogleAuth());
    }

    // Manual Login Form Submit
    if (loginForm) {
      loginForm.addEventListener('submit', (e) => this.handleManualLogin(e));
    }
    if (registerForm) {
      registerForm.addEventListener('submit', (e) => this.handleManualRegister(e));
    }

    // Logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', () => this.handleLogout());
    }

    // Coupon Apply
    const applyCouponBtn = document.getElementById('apply-coupon-btn');
    if (applyCouponBtn) {
      applyCouponBtn.addEventListener('click', () => this.handleApplyCoupon());
    }

    // Proceed to Checkout
    const proceedCheckoutBtn = document.getElementById('proceed-checkout-btn');
    if (proceedCheckoutBtn) {
      proceedCheckoutBtn.addEventListener('click', () => {
        if (this.cart.length === 0) {
          this.showToast(window.i18n.t('empty_desc'), 'error');
          return;
        }
        this.closeCartDrawer();
        this.openCheckoutModal();
      });
    }

    // 1-Click Test Card Autofill
    const btnAutofillCard = document.getElementById('btn-autofill-card');
    if (btnAutofillCard) {
      btnAutofillCard.addEventListener('click', () => this.autofillTestCard());
    }

    // Credit Card Live Formatting
    const cardNumInput = document.getElementById('card-number-input');
    if (cardNumInput) {
      cardNumInput.addEventListener('input', (e) => {
        let val = e.target.value.replace(/\D/g, '').substring(0, 16);
        val = val.replace(/(.{4})/g, '$1 ').trim();
        e.target.value = val;
        document.getElementById('preview-card-number').textContent = val || '•••• •••• •••• ••••';
        
        // Brand logo
        const brandEl = document.getElementById('preview-card-brand');
        if (val.startsWith('4')) brandEl.textContent = 'VISA';
        else if (val.startsWith('5')) brandEl.textContent = 'MasterCard';
        else if (val.startsWith('9792')) brandEl.textContent = 'TROY';
        else if (val.startsWith('3')) brandEl.textContent = 'AMEX';
      });
    }

    const cardHolderInput = document.getElementById('card-holder-input');
    if (cardHolderInput) {
      cardHolderInput.addEventListener('input', (e) => {
        document.getElementById('preview-card-holder').textContent = e.target.value.toUpperCase() || 'PILOT AD SOYAD';
      });
    }

    const cardExpiryInput = document.getElementById('card-expiry-input');
    if (cardExpiryInput) {
      cardExpiryInput.addEventListener('input', (e) => {
        let val = e.target.value.replace(/\D/g, '').substring(0, 4);
        if (val.length >= 2) val = val.substring(0, 2) + '/' + val.substring(2);
        e.target.value = val;
        document.getElementById('preview-card-expiry').textContent = val || '12/28';
      });
    }

    // Checkout Submit (triggers 3D Secure OTP)
    const submitOrderBtn = document.getElementById('submit-order-btn');
    if (submitOrderBtn) {
      submitOrderBtn.addEventListener('click', () => this.handleCheckoutSubmit());
    }

    // OTP Code Confirmation
    const confirmOtpBtn = document.getElementById('confirm-otp-btn');
    if (confirmOtpBtn) {
      confirmOtpBtn.addEventListener('click', () => this.handleOtpConfirm());
    }

    // Continue Shopping after Success
    const continueShopBtn = document.getElementById('btn-continue-shopping');
    if (continueShopBtn) {
      continueShopBtn.addEventListener('click', () => {
        document.getElementById('success-modal-backdrop').style.display = 'none';
      });
    }
  }

  setCurrency(curr) {
    this.currency = curr;
    localStorage.setItem('pozitron_currency', curr);
    document.querySelectorAll('.curr-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-currency') === curr);
    });
    this.updateCartUI();
    this.fetchProducts();
  }

  formatPrice(priceUSD, priceTRY) {
    if (this.currency === 'TRY') {
      return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(priceTRY);
    }
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(priceUSD);
  }

  formatImgUrl(url) {
    if (!url) return './assets/products/motor.png';
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) return url;
    if (url.startsWith('/assets/')) return '.' + url;
    if (url.startsWith('assets/')) return './' + url;
    return url;
  }

  getStaticData() {
    return window.__POZITRON_DATA__ || { categories: [], brands: [], products: [], reviews: [] };
  }

  queryStaticProducts(params) {
    const staticData = this.getStaticData();
    let items = [...(staticData.products || [])];

    // 1. Search Query
    const q = (params.get('q') || '').trim().toLowerCase();
    if (q) {
      items = items.filter(p => {
        const nameTR = (p.name_tr || '').toLowerCase();
        const nameEN = (p.name_en || '').toLowerCase();
        const brand = (p.brand || '').toLowerCase();
        const sku = (p.sku || '').toLowerCase();
        const descTR = (p.description_tr || '').toLowerCase();
        const descEN = (p.description_en || '').toLowerCase();
        const tags = Array.isArray(p.tags) ? p.tags.join(' ').toLowerCase() : '';
        return nameTR.includes(q) || nameEN.includes(q) || brand.includes(q) || sku.includes(q) || tags.includes(q) || descTR.includes(q) || descEN.includes(q);
      });
    }

    // 2. Category
    const category = params.get('category');
    if (category && category !== 'all') {
      items = items.filter(p => p.category_id === category);
    }

    // 3. Brand
    const brand = params.get('brand');
    if (brand && brand !== 'all') {
      items = items.filter(p => p.brand === brand);
    }

    // 4. Voltage / spec
    const voltage = params.get('voltage');
    if (voltage && voltage !== 'all') {
      items = items.filter(p => {
        const specsText = JSON.stringify(p.specs || {}).toLowerCase() + (p.tags ? p.tags.join(' ').toLowerCase() : '');
        return specsText.includes(voltage.toLowerCase());
      });
    }

    // 5. In Stock
    if (params.get('in_stock') === '1') {
      items = items.filter(p => p.stock > 0);
    }

    // 6. Bestseller
    if (params.get('bestseller') === '1') {
      items = items.filter(p => p.is_bestseller === 1);
    }

    // 7. Price
    const minPrice = parseFloat(params.get('min_price'));
    const maxPrice = parseFloat(params.get('max_price'));
    const curr = params.get('currency') || this.currency;

    if (!isNaN(minPrice) && minPrice > 0) {
      items = items.filter(p => (curr === 'TRY' ? p.price_try : p.price_usd) >= minPrice);
    }
    if (!isNaN(maxPrice) && maxPrice > 0) {
      items = items.filter(p => (curr === 'TRY' ? p.price_try : p.price_usd) <= maxPrice);
    }

    // 8. Sorting
    const sort = params.get('sort') || 'popular';
    if (sort === 'price_asc') {
      items.sort((a, b) => (curr === 'TRY' ? a.price_try - b.price_try : a.price_usd - b.price_usd));
    } else if (sort === 'price_desc') {
      items.sort((a, b) => (curr === 'TRY' ? b.price_try - a.price_try : b.price_usd - a.price_usd));
    } else if (sort === 'rating') {
      items.sort((a, b) => (b.rating || 0) - (a.rating || 0) || (b.review_count || 0) - (a.review_count || 0));
    } else if (sort === 'newest') {
      items.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
    } else if (sort === 'discount') {
      items.sort((a, b) => (b.discount_pct || 0) - (a.discount_pct || 0));
    } else {
      // popular / default
      items.sort((a, b) => (b.is_bestseller || 0) - (a.is_bestseller || 0) || (b.rating || 0) - (a.rating || 0));
    }

    const total = items.length;
    const page = Math.max(1, parseInt(params.get('page') || '1'));
    const limit = Math.min(100, Math.max(1, parseInt(params.get('limit') || '24')));
    const offset = (page - 1) * limit;
    const slice = items.slice(offset, offset + limit);

    return {
      products: slice,
      total: total,
      page: page,
      limit: limit,
      total_pages: Math.ceil(total / limit) || 1
    };
  }

  async loadCategories() {
    try {
      if (window.__POZITRON_DATA__ && window.__POZITRON_DATA__.categories && window.__POZITRON_DATA__.categories.length > 0) {
        this.categories = window.__POZITRON_DATA__.categories;
      } else {
        const res = await fetch(`${this.apiBase}/categories`);
        const data = await res.json();
        this.categories = data.categories || [];
      }
    } catch (e) {
      if (window.__POZITRON_DATA__ && window.__POZITRON_DATA__.categories) {
        this.categories = window.__POZITRON_DATA__.categories;
      }
    }
    this.renderCategoriesPills();
    this.renderCategorySidebar();
  }

  async loadBrands() {
    try {
      if (window.__POZITRON_DATA__ && window.__POZITRON_DATA__.brands && window.__POZITRON_DATA__.brands.length > 0) {
        this.brands = window.__POZITRON_DATA__.brands;
      } else {
        const res = await fetch(`${this.apiBase}/brands`);
        const data = await res.json();
        this.brands = data.brands || [];
      }
    } catch (e) {
      if (window.__POZITRON_DATA__ && window.__POZITRON_DATA__.brands) {
        this.brands = window.__POZITRON_DATA__.brands;
      }
    }
    this.renderBrandSidebar();
  }

  renderCategoriesPills() {
    const bar = document.getElementById('category-pills-bar');
    if (!bar) return;

    const lang = window.i18n.currentLang;
    let html = `
      <button type="button" class="category-pill-btn ${this.filters.category === 'all' ? 'active' : ''}" data-cat="all">
        <span>⚡</span> <span>${lang === 'tr' ? 'Tüm Parçalar (500)' : 'All 500 Parts'}</span>
      </button>
    `;

    this.categories.forEach(cat => {
      const name = lang === 'tr' ? cat.name_tr : cat.name_en;
      const isActive = this.filters.category === cat.id ? 'active' : '';
      html += `
        <button type="button" class="category-pill-btn ${isActive}" data-cat="${cat.id}">
          <span>${cat.icon || '📦'}</span> <span>${name}</span>
        </button>
      `;
    });

    bar.innerHTML = html;

    bar.querySelectorAll('.category-pill-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const cat = e.currentTarget.getAttribute('data-cat');
        this.filters.category = cat;
        this.filters.page = 1;
        this.renderCategoriesPills();
        this.renderCategorySidebar();
        this.fetchProducts();
      });
    });
  }

  renderCategorySidebar() {
    const list = document.getElementById('category-filter-list');
    if (!list) return;

    const lang = window.i18n.currentLang;
    let html = `
      <label class="custom-checkbox">
        <input type="radio" name="sidebar-cat" value="all" ${this.filters.category === 'all' ? 'checked' : ''}>
        <span class="checkmark"></span>
        <span>${lang === 'tr' ? 'Tüm Kategoriler' : 'All Categories'}</span>
        <span class="filter-count">500</span>
      </label>
    `;

    this.categories.forEach(cat => {
      const name = lang === 'tr' ? cat.name_tr : cat.name_en;
      const isChecked = this.filters.category === cat.id ? 'checked' : '';
      html += `
        <label class="custom-checkbox">
          <input type="radio" name="sidebar-cat" value="${cat.id}" ${isChecked}>
          <span class="checkmark"></span>
          <span>${name}</span>
          <span class="filter-count">${cat.item_count || ''}</span>
        </label>
      `;
    });

    list.innerHTML = html;

    list.querySelectorAll('input[name="sidebar-cat"]').forEach(input => {
      input.addEventListener('change', (e) => {
        this.filters.category = e.target.value;
        this.filters.page = 1;
        this.renderCategoriesPills();
        this.fetchProducts();
      });
    });
  }

  renderBrandSidebar() {
    const list = document.getElementById('brand-filter-list');
    if (!list) return;

    let html = `
      <label class="custom-checkbox">
        <input type="radio" name="sidebar-brand" value="all" ${this.filters.brand === 'all' ? 'checked' : ''}>
        <span class="checkmark"></span>
        <span>${window.i18n.t('all')}</span>
      </label>
    `;

    this.brands.forEach(b => {
      const isChecked = this.filters.brand === b ? 'checked' : '';
      html += `
        <label class="custom-checkbox">
          <input type="radio" name="sidebar-brand" value="${b}" ${isChecked}>
          <span class="checkmark"></span>
          <span>${b}</span>
        </label>
      `;
    });

    list.innerHTML = html;

    list.querySelectorAll('input[name="sidebar-brand"]').forEach(input => {
      input.addEventListener('change', (e) => {
        this.filters.brand = e.target.value;
        this.filters.page = 1;
        this.fetchProducts();
      });
    });
  }

  async fetchProducts() {
    const grid = document.getElementById('product-grid');
    const emptyState = document.getElementById('empty-state');
    const countText = document.getElementById('catalog-count-text');

    if (!grid) return;

    // Build URL params
    const params = new URLSearchParams({
      page: this.filters.page,
      limit: this.filters.limit,
      sort: this.filters.sort,
      currency: this.currency
    });

    if (this.filters.q) params.set('q', this.filters.q);
    if (this.filters.category !== 'all') params.set('category', this.filters.category);
    if (this.filters.brand !== 'all') params.set('brand', this.filters.brand);
    if (this.filters.voltage !== 'all') params.set('voltage', this.filters.voltage);
    if (this.filters.in_stock === '1') params.set('in_stock', '1');
    if (this.filters.bestseller === '1') params.set('bestseller', '1');
    if (this.filters.min_price) params.set('min_price', this.filters.min_price);
    if (this.filters.max_price) params.set('max_price', this.filters.max_price);

    try {
      let data = null;
      try {
        const res = await fetch(`${this.apiBase}/products?${params.toString()}`);
        if (res.ok) {
          data = await res.json();
        }
      } catch (err) {
        // Fallback to client-side static database
      }

      if (!data || !data.products) {
        data = this.queryStaticProducts(params);
      }

      const products = data.products || [];
      const total = data.total || 0;

      if (countText) {
        countText.textContent = window.i18n.t('showing_items', { count: total });
      }

      this.updateDynamicSeoMeta();

      if (products.length === 0) {
        grid.innerHTML = '';
        emptyState.style.display = 'block';
        document.getElementById('pagination-bar').innerHTML = '';
        return;
      }

      emptyState.style.display = 'none';
      this.renderProductCards(products, grid);
      this.renderPagination(data.page, data.total_pages);

    } catch (e) {
      console.error("Error fetching products", e);
    }
  }

  renderProductCards(products, grid) {
    const lang = window.i18n.currentLang;
    let html = '';

    products.forEach(p => {
      const name = lang === 'tr' ? p.name_tr : p.name_en;
      const priceFormatted = this.formatPrice(p.price_usd, p.price_try);
      
      let origPriceHtml = '';
      if (p.discount_pct > 0) {
        const origUSD = p.price_usd * (1 + p.discount_pct / 100);
        const origTRY = p.price_try * (1 + p.discount_pct / 100);
        origPriceHtml = `<span class="original-price">${this.formatPrice(origUSD, origTRY)}</span>`;
      }

      // Specs chips
      let specsHtml = '';
      if (p.specs) {
        const keys = Object.keys(p.specs).slice(0, 2);
        keys.forEach(k => {
          specsHtml += `<span class="spec-chip">${p.specs[k]}</span>`;
        });
      }

      // Badges
      let badgeHtml = '';
      if (p.discount_pct > 0) {
        badgeHtml = `<span class="card-badge badge-sale">-%${p.discount_pct}</span>`;
      } else if (p.is_bestseller) {
        badgeHtml = `<span class="card-badge badge-bestseller">TOP SELLER</span>`;
      }

      html += `
        <article class="product-card" data-id="${p.id}" data-slug="${p.slug}">
          <div class="card-media-wrap">
            ${badgeHtml}
            <img src="${this.formatImgUrl(p.image_url)}" alt="${name}" class="card-product-img" loading="lazy">
            <button type="button" class="card-quick-view-btn" data-action="quickview" data-id="${p.id}" title="${window.i18n.t('quick_view')}">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
            </button>
          </div>

          <div class="card-body">
            <div class="card-brand-row">
              <span class="card-brand">${p.brand}</span>
              <span class="card-stock-status">
                <span class="card-stock-dot"></span>
                <span>${p.stock > 0 ? window.i18n.t('in_stock') : window.i18n.t('out_of_stock')}</span>
              </span>
            </div>

            <h3 class="card-title" data-action="quickview" data-id="${p.id}">${name}</h3>

            <div class="card-specs-row">
              ${specsHtml}
            </div>

            <div class="card-rating-row">
              <span class="rating-stars">★ ${p.rating}</span>
              <span class="rating-count">(${p.review_count || 12})</span>
            </div>

            <div class="card-footer-row">
              <div class="price-box">
                ${origPriceHtml}
                <span class="current-price">${priceFormatted}</span>
              </div>
              <button type="button" class="btn-card-add" data-action="add-to-cart" data-id="${p.id}">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
                  <line x1="3" y1="6" x2="21" y2="6"></line>
                  <path d="M16 10a4 4 0 0 1-8 0"></path>
                </svg>
                <span>${window.i18n.t('add_to_cart')}</span>
              </button>
            </div>

          </div>
        </article>
      `;
    });

    grid.innerHTML = html;

    // Attach card event listeners
    grid.querySelectorAll('[data-action="add-to-cart"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const pid = e.currentTarget.getAttribute('data-id');
        const prod = products.find(x => x.id === pid);
        if (prod) this.addToCart(prod);
      });
    });

    grid.querySelectorAll('[data-action="quickview"]').forEach(el => {
      el.addEventListener('click', (e) => {
        const pid = e.currentTarget.getAttribute('data-id');
        this.openProductModal(pid);
      });
    });
  }

  renderPagination(currentPage, totalPages) {
    const bar = document.getElementById('pagination-bar');
    if (!bar) return;

    if (totalPages <= 1) {
      bar.innerHTML = '';
      return;
    }

    let html = '';
    if (currentPage > 1) {
      html += `<button type="button" class="page-btn" data-page="${currentPage - 1}">‹</button>`;
    }

    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, currentPage + 2);

    for (let i = start; i <= end; i++) {
      html += `<button type="button" class="page-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }

    if (currentPage < totalPages) {
      html += `<button type="button" class="page-btn" data-page="${currentPage + 1}">›</button>`;
    }

    bar.innerHTML = html;

    bar.querySelectorAll('.page-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const page = parseInt(e.currentTarget.getAttribute('data-page'));
        this.filters.page = page;
        this.fetchProducts();
        document.getElementById('catalog-section').scrollIntoView({ behavior: 'smooth' });
      });
    });
  }

  async handleLiveSearch(query) {
    const box = document.getElementById('search-suggestions');
    if (!box) return;

    if (!query || query.length < 2) {
      box.style.display = 'none';
      return;
    }

    let items = [];
    try {
      const res = await fetch(`${this.apiBase}/products?q=${encodeURIComponent(query)}&limit=5&currency=${this.currency}`);
      if (res.ok) {
        const data = await res.json();
        items = data.products || [];
      }
    } catch (e) {
      // Fallback
    }

    if (items.length === 0) {
      const staticData = this.getStaticData();
      const q = query.toLowerCase();
      items = (staticData.products || []).filter(p => {
        const nameTR = (p.name_tr || '').toLowerCase();
        const nameEN = (p.name_en || '').toLowerCase();
        const brand = (p.brand || '').toLowerCase();
        const sku = (p.sku || '').toLowerCase();
        return nameTR.includes(q) || nameEN.includes(q) || brand.includes(q) || sku.includes(q);
      }).slice(0, 5);
    }

    if (items.length === 0) {
      box.style.display = 'none';
      return;
    }

    const lang = window.i18n.currentLang;
    let html = '';
    items.forEach(p => {
      const name = lang === 'tr' ? p.name_tr : p.name_en;
      const price = this.formatPrice(p.price_usd, p.price_try);
      html += `
        <div class="suggestion-item" data-id="${p.id}">
          <img src="${this.formatImgUrl(p.image_url)}" alt="${name}" class="suggestion-img">
          <div class="suggestion-info">
            <div class="suggestion-title">${name}</div>
            <div class="suggestion-meta">${p.brand} • ${p.category_name_tr || p.category_id}</div>
          </div>
          <div class="suggestion-price">${price}</div>
        </div>
      `;
    });

    box.innerHTML = html;
    box.style.display = 'block';

    box.querySelectorAll('.suggestion-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const pid = e.currentTarget.getAttribute('data-id');
        this.hideSuggestions();
        this.openProductModal(pid);
      });
    });
  }

  hideSuggestions() {
    const box = document.getElementById('search-suggestions');
    if (box) box.style.display = 'none';
  }

  // ==========================================
  // CART OPERATIONS
  // ==========================================
  addToCart(product, quantity = 1) {
    const existing = this.cart.find(item => item.id === product.id);
    if (existing) {
      existing.quantity += quantity;
    } else {
      this.cart.push({
        id: product.id,
        name_en: product.name_en,
        name_tr: product.name_tr,
        brand: product.brand,
        price_usd: product.price_usd,
        price_try: product.price_try,
        image_url: product.image_url,
        quantity: quantity
      });
    }

    this.saveCart();
    this.updateCartUI();
    this.openCartDrawer();
    this.showToast(`${window.i18n.currentLang === 'tr' ? product.name_tr : product.name_en} sepete eklendi!`, 'success');
  }

  updateQuantity(productId, delta) {
    const item = this.cart.find(i => i.id === productId);
    if (!item) return;

    item.quantity += delta;
    if (item.quantity <= 0) {
      this.cart = this.cart.filter(i => i.id !== productId);
    }

    this.saveCart();
    this.updateCartUI();
  }

  removeFromCart(productId) {
    this.cart = this.cart.filter(i => i.id !== productId);
    this.saveCart();
    this.updateCartUI();
  }

  saveCart() {
    localStorage.setItem('pozitron_cart', JSON.stringify(this.cart));
  }

  updateCartUI() {
    const badge = document.getElementById('cart-badge-count');
    const drawerCount = document.getElementById('cart-drawer-count');
    const container = document.getElementById('cart-items-container');
    const subtotalEl = document.getElementById('cart-subtotal-val');
    const discountEl = document.getElementById('cart-discount-val');
    const discountRow = document.getElementById('cart-discount-row');
    const shippingEl = document.getElementById('cart-shipping-val');
    const grandtotalEl = document.getElementById('cart-grandtotal-val');
    const progressFill = document.getElementById('shipping-progress-fill');
    const progressText = document.getElementById('free-shipping-text');

    const totalItems = this.cart.reduce((sum, i) => sum + i.quantity, 0);
    if (badge) badge.textContent = totalItems;
    if (drawerCount) drawerCount.textContent = `(${totalItems} ${window.i18n.currentLang === 'tr' ? 'Ürün' : 'Items'})`;

    let subtotalUSD = 0;
    let subtotalTRY = 0;

    if (!container) return;

    if (this.cart.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding: 40px 10px; color: var(--text-muted);">
          <div style="font-size: 2.5rem; margin-bottom: 10px;">🛒</div>
          <p>${window.i18n.currentLang === 'tr' ? 'Sepetiniz şu an boş.' : 'Your cart is empty.'}</p>
        </div>
      `;
      if (subtotalEl) subtotalEl.textContent = this.formatPrice(0, 0);
      if (grandtotalEl) grandtotalEl.textContent = this.formatPrice(0, 0);
      if (progressFill) progressFill.style.width = '0%';
      return;
    }

    const lang = window.i18n.currentLang;
    let html = '';

    this.cart.forEach(item => {
      const name = lang === 'tr' ? item.name_tr : item.name_en;
      const itemTotalUSD = item.price_usd * item.quantity;
      const itemTotalTRY = item.price_try * item.quantity;
      subtotalUSD += itemTotalUSD;
      subtotalTRY += itemTotalTRY;

      html += `
        <div class="cart-item-row">
          <img src="${this.formatImgUrl(item.image_url)}" alt="${name}" class="cart-item-img">
          <div class="cart-item-details">
            <div class="cart-item-name">${name}</div>
            <div class="cart-item-brand">${item.brand}</div>
            <div class="cart-item-bottom">
              <div class="qty-stepper">
                <button type="button" class="qty-btn" data-action="dec" data-id="${item.id}">-</button>
                <span class="qty-value">${item.quantity}</span>
                <button type="button" class="qty-btn" data-action="inc" data-id="${item.id}">+</button>
              </div>
              <div class="cart-item-price">${this.formatPrice(itemTotalUSD, itemTotalTRY)}</div>
              <button type="button" class="btn-remove-item" data-action="del" data-id="${item.id}">✕</button>
            </div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // Attach stepper listeners
    container.querySelectorAll('[data-action="inc"]').forEach(b => {
      b.addEventListener('click', () => this.updateQuantity(b.getAttribute('data-id'), 1));
    });
    container.querySelectorAll('[data-action="dec"]').forEach(b => {
      b.addEventListener('click', () => this.updateQuantity(b.getAttribute('data-id'), -1));
    });
    container.querySelectorAll('[data-action="del"]').forEach(b => {
      b.addEventListener('click', () => this.removeFromCart(b.getAttribute('data-id')));
    });

    // Discount & Shipping
    let discountUSD = 0;
    let discountTRY = 0;
    if (this.appliedCoupon) {
      if (this.appliedCoupon.discount_type === 'percent') {
        discountUSD = subtotalUSD * (this.appliedCoupon.discount_value / 100);
        discountTRY = subtotalTRY * (this.appliedCoupon.discount_value / 100);
      } else {
        discountUSD = this.appliedCoupon.discount_usd || 10;
        discountTRY = this.appliedCoupon.discount_try || 350;
      }
      if (discountRow) discountRow.style.display = 'flex';
      if (discountEl) discountEl.textContent = `-${this.formatPrice(discountUSD, discountTRY)}`;
    } else {
      if (discountRow) discountRow.style.display = 'none';
    }

    const freeShippingTargetTRY = 1500;
    const isFreeShipping = subtotalTRY >= freeShippingTargetTRY;
    const shippingFeeUSD = isFreeShipping ? 0 : 9.99;
    const shippingFeeTRY = isFreeShipping ? 0 : 350;

    if (shippingEl) {
      shippingEl.textContent = isFreeShipping ? (lang === 'tr' ? 'ÜCRETSİZ' : 'FREE') : this.formatPrice(shippingFeeUSD, shippingFeeTRY);
    }

    const grandUSD = Math.max(0, subtotalUSD - discountUSD + shippingFeeUSD);
    const grandTRY = Math.max(0, subtotalTRY - discountTRY + shippingFeeTRY);

    if (subtotalEl) subtotalEl.textContent = this.formatPrice(subtotalUSD, subtotalTRY);
    if (grandtotalEl) grandtotalEl.textContent = this.formatPrice(grandUSD, grandTRY);

    // Free shipping progress bar
    if (progressFill && progressText) {
      const pct = Math.min(100, Math.round((subtotalTRY / freeShippingTargetTRY) * 100));
      progressFill.style.width = `${pct}%`;
      if (isFreeShipping) {
        progressText.innerHTML = window.i18n.t('free_shipping_earned');
      } else {
        const remaining = this.formatPrice((freeShippingTargetTRY - subtotalTRY) / 35.5, freeShippingTargetTRY - subtotalTRY);
        progressText.innerHTML = `${remaining} daha ekleyin, <strong>Ücretsiz Kargo</strong> kazanın!`;
      }
    }
  }

  openCartDrawer() {
    const backdrop = document.getElementById('cart-backdrop');
    if (backdrop) backdrop.classList.add('open');
  }

  closeCartDrawer() {
    const backdrop = document.getElementById('cart-backdrop');
    if (backdrop) backdrop.classList.remove('open');
  }

  async handleApplyCoupon() {
    const input = document.getElementById('coupon-input');
    const feedback = document.getElementById('coupon-feedback');
    if (!input) return;

    const code = input.value.trim().toUpperCase();
    if (!code) return;

    let subtotalUSD = 0;
    let subtotalTRY = 0;
    this.cart.forEach(i => {
      subtotalUSD += i.price_usd * i.quantity;
      subtotalTRY += i.price_try * i.quantity;
    });

    let data = null;
    try {
      const res = await fetch(`${this.apiBase}/coupons/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, subtotal_usd: subtotalUSD, subtotal_try: subtotalTRY })
      });
      if (res.ok) data = await res.json();
    } catch (e) {
      // static fallback
    }

    if (!data) {
      const upper = code.toUpperCase();
      if (upper === 'POZITRON10') {
        data = { valid: true, discount_type: 'percent', discount_value: 10, discount_usd: subtotalUSD * 0.10, discount_try: subtotalTRY * 0.10, code: upper };
      } else if (upper === 'FPV2026') {
        data = { valid: true, discount_type: 'percent', discount_value: 15, discount_usd: subtotalUSD * 0.15, discount_try: subtotalTRY * 0.15, code: upper };
      } else if (upper === 'DRONE50') {
        data = { valid: true, discount_type: 'fixed', discount_value: 50, discount_usd: 1.4, discount_try: 50, code: upper };
      } else {
        data = { valid: false, error: 'Geçersiz kupon kodu. (Dene: POZITRON10, FPV2026)' };
      }
    }

    if (data.valid) {
      this.appliedCoupon = data;
      feedback.innerHTML = `<span class="text-success">✓ %${data.discount_value || 10} İndirim uygulandı!</span>`;
      this.updateCartUI();
    } else {
      feedback.innerHTML = `<span class="text-danger">${data.error || 'Geçersiz kupon kodu.'}</span>`;
    }
  }

  // ==========================================
  // AUTHENTICATION
  // ==========================================
  openAuthModal() {
    document.getElementById('auth-modal-backdrop').style.display = 'flex';
  }

  closeAuthModal() {
    document.getElementById('auth-modal-backdrop').style.display = 'none';
  }

  updateUserUI() {
    const nameEl = document.getElementById('user-display-name');
    const dropName = document.getElementById('user-name-text');
    const dropEmail = document.getElementById('user-email-text');
    const avatarImg = document.getElementById('user-avatar-img');

    if (this.user) {
      if (nameEl) nameEl.textContent = this.user.full_name.split(' ')[0];
      if (dropName) dropName.textContent = this.user.full_name;
      if (dropEmail) dropEmail.textContent = this.user.email;
      if (avatarImg) avatarImg.src = this.user.avatar_url;
    } else {
      if (nameEl) nameEl.textContent = window.i18n.t('nav_login');
    }
  }

  async handleGoogleAuth() {
    try {
      let data = null;
      const email = "pilot.pozitron@gmail.com";
      const full_name = "Kaptan Pilot Ahmet";
      try {
        const res = await fetch(`${this.apiBase}/auth/google`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, full_name })
        });
        if (res.ok) data = await res.json();
      } catch (err) {}

      if (!data || !data.success) {
        data = {
          success: true,
          user: {
            id: "usr_google_2026",
            email: email,
            full_name: full_name,
            avatar_url: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&q=80",
            provider: "gmail"
          }
        };
      }

      this.user = data.user;
      localStorage.setItem('pozitron_user', JSON.stringify(this.user));
      this.updateUserUI();
      this.closeAuthModal();
      this.showToast(`Hoş geldiniz, ${this.user.full_name}! (Google)`, 'success');
    } catch (e) {
      this.showToast("Google girişi başarısız.", 'error');
    }
  }

  async handleManualLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    const err = document.getElementById('login-error-msg');

    try {
      let data = null;
      try {
        const res = await fetch(`${this.apiBase}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        if (res.ok) data = await res.json();
      } catch (e) {}

      if (!data || !data.success) {
        // Fallback for static client
        const storedUsers = JSON.parse(localStorage.getItem('pozitron_all_users') || '[]');
        const match = storedUsers.find(u => u.email === email && u.password === password);
        if (match || password.length >= 6) {
          data = {
            success: true,
            user: match || {
              id: "usr_" + Math.random().toString(36).substr(2, 8),
              email: email,
              full_name: email.split('@')[0].toUpperCase(),
              avatar_url: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&q=80",
              provider: "manual"
            }
          };
        }
      }

      if (data && data.success) {
        this.user = data.user;
        localStorage.setItem('pozitron_user', JSON.stringify(this.user));
        this.updateUserUI();
        this.closeAuthModal();
        this.showToast(`Hoş geldiniz, ${this.user.full_name}!`, 'success');
      } else {
        err.textContent = (data && data.error) || 'Giriş yapılamadı. Şifre en az 6 karakter olmalıdır.';
        err.style.display = 'block';
      }
    } catch (e) {
      err.textContent = 'Giriş işlemi tamamlanamadı.';
      err.style.display = 'block';
    }
  }

  async handleManualRegister(e) {
    e.preventDefault();
    const full_name = document.getElementById('reg-name').value;
    const email = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;
    const err = document.getElementById('reg-error-msg');

    try {
      let data = null;
      try {
        const res = await fetch(`${this.apiBase}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ full_name, email, password })
        });
        if (res.ok) data = await res.json();
      } catch (e) {}

      if (!data || !data.success) {
        // Fallback for static client
        const newUser = {
          id: "usr_" + Math.random().toString(36).substr(2, 8),
          email: email,
          password: password,
          full_name: full_name,
          avatar_url: "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&q=80",
          provider: "manual"
        };
        const storedUsers = JSON.parse(localStorage.getItem('pozitron_all_users') || '[]');
        storedUsers.push(newUser);
        localStorage.setItem('pozitron_all_users', JSON.stringify(storedUsers));
        data = { success: true, user: newUser };
      }

      if (data && data.success) {
        this.user = data.user;
        localStorage.setItem('pozitron_user', JSON.stringify(this.user));
        this.updateUserUI();
        this.closeAuthModal();
        this.showToast('Hesabınız başarıyla oluşturuldu!', 'success');
      } else {
        err.textContent = (data && data.error) || 'Kayıt başarısız.';
        err.style.display = 'block';
      }
    } catch (e) {
      err.textContent = 'Kayıt işlemi tamamlanamadı.';
      err.style.display = 'block';
    }
  }

  handleLogout() {
    this.user = null;
    localStorage.removeItem('pozitron_user');
    this.updateUserUI();
    document.getElementById('user-dropdown-menu').style.display = 'none';
    this.showToast('Başarıyla çıkış yapıldı.', 'success');
  }

  // ==========================================
  // CHECKOUT & 3D SECURE PAYMENT
  // ==========================================
  openCheckoutModal() {
    const modal = document.getElementById('checkout-modal-backdrop');
    if (!modal) return;

    // Pre-fill user data if logged in
    if (this.user) {
      document.getElementById('chk-name').value = this.user.full_name || '';
      document.getElementById('chk-email').value = this.user.email || '';
      document.getElementById('chk-phone').value = this.user.phone || '+90 555 123 4567';
      document.getElementById('chk-address').value = this.user.address || 'Teknopark İstanbul No: 42';
      document.getElementById('chk-city').value = this.user.city || 'İstanbul';
    }

    // Update total price
    let subUSD = 0, subTRY = 0;
    this.cart.forEach(i => {
      subUSD += i.price_usd * i.quantity;
      subTRY += i.price_try * i.quantity;
    });

    const isFree = subTRY >= 1500;
    const grandUSD = subUSD + (isFree ? 0 : 9.99);
    const grandTRY = subTRY + (isFree ? 0 : 350);

    document.getElementById('checkout-total-val').textContent = this.formatPrice(grandUSD, grandTRY);
    modal.style.display = 'flex';
  }

  closeCheckoutModal() {
    document.getElementById('checkout-modal-backdrop').style.display = 'none';
  }

  autofillTestCard() {
    document.getElementById('chk-name').value = "Pilot Test Kullanıcı";
    document.getElementById('chk-email').value = "pilot.test@pozitronmarket.com";
    document.getElementById('chk-phone').value = "+90 555 987 6543";
    document.getElementById('chk-address').value = "ODTÜ Teknokent Bilişim Vadisi No: 18";
    document.getElementById('chk-city').value = "Ankara";
    document.getElementById('chk-country').value = "Turkey";

    document.getElementById('card-holder-input').value = "PILOT TEST KULLANICI";
    document.getElementById('card-number-input').value = "4532 0123 4567 8910";
    document.getElementById('card-expiry-input').value = "12/28";
    document.getElementById('card-cvv-input').value = "543";

    // Update virtual card
    document.getElementById('preview-card-holder').textContent = "PILOT TEST KULLANICI";
    document.getElementById('preview-card-number').textContent = "4532 0123 4567 8910";
    document.getElementById('preview-card-expiry').textContent = "12/28";
    document.getElementById('preview-card-brand').textContent = "VISA";

    this.showToast("Test kartı bilgileri dolduruldu! ⚡", 'success');
  }

  handleCheckoutSubmit() {
    const name = document.getElementById('chk-name').value.trim();
    const email = document.getElementById('chk-email').value.trim();
    const phone = document.getElementById('chk-phone').value.trim();
    const address = document.getElementById('chk-address').value.trim();
    const city = document.getElementById('chk-city').value.trim();
    const country = document.getElementById('chk-country').value.trim();

    const cardHolder = document.getElementById('card-holder-input').value.trim();
    const cardNumber = document.getElementById('card-number-input').value.replace(/\s/g, '');
    const cardExpiry = document.getElementById('card-expiry-input').value.trim();
    const cardCvv = document.getElementById('card-cvv-input').value.trim();

    const err = document.getElementById('checkout-error-msg');

    if (!name || !email || !phone || !address || !city) {
      err.textContent = "Lütfen tüm teslimat bilgilerini eksiksiz doldurun.";
      err.style.display = 'block';
      return;
    }

    if (!cardNumber || cardNumber.length < 13 || !cardExpiry || !cardCvv) {
      err.textContent = "Lütfen kredi kartı bilgilerini doğru formatta girin.";
      err.style.display = 'block';
      return;
    }

    err.style.display = 'none';

    // Store payload and open OTP simulation modal
    this.pendingOrderData = {
      items: this.cart,
      customer_name: name,
      customer_email: email,
      customer_phone: phone,
      shipping_address: address,
      city: city,
      country: country,
      currency: this.currency,
      coupon_code: this.appliedCoupon ? this.appliedCoupon.code : '',
      card_number: cardNumber,
      card_holder: cardHolder,
      card_expiry: cardExpiry,
      card_cvv: cardCvv,
      user_id: this.user ? this.user.id : null
    };

    // Open 3D Secure OTP Modal
    this.closeCheckoutModal();
    document.getElementById('otp-modal-backdrop').style.display = 'flex';
  }

  async handleOtpConfirm() {
    const otpInput = document.getElementById('otp-code-input').value.trim();
    const otpErr = document.getElementById('otp-error-msg');

    if (otpInput !== '554433' && otpInput.length !== 6) {
      otpErr.textContent = "Geçersiz SMS kodu. Lütfen 554433 kodunu girin.";
      otpErr.style.display = 'block';
      return;
    }

    otpErr.style.display = 'none';

    let order = null;
    try {
      const res = await fetch(`${this.apiBase}/payment/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.pendingOrderData)
      });
      if (res.ok) order = await res.json();
    } catch (e) {
      // static fallback
    }

    if (!order || !order.success) {
      const orderNum = 'PZTR-2026-' + Math.floor(10000 + Math.random() * 90000);
      let subUSD = 0, subTRY = 0;
      (this.pendingOrderData.items || []).forEach(i => {
        subUSD += i.price_usd * i.quantity;
        subTRY += i.price_try * i.quantity;
      });
      order = {
        success: true,
        order_number: orderNum,
        tracking_number: 'TR-YURTICI-' + Math.floor(10000000 + Math.random() * 90000000),
        transaction_id: 'TXN_' + Math.random().toString(36).substr(2, 10).toUpperCase(),
        card_brand: 'Mastercard / Visa',
        card_last4: this.pendingOrderData.card_number ? this.pendingOrderData.card_number.slice(-4) : '4242',
        shipping_address: `${this.pendingOrderData.shipping_address}, ${this.pendingOrderData.city} / ${this.pendingOrderData.country}`,
        total_usd: subUSD,
        total_try: subTRY,
        status: 'confirmed',
        created_at: new Date().toISOString()
      };
      const prevOrders = JSON.parse(localStorage.getItem('pozitron_orders') || '[]');
      prevOrders.unshift(order);
      localStorage.setItem('pozitron_orders', JSON.stringify(prevOrders));
    }

    if (order && order.success) {
      // Clear cart
      this.cart = [];
      this.appliedCoupon = null;
      this.saveCart();
      this.updateCartUI();

      // Close OTP modal
      document.getElementById('otp-modal-backdrop').style.display = 'none';

      // Render Invoice Receipt Modal
      this.renderOrderReceipt(order);
      document.getElementById('success-modal-backdrop').style.display = 'flex';
    } else {
      otpErr.textContent = (order && order.error) || "Ödeme onaylanamadı.";
      otpErr.style.display = 'block';
    }
  }

  renderOrderReceipt(order) {
    const card = document.getElementById('order-receipt-card');
    if (!card) return;

    card.innerHTML = `
      <div class="receipt-row">
        <span>Sipariş No:</span>
        <strong>${order.order_number}</strong>
      </div>
      <div class="receipt-row">
        <span>Kargo Takip No:</span>
        <strong>${order.tracking_number}</strong>
      </div>
      <div class="receipt-row">
        <span>İşlem Kodu (TXN):</span>
        <strong>${order.transaction_id}</strong>
      </div>
      <div class="receipt-row">
        <span>Ödeme Kartı:</span>
        <strong>${order.card_brand} (•••• ${order.card_last4})</strong>
      </div>
      <div class="receipt-row">
        <span>Teslimat Adresi:</span>
        <span>${order.shipping_address}</span>
      </div>
      <div class="receipt-row" style="padding-top:8px; border-top:1px solid var(--border-subtle);">
        <span>Toplam Tutar:</span>
        <strong style="color:var(--brand-light); font-size:1.1rem;">${this.formatPrice(order.total_usd, order.total_try)}</strong>
      </div>
    `;
  }

  // ==========================================
  // PRODUCT QUICK VIEW MODAL
  // ==========================================
  async openProductModal(idOrSlug) {
    const modal = document.getElementById('product-modal-backdrop');
    const body = document.getElementById('product-modal-body');
    if (!modal || !body) return;

    try {
      let p = null;
      try {
        const res = await fetch(`${this.apiBase}/products/${idOrSlug}`);
        if (res.ok) {
          const data = await res.json();
          p = data.product;
        }
      } catch (err) {}

      if (!p) {
        const staticData = this.getStaticData();
        p = (staticData.products || []).find(x => x.id === idOrSlug || x.slug === idOrSlug);
      }

      if (!p) return;

      const lang = window.i18n.currentLang;
      const name = lang === 'tr' ? p.name_tr : p.name_en;
      const desc = lang === 'tr' ? (p.description_tr || p.desc_tr) : (p.description_en || p.desc_en);
      const price = this.formatPrice(p.price_usd, p.price_try);

      let specsList = '';
      if (p.specs) {
        Object.entries(p.specs).forEach(([k, v]) => {
          specsList += `<li><strong>${k}:</strong> <span>${v}</span></li>`;
        });
      }

      const gallery = (p.gallery && p.gallery.length > 0) ? p.gallery : [p.image_url];
      let galleryHtml = '';
      if (gallery.length > 1) {
        galleryHtml = `
          <div style="display:flex; gap:8px; margin-top:12px; justify-content:center;">
            ${gallery.map((img, idx) => `
              <img src="${this.formatImgUrl(img)}" alt="${name} view ${idx + 1}" class="modal-thumb-img ${idx === 0 ? 'active' : ''}" style="width:52px; height:52px; object-fit:cover; border-radius:8px; border:2px solid ${idx === 0 ? 'var(--brand-primary)' : 'var(--border-subtle)'}; cursor:pointer; background:var(--bg-secondary); padding:2px;" data-src="${this.formatImgUrl(img)}">
            `).join('')}
          </div>
        `;
      }

      body.innerHTML = `
        <div style="display:grid; grid-template-columns: 1fr 1.2fr; gap: 32px; align-items:start;">
          <div>
            <div style="background:var(--bg-secondary); padding:20px; border-radius:12px; border:1px solid var(--border-subtle); display:flex; align-items:center; justify-content:center; min-height:280px;">
              <img id="modal-main-product-img" src="${this.formatImgUrl(p.image_url)}" alt="${name}" style="max-width:100%; max-height:280px; object-fit:contain; border-radius:8px;">
            </div>
            ${galleryHtml}
          </div>
          <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="font-size:0.8rem; font-weight:700; color:var(--brand-primary); text-transform:uppercase; letter-spacing:0.5px;">${p.brand} • SKU: ${p.sku}</div>
            <h2 style="font-size:1.35rem; font-weight:800; line-height:1.3; color:var(--text-primary); margin:0;">${name}</h2>
            <div style="display:flex; align-items:center; gap:8px; font-size:0.9rem;">
              <span style="color:#d97706; font-weight:700;">★ ${p.rating}</span>
              <span style="color:var(--text-muted);">(${p.review_count || 12} pilot değerlendirmesi)</span>
              <span style="color:var(--status-success); margin-left:auto; font-weight:600; font-size:0.82rem;">● Stokta Var (${p.stock} adet)</span>
            </div>
            <div style="font-size:1.6rem; font-weight:800; color:var(--brand-primary); margin:4px 0;">${price}</div>
            <p style="font-size:0.88rem; color:var(--text-secondary); line-height:1.6; margin:0;">${desc || ''}</p>
            
            <div style="background:var(--bg-secondary); padding:12px 16px; border-radius:8px; border:1px solid var(--border-subtle); margin:6px 0;">
              <strong style="font-size:0.85rem; display:block; margin-bottom:6px; color:var(--text-primary);">Teknik Özellikler:</strong>
              <ul style="list-style:none; display:grid; grid-template-columns:1fr 1fr; gap:6px; font-size:0.8rem; color:var(--text-secondary); padding:0; margin:0;">
                ${specsList}
              </ul>
            </div>

            <button type="button" class="btn-primary" id="btn-modal-add-cart" style="margin-top:8px; width:100%; justify-content:center; padding:12px;">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path><line x1="3" y1="6" x2="21" y2="6"></line><path d="M16 10a4 4 0 0 1-8 0"></path></svg>
              <span>Sepete Ekle (${price})</span>
            </button>
          </div>
        </div>
      `;

      modal.style.display = 'flex';

      // Thumbnail click handlers
      body.querySelectorAll('.modal-thumb-img').forEach(thumb => {
        thumb.addEventListener('click', (e) => {
          const src = e.currentTarget.getAttribute('data-src');
          const mainImg = document.getElementById('modal-main-product-img');
          if (mainImg) mainImg.src = src;
          body.querySelectorAll('.modal-thumb-img').forEach(t => t.style.borderColor = 'var(--border-subtle)');
          e.currentTarget.style.borderColor = 'var(--brand-primary)';
        });
      });

      document.getElementById('btn-modal-add-cart').addEventListener('click', () => {
        this.addToCart(p);
        this.closeProductModal();
      });

    } catch (e) {
      console.error(e);
    }
  }

  closeProductModal() {
    document.getElementById('product-modal-backdrop').style.display = 'none';
  }

  // ==========================================
  // DRONE COMPATIBILITY BUILDER
  // ==========================================
  async openBuilderModal() {
    const modal = document.getElementById('builder-modal-backdrop');
    const body = document.getElementById('builder-modal-body');
    if (!modal || !body) return;

    let motors = [], escs = [], props = [], batteries = [];
    const staticData = this.getStaticData();
    if (staticData && staticData.products && staticData.products.length > 0) {
      motors = staticData.products.filter(p => p.category_id === 'motors').slice(0, 30);
      escs = staticData.products.filter(p => p.category_id === 'esc').slice(0, 30);
      props = staticData.products.filter(p => p.category_id === 'propellers').slice(0, 30);
      batteries = staticData.products.filter(p => p.category_id === 'batteries_chargers').slice(0, 30);
    } else {
      try {
        const [mRes, eRes, pRes, bRes] = await Promise.all([
          fetch(`${this.apiBase}/products?category=motors&limit=30`),
          fetch(`${this.apiBase}/products?category=esc&limit=30`),
          fetch(`${this.apiBase}/products?category=propellers&limit=30`),
          fetch(`${this.apiBase}/products?category=batteries_chargers&limit=30`)
        ]);
        motors = (await mRes.json()).products || [];
        escs = (await eRes.json()).products || [];
        props = (await pRes.json()).products || [];
        batteries = (await bRes.json()).products || [];
      } catch (e) {}
    }

    const lang = window.i18n.currentLang;

    body.innerHTML = `
      <div class="builder-slots-grid">
        <div class="builder-slot-card">
          <span class="slot-label">1. Motor</span>
          <select id="slot-motor" class="slot-select">
            <option value="">Motor Seçin...</option>
            ${motors.map(m => `<option value="${m.id}">${m.brand} - ${lang === 'tr' ? m.name_tr : m.name_en}</option>`).join('')}
          </select>
        </div>

        <div class="builder-slot-card">
          <span class="slot-label">2. ESC Sürücü</span>
          <select id="slot-esc" class="slot-select">
            <option value="">ESC Seçin...</option>
            ${escs.map(e => `<option value="${e.id}">${e.brand} - ${lang === 'tr' ? e.name_tr : e.name_en}</option>`).join('')}
          </select>
        </div>

        <div class="builder-slot-card">
          <span class="slot-label">3. Pervane</span>
          <select id="slot-prop" class="slot-select">
            <option value="">Pervane Seçin...</option>
            ${props.map(pr => `<option value="${pr.id}">${pr.brand} - ${lang === 'tr' ? pr.name_tr : pr.name_en}</option>`).join('')}
          </select>
        </div>

        <div class="builder-slot-card">
          <span class="slot-label">4. LiPo Batarya</span>
          <select id="slot-battery" class="slot-select">
            <option value="">Batarya Seçin...</option>
            ${batteries.map(b => `<option value="${b.id}">${b.brand} - ${lang === 'tr' ? b.name_tr : b.name_en}</option>`).join('')}
          </select>
        </div>
      </div>

      <div class="builder-score-card">
        <div class="score-circle" id="builder-score-val">100</div>
        <div class="builder-feedback-wrap" id="builder-feedback-wrap">
          <strong id="builder-status-text" style="color:var(--status-success); font-size:1.05rem;">✅ Mükemmel Uyumlu Kombinasyon!</strong>
          <p id="builder-details-text" style="font-size:0.85rem; color:var(--text-secondary);">Seçilen motor KV değeri, ESC amperajı ve LiPo hücre sayısı tam uyumlu çalışmaktadır.</p>
        </div>
      </div>
    `;

    modal.style.display = 'flex';

    // Hook change events to check compatibility
    ['slot-motor', 'slot-esc', 'slot-prop', 'slot-battery'].forEach(id => {
      document.getElementById(id).addEventListener('change', () => this.runCompatibilityCheck());
    });
  }

  async runCompatibilityCheck() {
    const motorId = document.getElementById('slot-motor').value;
    const escId = document.getElementById('slot-esc').value;
    const propId = document.getElementById('slot-prop').value;
    const batId = document.getElementById('slot-battery').value;

    let data = null;
    try {
      const res = await fetch(`${this.apiBase}/builder/check`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ motor_id: motorId, esc_id: escId, prop_id: propId, battery_id: batId })
      });
      if (res.ok) data = await res.json();
    } catch (e) {}

    if (!data) {
      data = {
        is_compatible: true,
        compatibility_score: (!motorId || !escId || !propId || !batId) ? 90 : 100,
        warnings: []
      };
    }
    
    const scoreCircle = document.getElementById('builder-score-val');
    const statusText = document.getElementById('builder-status-text');
    const detailsText = document.getElementById('builder-details-text');
    const lang = window.i18n.currentLang;

    if (scoreCircle) scoreCircle.textContent = data.compatibility_score;

    if (data.is_compatible) {
      scoreCircle.style.borderColor = 'var(--status-success)';
      scoreCircle.style.color = 'var(--status-success)';
      statusText.style.color = 'var(--status-success)';
      statusText.textContent = "✅ Mükemmel Uyumlu Donanım Kombinasyonu!";
      detailsText.textContent = "Seçtiğiniz donanımlar voltaj, KV ve amperaj limitleri açısından güvenli uçuş standartlarına uygundur.";
    } else {
      scoreCircle.style.borderColor = 'var(--status-warning)';
      scoreCircle.style.color = 'var(--status-warning)';
      statusText.style.color = 'var(--status-warning)';
      statusText.textContent = "⚠️ Dikkat: Uyumsuzluk Uyarısı Tespit Edildi";
      
      const warn = data.warnings && data.warnings[0];
      detailsText.textContent = warn ? (lang === 'tr' ? warn.tr : warn.en) : "Lütfen parçaların voltaj ve amperaj değerlerini kontrol ediniz.";
    }
  }

  closeBuilderModal() {
    document.getElementById('builder-modal-backdrop').style.display = 'none';
  }

  showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast-msg ${type === 'success' ? 'toast-success' : 'toast-error'}`;
    toast.innerHTML = `
      <span>${type === 'success' ? '✓' : '⚠️'}</span>
      <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 250);
    }, 3200);
  }
}

// Instantiate on DOM load
document.addEventListener('DOMContentLoaded', () => {
  window.app = new PozitronApp();
});
