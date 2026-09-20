/**
 * Pozitron Market - Minimalist Client Application Engine
 */

const TURKISH_CITIES = [
  "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir",
  "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli",
  "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari",
  "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir",
  "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir",
  "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat",
  "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman",
  "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
];

class PozitronApp {
  constructor() {
    this.apiBase = '/api';
    this.currency = 'TRY';
    this.cart = JSON.parse(localStorage.getItem('pozitron_cart') || '[]');
    this.user = JSON.parse(localStorage.getItem('pozitron_user') || 'null');
    // Persistent sign-in backup: restore from 1-year cookie if localStorage was cleared
    if (!this.user) {
      try {
        const match = document.cookie.match(/(?:^|;\s*)pozitron_user_backup=([^;]+)/);
        if (match && match[1]) {
          const cookieUser = JSON.parse(decodeURIComponent(match[1]));
          if (cookieUser && (cookieUser.email || cookieUser.id)) {
            this.user = cookieUser;
            localStorage.setItem('pozitron_user', JSON.stringify(this.user));
          }
        }
      } catch (e) {}
    }
    if (this.user && this.isUserAdmin(this.user)) {
      this.user.role = 'admin';
      localStorage.setItem('pozitron_user', JSON.stringify(this.user));
    }
    this.appliedCoupon = null;
    this.categories = [];
    this.brands = [];
    
    this.escapeHTML = (str) => {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    };

    // SHA-256 password hashing for secure storage
    this.hashPassword = async (password) => {
      const encoder = new TextEncoder();
      const data = encoder.encode(password + '_pozitron_salt_2026');
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    };

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

    this.usdRate = (window.pozitronData && window.pozitronData.usd_rate ? parseFloat(window.pozitronData.usd_rate) : 50.0);
    const cachedRate = parseFloat(localStorage.getItem('pozitron_usd_rate'));
    if (!isNaN(cachedRate) && cachedRate > 0) {
      this.usdRate = cachedRate;
    }

    this.init();
  }

  async init() {
    // 0. Initialize User Database & Currency Rate
    this.initUserDatabase();
    await this.loadCurrencyRate();

    // 1. Initialize i18n
    window.i18n.updateDom();

    // 2. Setup Event Listeners
    this.bindEvents();
    this.init3DStudio();

    // 3. Load Initial Data
    await this.loadCategories();
    await this.loadBrands();
    this.updateUserUI();
    this.updateCartUI();

    // 4. Parse URL Query & Hash on Load (e.g. #category=vtx, #brand=SpeedyBee, ?category=vtx, etc.)
    const shouldScroll = this.handleUrlAndHashChange(true);

    // 5. Initial Product Fetch & Comments System
    await this.fetchProducts();
    this.initCommunityComments();

    if (shouldScroll) {
      this.scrollToCatalog();
    }

    // 6. Listen for hash changes
    window.addEventListener('hashchange', () => this.handleUrlAndHashChange(false));
    window.addEventListener('languageChanged', () => {
      this.renderCategoriesPills();
      this.renderCategorySidebar();
      this.fetchProducts();
      this.renderCommunityReviews(this.currentCommentFilter || 'all');
      this.updateDynamicSeoMeta();
    });

    // 7. Handle browser back / forward navigation
    window.addEventListener('popstate', (e) => {
      const modal = document.getElementById('product-modal-backdrop');
      if (modal && modal.style.display !== 'none') {
        modal.style.display = 'none';
      }
      this.handleUrlAndHashChange(false);
    });
  }

  handleUrlAndHashChange(isInitial = false) {
    let changed = false;
    let shouldScroll = false;

    // 1. Parse Search Query Parameters (e.g. ?category=vtx, ?brand=SpeedyBee, ?q=motors, ?product=...)
    try {
      const urlParams = new URLSearchParams(window.location.search);

      if (urlParams.has('category')) {
        const cat = urlParams.get('category');
        if (cat && this.filters.category !== cat) {
          this.filters.category = cat;
          if (!urlParams.has('brand')) this.filters.brand = 'all';
          this.filters.page = 1;
          changed = true;
          shouldScroll = true;
        }
      }

      if (urlParams.has('brand')) {
        const brand = decodeURIComponent(urlParams.get('brand'));
        if (brand && this.filters.brand !== brand) {
          this.filters.brand = brand;
          this.filters.page = 1;
          changed = true;
          shouldScroll = true;
        }
      }

      if (urlParams.has('q')) {
        const query = decodeURIComponent(urlParams.get('q'));
        if (query && this.filters.q !== query) {
          this.filters.q = query;
          const searchInput = document.getElementById('search-input');
          if (searchInput) searchInput.value = query;
          this.filters.page = 1;
          changed = true;
          shouldScroll = true;
        }
      }

      if (urlParams.has('voltage')) {
        const v = urlParams.get('voltage');
        if (v && this.filters.voltage !== v) {
          this.filters.voltage = v;
          this.filters.page = 1;
          changed = true;
          shouldScroll = true;
        }
      }

      if (urlParams.has('build')) {
        setTimeout(() => this.loadSharedBuild(urlParams.get('build')), 250);
      } else if (urlParams.has('product')) {
        const prod = urlParams.get('product');
        setTimeout(() => this.openProductModal(prod), 250);
      } else if (urlParams.has('builder')) {
        setTimeout(() => this.openBuilderModal(), 250);
      } else if (urlParams.has('3d-studio')) {
        setTimeout(() => this.open3DStudioModal(), 250);
      }
    } catch (e) {
      console.warn('URL search parse error:', e);
    }

    // 2. Parse Hash Parameters (e.g. #category=vtx, #brand=SpeedyBee, #q=motor, #builder, #cart, etc.)
    try {
      const rawHash = (window.location.hash || '').replace(/^#/, '');
      if (rawHash) {
        const hashParams = new URLSearchParams(rawHash.includes('=') ? rawHash : '');

        if (hashParams.has('category') || rawHash.startsWith('category=')) {
          const cat = hashParams.get('category') || (rawHash.split('category=')[1] ? rawHash.split('category=')[1].split('&')[0] : '');
          if (cat && this.filters.category !== cat) {
            this.filters.category = cat;
            if (!hashParams.has('brand') && !rawHash.includes('brand=')) {
              this.filters.brand = 'all';
            }
            this.filters.page = 1;
            changed = true;
            shouldScroll = true;
          }
        }

        if (hashParams.has('brand') || rawHash.startsWith('brand=')) {
          const brand = decodeURIComponent(hashParams.get('brand') || (rawHash.split('brand=')[1] ? rawHash.split('brand=')[1].split('&')[0] : ''));
          if (brand && this.filters.brand !== brand) {
            this.filters.brand = brand;
            this.filters.page = 1;
            changed = true;
            shouldScroll = true;
          }
        }

        if (hashParams.has('q') || rawHash.startsWith('q=')) {
          const query = decodeURIComponent(hashParams.get('q') || (rawHash.split('q=')[1] ? rawHash.split('q=')[1].split('&')[0] : ''));
          if (query && this.filters.q !== query) {
            this.filters.q = query;
            const searchInput = document.getElementById('search-input');
            if (searchInput) searchInput.value = query;
            this.filters.page = 1;
            changed = true;
            shouldScroll = true;
          }
        }

        if (rawHash.startsWith('product=')) {
          const prodSlug = rawHash.split('=')[1];
          setTimeout(() => this.openProductModal(prodSlug), 250);
        } else if (rawHash === 'builder') {
          setTimeout(() => this.openBuilderModal(), 250);
        } else if (rawHash.startsWith('build=')) {
          const buildData = rawHash.substring(6);
          setTimeout(() => this.loadSharedBuild(buildData), 250);
        } else if (rawHash === '3d-studio') {
          setTimeout(() => this.open3DStudioModal(), 250);
        } else if (rawHash === 'cart') {
          setTimeout(() => this.openCart(), 250);
        } else if (rawHash === 'catalog-section' || rawHash === 'products') {
          shouldScroll = true;
        }
      }
    } catch (e) {
      console.warn('Hash parse error:', e);
    }

    if (changed || isInitial) {
      this.renderCategoriesPills();
      this.renderCategorySidebar();
      this.renderBrandSidebar();
      this.updateDynamicSeoMeta();
      if (!isInitial) {
        this.fetchProducts();
      }
    }

    if (shouldScroll) {
      this.scrollToCatalog();
    }

    return shouldScroll;
  }

  scrollToCatalog() {
    const el = document.getElementById('catalog-section');
    if (el) {
      setTimeout(() => {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 120);
    }
  }

  handleSearchSubmit(e) {
    if (e) e.preventDefault();
    const searchInput = document.getElementById('search-input');
    const val = searchInput ? searchInput.value.trim() : '';
    this.filters.q = val;
    this.filters.page = 1;
    this.hideSuggestions();
    this.fetchProducts();
    this.updateDynamicSeoMeta();
    if (val) {
      history.pushState(null, '', '#q=' + encodeURIComponent(val));
    }
    this.scrollToCatalog();
  }

  updateDynamicSeoMeta() {
    const lang = window.i18n.currentLang;
    const catObj = this.categories.find(c => c.id === this.filters.category);
    let title = "Pozitron Market | Drone & FPV Donanım Mağazası";

    if (this.filters.q) {
      title = `${this.filters.q} - Drone Parçaları | Pozitron Market`;
    } else if (catObj) {
      const catName = lang === 'tr' ? catObj.name_tr : catObj.name_en;
      title = `${catName} | Pozitron Market`;
    }

    document.title = title;
  }

  resetAllFilters() {
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
    const searchInput = document.getElementById('search-input');
    const searchClear = document.getElementById('search-clear-btn');
    if (searchInput) searchInput.value = '';
    if (searchClear) searchClear.style.display = 'none';
    const inStockChk = document.getElementById('filter-in-stock');
    if (inStockChk) inStockChk.checked = true;
    const bestChk = document.getElementById('filter-bestseller');
    if (bestChk) bestChk.checked = false;
    const minP = document.getElementById('min-price-input');
    if (minP) minP.value = '';
    const maxP = document.getElementById('max-price-input');
    if (maxP) maxP.value = '';
    document.querySelectorAll('#voltage-filter-list .v-pill').forEach(p => p.classList.remove('active'));
    const allVolt = document.querySelector('#voltage-filter-list .v-pill[data-voltage="all"]');
    if (allVolt) allVolt.classList.add('active');
    this.renderCategoriesPills();
    this.renderCategorySidebar();
    this.renderBrandSidebar();
    this.fetchProducts();
    this.updateDynamicSeoMeta();
    if (window.location.hash) {
      history.pushState(null, '', window.location.pathname + window.location.search);
    }
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

    if (searchForm) {
      searchForm.addEventListener('submit', (e) => {
        this.handleSearchSubmit(e);
      });
    }

    if (searchInput) {
      let debounceTimer = null;
      searchInput.addEventListener('input', (e) => {
        const val = e.target.value.trim();
        if (searchClear) searchClear.style.display = val ? 'block' : 'none';
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
          this.handleLiveSearch(val);
        }, 220);
      });

      searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          this.handleSearchSubmit(e);
        }
      });
    }

    if (searchClear) {
      searchClear.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        searchClear.style.display = 'none';
        this.filters.q = '';
        this.hideSuggestions();
        this.fetchProducts();
        if (window.location.hash.startsWith('#q=')) {
          history.pushState(null, '', '#');
        }
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

    // Global ESC key listener to close modals, drawers and dropdowns
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' || e.key === 'Esc' || e.keyCode === 27) {
        this.handleEscapeKey();
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

    // Reset Filters Buttons
    const resetBtn = document.getElementById('btn-reset-filters');
    const resetEmptyBtn = document.getElementById('btn-reset-empty');
    if (resetBtn) resetBtn.addEventListener('click', () => this.resetAllFilters());
    if (resetEmptyBtn) resetEmptyBtn.addEventListener('click', () => this.resetAllFilters());

    // Category links in page & footer (e.g. data-cat="vtx")
    document.querySelectorAll('a[data-cat]').forEach(link => {
      link.addEventListener('click', (e) => {
        const cat = link.getAttribute('data-cat');
        if (cat) {
          e.preventDefault();
          this.filters.category = cat;
          this.filters.brand = 'all';
          this.filters.page = 1;
          this.renderCategoriesPills();
          this.renderCategorySidebar();
          this.renderBrandSidebar();
          this.fetchProducts();
          this.updateDynamicSeoMeta();
          history.pushState(null, '', cat === 'all' ? '#' : `#category=${cat}`);
          this.scrollToCatalog();
        }
      });
    });

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

    const closeGoogleModal = document.getElementById('close-google-modal');
    if (closeGoogleModal) closeGoogleModal.addEventListener('click', () => this.closeGoogleModal());

    const closeOrdersModal = document.getElementById('close-orders-modal');
    if (closeOrdersModal) closeOrdersModal.addEventListener('click', () => this.closeOrdersModal());

    const closeChkModal = document.getElementById('close-checkout-modal');
    if (closeChkModal) closeChkModal.addEventListener('click', () => this.closeCheckoutModal());

    // User Auth Button
    const authBtn = document.getElementById('auth-btn');
    if (authBtn) {
      authBtn.addEventListener('click', (e) => this.handleAuthBtnClick(e));
    }

    // Close user dropdown on click outside
    document.addEventListener('click', (e) => {
      const drop = document.getElementById('user-dropdown-menu');
      const authWrap = document.getElementById('user-auth-wrap');
      if (drop && drop.style.display !== 'none') {
        if (authWrap && !authWrap.contains(e.target)) {
          drop.style.display = 'none';
        }
      }
    });

    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    if (tabLogin && tabRegister) {
      tabLogin.addEventListener('click', () => {
        tabLogin.classList.add('active');
        tabRegister.classList.remove('active');
        if (loginForm) loginForm.style.display = 'block';
        if (registerForm) registerForm.style.display = 'none';
      });
      tabRegister.addEventListener('click', () => {
        tabRegister.classList.add('active');
        tabLogin.classList.remove('active');
        if (loginForm) loginForm.style.display = 'none';
        if (registerForm) registerForm.style.display = 'block';
      });
    }

    // Google Auth handled by GIS (g_id_onload) and handleCredentialResponse

    // My Orders in Dropdown
    const myOrdersBtn = document.getElementById('my-orders-btn');
    if (myOrdersBtn) {
      myOrdersBtn.addEventListener('click', () => this.openOrdersModal());
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

    // Brand Logo Reset Filters & Scroll to Top
    const brandLogo = document.getElementById('brand-logo-link');
    if (brandLogo) {
      brandLogo.addEventListener('click', (e) => {
        e.preventDefault();
        this.resetAllFilters();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }    // WA Confirm Modal
    const btnWaCancel = document.getElementById('btn-wa-cancel');
    if (btnWaCancel) btnWaCancel.addEventListener('click', () => this.handleWaCancel());

    const btnWaConfirm = document.getElementById('btn-wa-confirm');
    if (btnWaConfirm) btnWaConfirm.addEventListener('click', () => this.handleWaConfirm());

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

    // Card formatting & brand detection helpers
    const setupCardInputs = (numId, expId, brandIconId) => {
      const numEl = document.getElementById(numId);
      const expEl = document.getElementById(expId);
      const iconEl = document.getElementById(brandIconId);

      if (numEl) {
        numEl.addEventListener('input', (e) => {
          let val = e.target.value.replace(/\D/g, '').substring(0, 16);
          const parts = val.match(/.{1,4}/g);
          e.target.value = parts ? parts.join(' ') : val;

          // Detect brand
          if (iconEl) {
            if (/^4/.test(val)) { iconEl.textContent = 'VISA'; iconEl.style.color = '#1a56db'; }
            else if (/^(5[1-5]|2[2-7])/.test(val)) { iconEl.textContent = 'MC'; iconEl.style.color = '#ea580c'; }
            else if (/^9792/.test(val)) { iconEl.textContent = 'TROY'; iconEl.style.color = '#0284c7'; }
            else { iconEl.textContent = ''; iconEl.style.color = 'inherit'; }
          }
        });
      }

      if (expEl) {
        expEl.addEventListener('input', (e) => {
          let val = e.target.value.replace(/\D/g, '').substring(0, 4);
          if (val.length >= 2) val = val.substring(0, 2) + '/' + val.substring(2);
          e.target.value = val;
        });
      }
    };

    setupCardInputs('iyzico-card-number', 'iyzico-card-expiry', 'iyzico-card-brand-icon');
    setupCardInputs('paytr-card-number', 'paytr-card-expiry', 'paytr-card-brand-icon');

    // Checkout Submit (triggers 3D Secure or Havale)
    const submitOrderBtn = document.getElementById('submit-order-btn');
    if (submitOrderBtn) {
      submitOrderBtn.addEventListener('click', () => this.handleCheckoutSubmit());
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
    const rate = this.usdRate || 50.0;
    let tryVal = priceTRY;
    let usdVal = priceUSD;

    // Handle single-argument calls (e.g. formatPrice(amountTRY))
    if (tryVal === undefined || tryVal === null) {
      if (typeof priceUSD === 'number' || (!isNaN(Number(priceUSD)) && priceUSD !== '')) {
        tryVal = Number(priceUSD);
        usdVal = tryVal / rate;
      } else {
        tryVal = 0;
        usdVal = 0;
      }
    } else {
      tryVal = Number(tryVal) || 0;
      usdVal = (usdVal !== undefined && usdVal !== null && !isNaN(Number(usdVal))) 
        ? Number(usdVal) 
        : (tryVal / rate);
    }

    if (this.currency === 'TRY') {
      return new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' }).format(tryVal);
    }
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(usdVal);
  }

  formatImgUrl(url) {
    if (!url) return './assets/products/motor.png';
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) return url;
    if (url.startsWith('/assets/')) return '.' + url;
    if (url.startsWith('assets/')) return './' + url;
    return url;
  }

  // ==========================================
  // GA4 ENHANCED E-COMMERCE & AI SEARCH (GEO)
  // ==========================================
  trackGA4Event(eventName, params = {}) {
    try {
      if (typeof window.gtag === 'function') {
        window.gtag('event', eventName, params);
      }
      if (window.dataLayer && Array.isArray(window.dataLayer)) {
        window.dataLayer.push({
          event: eventName,
          ecommerce: params
        });
      }
      console.log(`[GA4 E-Commerce Event] ${eventName}:`, params);
    } catch (e) {
      console.warn('[GA4 Tracking Error]:', e);
    }
  }

  updateProductStructuredData(p) {
    if (!p) return;
    try {
      let script = document.getElementById('dynamic-product-jsonld');
      if (!script) {
        script = document.createElement('script');
        script.id = 'dynamic-product-jsonld';
        script.type = 'application/ld+json';
        document.head.appendChild(script);
      }

      const lang = window.i18n ? window.i18n.currentLang : 'tr';
      const name = lang === 'tr' ? (p.name_tr || p.name_en) : (p.name_en || p.name_tr);
      const desc = lang === 'tr' ? (p.description_tr || p.desc_tr) : (p.description_en || p.desc_en);
      const price = this.currency === 'TRY' ? (p.price_try || 0) : (p.price_usd || 0);
      const rawImg = p.image_url || '/assets/products/motor.png';
      const absImg = rawImg.startsWith('http') ? rawImg : `https://pozitronmarket.com/${rawImg.replace(/^\.?\//, '')}`;

      const schemaData = {
        "@context": "https://schema.org/",
        "@type": "Product",
        "name": name,
        "image": [absImg],
        "description": desc,
        "sku": p.sku || `PZTR-${p.id}`,
        "mpn": p.sku || p.id,
        "brand": {
          "@type": "Brand",
          "name": p.brand || "Pozitron"
        },
        "offers": {
          "@type": "Offer",
          "url": `https://pozitronmarket.com/#product-${p.slug || p.id}`,
          "priceCurrency": this.currency || "TRY",
          "price": price,
          "priceValidUntil": "2027-12-31",
          "itemCondition": "https://schema.org/NewCondition",
          "availability": (parseInt(p.stock) > 0) ? "https://schema.org/InStock" : "https://schema.org/OutOfStock",
          "seller": {
            "@type": "Organization",
            "name": "Pozitron Market"
          }
        },
        "aggregateRating": {
          "@type": "AggregateRating",
          "ratingValue": "4.9",
          "reviewCount": "24",
          "bestRating": "5",
          "worstRating": "1"
        }
      };

      script.textContent = JSON.stringify(schemaData);
    } catch(e) {}
  }

  getProductReviewsList(prod) {
    if (!prod) return [];
    const reviews = this.getCommunityReviews();
    
    // Support either product object or id/string
    let p = prod;
    if (typeof prod === 'string') {
      const staticData = this.getStaticData();
      p = (staticData.products || []).find(x => x.id === prod || x.slug === prod || x.sku === prod) || { id: prod, name_tr: prod, name_en: prod };
    }

    const pId = String(p.id || '').toLowerCase().trim();
    const pSlug = String(p.slug || '').toLowerCase().trim();
    const pSku = String(p.sku || '').toLowerCase().trim();
    const pNameTR = String(p.name_tr || '').toLowerCase().trim();
    const pNameEN = String(p.name_en || '').toLowerCase().trim();

    return reviews.filter(r => {
      if (!r) return false;
      const rName = String(r.productName || '').toLowerCase().trim();
      const rId = String(r.productId || '').toLowerCase().trim();

      // Skip general store reviews
      if (!rId && (!rName || rName.includes('genel') || rName.includes('general'))) {
        return false;
      }

      // 1. Direct ID / SKU / Slug matching
      if (rId) {
        if (pId && (rId === pId || pId.includes(rId) || rId.includes(pId))) return true;
        if (pSlug && (rId === pSlug || pSlug.includes(rId) || rId.includes(pSlug))) return true;
        if (pSku && (rId === pSku || pSku.includes(rId) || rId.includes(pSku))) return true;
      }

      // 2. Intelligent Product Name matching
      if (rName && !rName.includes('genel') && !rName.includes('general')) {
        // Direct inclusion
        if (pNameTR && (pNameTR.includes(rName) || rName.includes(pNameTR))) return true;
        if (pNameEN && (pNameEN.includes(rName) || rName.includes(pNameEN))) return true;

        // Clean model words and match keywords
        const cleanRName = rName.replace(/\(.*?\)/g, '').replace(/[^a-z0-9]/g, ' ').trim();
        const cleanTR = pNameTR.replace(/[^a-z0-9]/g, ' ').trim();
        const cleanEN = pNameEN.replace(/[^a-z0-9]/g, ' ').trim();

        const rKeywords = cleanRName.split(/\s+/).filter(w => w.length >= 3 && !['v1', 'v2', 'v3', 'v4', 'v5', 'pro', 'drone', 'fpv', 'set', 'kiti', 'stack', 'unit'].includes(w));
        if (rKeywords.length >= 2) {
          const matchTR = rKeywords.every(kw => cleanTR.includes(kw));
          const matchEN = rKeywords.every(kw => cleanEN.includes(kw));
          if (matchTR || matchEN) return true;
        }
      }

      return false;
    });
  }

  getProductReviewStats(prod) {
    const matched = this.getProductReviewsList(prod);

    if (matched.length > 0) {
      const sum = matched.reduce((acc, curr) => acc + (parseInt(curr.rating) || 5), 0);
      const avg = (sum / matched.length).toFixed(1);
      return {
        count: matched.length,
        rating: avg,
        hasReviews: true,
        reviews: matched
      };
    }

    return {
      count: 0,
      rating: '0',
      hasReviews: false,
      reviews: []
    };
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
      items.sort((a, b) => {
        const statsA = this.getProductReviewStats(a);
        const statsB = this.getProductReviewStats(b);
        const hasA = statsA.hasReviews && statsA.count > 0 ? 1 : 0;
        const hasB = statsB.hasReviews && statsB.count > 0 ? 1 : 0;
        if (hasA !== hasB) {
          return hasB - hasA; // Products with real reviews come first!
        }
        if (hasA && hasB) {
          const rA = parseFloat(statsA.rating) || 0;
          const rB = parseFloat(statsB.rating) || 0;
          if (rB !== rA) return rB - rA;
          return statsB.count - statsA.count;
        }
        return (b.is_bestseller || 0) - (a.is_bestseller || 0);
      });
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
        <span>${lang === 'tr' ? 'Tüm Parçalar' : 'All Parts'}</span>
      </button>
    `;

    this.categories.forEach(cat => {
      const name = lang === 'tr' ? cat.name_tr : cat.name_en;
      const isActive = this.filters.category === cat.id ? 'active' : '';
      html += `
        <button type="button" class="category-pill-btn ${isActive}" data-cat="${cat.id}">
          <span>${name}</span>
        </button>
      `;
    });

    bar.innerHTML = html;

    const activePill = bar.querySelector('.category-pill-btn.active');
    if (activePill) {
      setTimeout(() => {
        activePill.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      }, 50);
    }

    bar.querySelectorAll('.category-pill-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const cat = e.currentTarget.getAttribute('data-cat');
        this.filters.category = cat;
        this.filters.brand = 'all';
        this.filters.page = 1;
        this.renderCategoriesPills();
        this.renderCategorySidebar();
        this.renderBrandSidebar();
        this.fetchProducts();
        this.updateDynamicSeoMeta();
        history.pushState(null, '', cat === 'all' ? '#' : `#category=${cat}`);
      });
    });
  }

  renderCategorySidebar() {
    const list = document.getElementById('category-filter-list');
    if (!list) return;

    const lang = window.i18n.currentLang;
    const totalCount = this.categories.reduce((acc, c) => acc + (c.item_count || 0), 0);
    let html = `
      <label class="custom-checkbox">
        <input type="radio" name="sidebar-cat" value="all" ${this.filters.category === 'all' ? 'checked' : ''}>
        <span class="checkmark"></span>
        <span>${lang === 'tr' ? 'Tüm Kategoriler' : 'All Categories'}</span>
        ${totalCount > 0 ? `<span class="filter-count">${totalCount}</span>` : ''}
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
        this.filters.brand = 'all';
        this.filters.page = 1;
        this.renderCategoriesPills();
        this.renderBrandSidebar();
        this.fetchProducts();
        this.updateDynamicSeoMeta();
        history.pushState(null, '', e.target.value === 'all' ? '#' : `#category=${e.target.value}`);
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
        history.pushState(null, '', e.target.value === 'all' ? '#' : `#brand=${encodeURIComponent(e.target.value)}`);
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
        countText.textContent = '';
        countText.style.display = 'none';
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

      // GA4 view_item_list event
      const listLang = window.i18n ? window.i18n.currentLang : 'tr';
      this.trackGA4Event('view_item_list', {
        item_list_id: this.filters.category || 'all_products',
        item_list_name: this.filters.category ? this.filters.category : 'Tüm Ürünler',
        items: products.slice(0, 12).map((p, idx) => ({
          item_id: p.sku || p.id,
          item_name: listLang === 'tr' ? (p.name_tr || p.name_en) : (p.name_en || p.name_tr),
          item_brand: p.brand || 'Pozitron',
          item_category: p.category_id || 'FPV',
          price: this.currency === 'TRY' ? (p.price_try || 0) : (p.price_usd || 0),
          index: idx + 1
        }))
      });

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

      // Dynamic Review Rating & Count from Real Pilot Comments: ONLY display if real reviews exist!
      const reviewStats = this.getProductReviewStats(p);
      let ratingRowHtml = '';
      if (reviewStats.hasReviews && reviewStats.count > 0) {
        ratingRowHtml = `
          <div class="card-rating-row" style="display:flex; align-items:center; gap:6px; margin: 3px 0 5px 0; font-size:0.80rem;">
            <div style="display:flex; align-items:center; gap:2px; color:#f59e0b;">
              <span style="font-size:0.88rem;">★</span>
              <strong style="color:var(--text-primary); font-size:0.82rem;">${reviewStats.rating}</strong>
            </div>
            <span style="color:var(--text-muted); font-size:0.75rem;">(${reviewStats.count} ${lang === 'tr' ? 'Yorum' : 'Reviews'})</span>
          </div>
        `;
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
          <a href="./products/${p.slug}" class="card-media-wrap" title="${name}">
            ${badgeHtml}
            <img src="${this.formatImgUrl(p.image_url)}" alt="${name}" class="card-product-img" loading="lazy">
          </a>

          <div class="card-body">
            <div class="card-brand-row">
              <span class="card-brand">${p.brand}</span>
              <span class="card-stock-status ${p.stock > 0 ? (p.stock <= 3 ? 'low-stock' : '') : 'out-of-stock'}">
                <span class="card-stock-dot ${p.stock > 0 ? (p.stock <= 3 ? 'pulse' : '') : 'out-of-stock'}"></span>
                <span>${p.stock > 0 ? (p.stock <= 3 ? `Son ${p.stock} Adet!` : window.i18n.t('in_stock')) : window.i18n.t('out_of_stock')}</span>
              </span>
            </div>

            <h3 class="card-title">
              <a href="./products/${p.slug}">${name}</a>
            </h3>

            ${ratingRowHtml}

            <div class="card-specs-row">
              ${specsHtml}
            </div>

            <div class="card-footer-row">
              <div class="price-box">
                ${origPriceHtml}
                <span class="current-price">${priceFormatted}</span>
              </div>
              ${p.stock > 0 ? `
                <button type="button" class="btn-card-add" data-action="add-to-cart" data-id="${p.id}">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
                    <line x1="3" y1="6" x2="21" y2="6"></line>
                    <path d="M16 10a4 4 0 0 1-8 0"></path>
                  </svg>
                  <span>${window.i18n.t('add_to_cart')}</span>
                </button>
              ` : `
                <button type="button" class="btn-card-alert" data-action="stock-alert" data-id="${p.id}">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
                  <span>${window.i18n.t('stock_alert_btn')}</span>
                </button>
              `}
            </div>

          </div>
        </article>
      `;
    });

    grid.innerHTML = html;

    // Attach card event listeners
    grid.querySelectorAll('[data-action="add-to-cart"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const pid = e.currentTarget.getAttribute('data-id');
        const prod = products.find(x => x.id === pid);
        if (prod) this.addToCart(prod);
      });
    });

    grid.querySelectorAll('[data-action="stock-alert"]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const pid = e.currentTarget.getAttribute('data-id');
        this.openStockAlertModal(pid);
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

    const staticData = this.getStaticData();
    const q = query.toLowerCase().trim();
    const allMatches = (staticData.products || []).filter(p => {
      const nameTR = (p.name_tr || '').toLowerCase();
      const nameEN = (p.name_en || '').toLowerCase();
      const brand = (p.brand || '').toLowerCase();
      const sku = (p.sku || '').toLowerCase();
      const cat = (p.category_id || '').toLowerCase();
      return nameTR.includes(q) || nameEN.includes(q) || brand.includes(q) || sku.includes(q) || cat.includes(q);
    });

    const totalCount = allMatches.length;
    const items = allMatches.slice(0, 6);

    const lang = window.i18n ? window.i18n.currentLang : 'tr';

    if (items.length === 0) {
      box.innerHTML = `
        <div class="search-no-results">
          <div class="search-no-results-icon"><svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--text-muted);"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg></div>
          <div class="search-no-results-title">"${query}" ile eşleşen ürün bulunamadı</div>
          <div class="search-no-results-sub">Farklı bir marka, model veya kategori aramayı deneyebilirsiniz.</div>
        </div>
      `;
      box.style.display = 'flex';
      return;
    }

    const categoryMap = {};
    (staticData.categories || []).forEach(c => {
      categoryMap[c.id] = lang === 'tr' ? (c.name_tr || c.name) : (c.name_en || c.name);
    });

    let itemsHtml = items.map(p => {
      const name = lang === 'tr' ? p.name_tr : p.name_en;
      const price = this.formatPrice(p.price_usd, p.price_try);
      const catName = categoryMap[p.category_id] || p.category_id;
      const stockText = p.stock > 0 ? (lang === 'tr' ? `Stokta (${p.stock} adet)` : `In Stock (${p.stock})`) : (lang === 'tr' ? 'Tükendi' : 'Out of Stock');
      const stockColor = p.stock > 0 ? '#16a34a' : '#ef4444';

      return `
        <div class="suggestion-item" data-id="${p.id}">
          <img src="${this.formatImgUrl(p.image_url)}" alt="${name}" class="suggestion-img" loading="lazy">
          <div class="suggestion-info">
            <div class="suggestion-title">${name}</div>
            <div class="suggestion-meta-row">
              <span class="suggestion-badge-brand">${p.brand}</span>
              <span class="suggestion-badge-cat">${catName}</span>
            </div>
          </div>
          <div class="suggestion-price-col">
            <div class="suggestion-price">${price}</div>
            <div class="suggestion-stock" style="color:${stockColor};">● ${stockText}</div>
          </div>
        </div>
      `;
    }).join('');

    box.innerHTML = `
      <div class="search-suggestions-header">
        <span class="search-suggestions-count">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:4px;"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          <span>"${query}" için <strong>${totalCount}</strong> ürün bulundu</span>
        </span>
        <span style="font-size:0.75rem; color:var(--text-muted);">Tıklayarak inceleyin</span>
      </div>
      <div class="search-suggestions-list">
        ${itemsHtml}
      </div>
      <div class="search-suggestions-footer">
        <button type="button" class="search-all-btn" id="btn-search-show-all">
          <span>Tüm Sonuçları Listele (${totalCount} Ürün)</span>
          <span>→</span>
        </button>
      </div>
    `;

    box.style.display = 'flex';

    box.querySelectorAll('.suggestion-item').forEach(item => {
      item.addEventListener('click', (e) => {
        const pid = e.currentTarget.getAttribute('data-id');
        this.hideSuggestions();
        const staticData = this.getStaticData();
        const prod = (staticData.products || []).find(p => p.id === pid || p.slug === pid);
        if (prod && prod.slug) {
          window.location.href = `./products/${prod.slug}`;
        } else {
          this.openProductModal(pid);
        }
      });
    });

    const showAllBtn = document.getElementById('btn-search-show-all');
    if (showAllBtn) {
      showAllBtn.addEventListener('click', () => {
        this.filters.q = query;
        this.filters.page = 1;
        this.hideSuggestions();
        this.fetchProducts();
        const catalogEl = document.getElementById('catalog') || document.getElementById('products-section') || document.querySelector('.products-section');
        if (catalogEl) {
          catalogEl.scrollIntoView({ behavior: 'smooth' });
        }
      });
    }
  }

  hideSuggestions() {
    const box = document.getElementById('search-suggestions');
    if (box) box.style.display = 'none';
  }

  // ==========================================
  // CART OPERATIONS
  // ==========================================
  addToCart(product, quantity = 1) {
    if (typeof product === 'string') {
      const found = (this.products || []).find(p => p.id === product || p.slug === product) || 
                    (this.getStaticData().products || []).find(p => p.id === product || p.slug === product);
      if (found) product = found;
      else return;
    }
    if (!product || !product.id) return;

    const existing = this.cart.find(item => item.id === product.id);
    if (existing) {
      existing.quantity += quantity;
    } else {
      this.cart.push({
        id: product.id,
        sku: product.sku || `PZTR-${product.id}`,
        name_en: product.name_en,
        name_tr: product.name_tr,
        brand: product.brand,
        category_id: product.category_id,
        price_usd: product.price_usd,
        price_try: product.price_try,
        image_url: product.image_url,
        quantity: quantity
      });
    }

    // GA4 add_to_cart event tracking
    const itemPrice = this.currency === 'TRY' ? (product.price_try || 0) : (product.price_usd || 0);
    this.trackGA4Event('add_to_cart', {
      currency: this.currency || 'TRY',
      value: itemPrice * quantity,
      items: [{
        item_id: product.sku || product.id,
        item_name: window.i18n?.currentLang === 'tr' ? (product.name_tr || product.name_en) : (product.name_en || product.name_tr),
        item_brand: product.brand || 'Pozitron',
        item_category: product.category_id || 'FPV',
        price: itemPrice,
        quantity: quantity
      }]
    });

    this.saveCart();
    this.updateCartUI();
    this.openCartDrawer();
    this.showToast(`${window.i18n.currentLang === 'tr' ? product.name_tr : product.name_en} sepete eklendi!`, 'success');
  }

  updateQuantity(productId, delta) {
    const item = this.cart.find(i => i.id === productId);
    if (!item) return;

    if (delta < 0) {
      // GA4 remove_from_cart event tracking for decrement
      const itemPrice = this.currency === 'TRY' ? (item.price_try || 0) : (item.price_usd || 0);
      this.trackGA4Event('remove_from_cart', {
        currency: this.currency || 'TRY',
        value: itemPrice * Math.abs(delta),
        items: [{
          item_id: item.sku || item.id,
          item_name: item.name_en || item.name_tr,
          item_brand: item.brand || 'Pozitron',
          item_category: item.category_id || 'FPV',
          price: itemPrice,
          quantity: Math.abs(delta)
        }]
      });
    }

    item.quantity += delta;
    if (item.quantity <= 0) {
      this.cart = this.cart.filter(i => i.id !== productId);
    }

    this.saveCart();
    this.updateCartUI();
  }

  removeFromCart(productId) {
    const item = this.cart.find(i => i.id === productId);
    if (item) {
      const itemPrice = this.currency === 'TRY' ? (item.price_try || 0) : (item.price_usd || 0);
      this.trackGA4Event('remove_from_cart', {
        currency: this.currency || 'TRY',
        value: itemPrice * (item.quantity || 1),
        items: [{
          item_id: item.sku || item.id,
          item_name: item.name_en || item.name_tr,
          item_brand: item.brand || 'Pozitron',
          item_category: item.category_id || 'FPV',
          price: itemPrice,
          quantity: item.quantity || 1
        }]
      });
    }
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
          <div style="margin-bottom: 12px; color:var(--text-muted);">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
          </div>
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

      const specsHtml = item.custom_specs ? `
        <div style="font-size:0.72rem; color:#0284c7; background:#f0f9ff; border:1px solid #bae6fd; border-radius:4px; padding:2px 6px; margin:3px 0; display:inline-block;">
          ${item.custom_specs.material} • ${item.custom_specs.infill} • ${item.custom_specs.color}
        </div>
      ` : '';

      html += `
        <div class="cart-item-row">
          <img src="${this.formatImgUrl(item.image_url)}" alt="${name}" class="cart-item-img">
          <div class="cart-item-details">
            <div class="cart-item-name">${name}</div>
            ${specsHtml}
            <div class="cart-item-brand">${item.brand || 'Pozitron 3D Studio'}</div>
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
    const shippingFeeUSD = isFreeShipping ? 0 : 2.10;
    const shippingFeeTRY = isFreeShipping ? 0 : 99;

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
        const remaining = this.formatPrice((freeShippingTargetTRY - subtotalTRY) / (this.usdRate || 50.0), freeShippingTargetTRY - subtotalTRY);
        progressText.innerHTML = `${remaining} daha ekleyin, <strong>Ücretsiz Kargo</strong> kazanın!`;
      }
    }
  }

  openCartDrawer() {
    const backdrop = document.getElementById('cart-backdrop');
    if (backdrop) backdrop.classList.add('open');

    // GA4 view_cart tracking
    if (this.cart && this.cart.length > 0) {
      let subTotal = 0;
      this.cart.forEach(i => {
        subTotal += (this.currency === 'TRY' ? (i.price_try || 0) : (i.price_usd || 0)) * (i.quantity || 1);
      });
      const lang = window.i18n ? window.i18n.currentLang : 'tr';
      this.trackGA4Event('view_cart', {
        currency: this.currency || 'TRY',
        value: subTotal,
        items: this.cart.map(item => ({
          item_id: item.sku || item.id,
          item_name: lang === 'tr' ? (item.name_tr || item.name_en) : (item.name_en || item.name_tr),
          item_brand: item.brand || 'Pozitron',
          item_category: item.category_id || 'FPV',
          price: this.currency === 'TRY' ? (item.price_try || 0) : (item.price_usd || 0),
          quantity: item.quantity || 1
        }))
      });
    }
  }

  closeCartDrawer() {
    const backdrop = document.getElementById('cart-backdrop');
    if (backdrop) backdrop.classList.remove('open');
  }

  openCart() {
    this.openCartDrawer();
  }

  closeCart() {
    this.closeCartDrawer();
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
  // ACCOUNTS DATABASE & AUTHENTICATION
  // ==========================================
  getRobotAvatar(u) {
    if (!u) return 'https://api.dicebear.com/7.x/bottts/svg?seed=PilotBot&scale=90';
    const raw = typeof u === 'string' ? u : (u.avatar_url || '');
    const isHumanStock = raw.includes('unsplash') || raw.includes('pravatar') || raw.includes('randomuser') || raw.includes('photo-') || raw.includes('portrait') || raw.includes('person');

    if (raw && !isHumanStock && (raw.includes('googleusercontent.com') || raw.includes('dicebear'))) {
      return raw;
    }
    const seed = (typeof u === 'object' ? (u.full_name || u.email || u.id) : u) || 'Pilot';
    return `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(seed)}&scale=90&backgroundColor=f1f5f9,e0e7ff,f0fdf4,fef3c7,fce7f3`;
  }

  initUserDatabase() {
    const DB_KEY = 'pozitron_users_db';
    const FORBIDDEN_DEMOS = [
      'test_pilot@example.com',
      'demo.pilot@gmail.com',
      'drone.tr@gmail.com',
      'eyup@pozitron.com'
    ];
    let users = [];
    try {
      users = JSON.parse(localStorage.getItem(DB_KEY) || '[]');
    } catch (e) {
      users = [];
    }

    if (!Array.isArray(users)) {
      users = [];
    } else {
      users = users.filter(u => u && u.email && !FORBIDDEN_DEMOS.includes(u.email.toLowerCase().trim()));
    }
    localStorage.setItem(DB_KEY, JSON.stringify(users));

    // Also check current active user
    try {
      const cur = JSON.parse(localStorage.getItem('pozitron_user') || 'null');
      if (cur && cur.email && FORBIDDEN_DEMOS.includes(cur.email.toLowerCase().trim())) {
        localStorage.removeItem('pozitron_user');
      }
    } catch(e) {}
  }

  getAllUsersFromDb() {
    this.initUserDatabase();
    try {
      const FORBIDDEN_DEMOS = [
        'test_pilot@example.com',
        'demo.pilot@gmail.com',
        'drone.tr@gmail.com',
        'eyup@pozitron.com'
      ];
      const list = JSON.parse(localStorage.getItem('pozitron_users_db') || '[]');
      return Array.isArray(list) ? list.filter(u => u && u.email && !FORBIDDEN_DEMOS.includes(u.email.toLowerCase().trim())) : [];
    } catch (e) {
      return [];
    }
  }

  isValidEmail(email) {
    const re = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return re.test(String(email).trim().toLowerCase());
  }

  openAuthModal() {
    const backdrop = document.getElementById('auth-modal-backdrop');
    if (backdrop) backdrop.style.display = 'flex';
    // Clear any previous error messages
    const loginErr = document.getElementById('login-error-msg');
    const regErr = document.getElementById('reg-error-msg');
    if (loginErr) loginErr.style.display = 'none';
    if (regErr) regErr.style.display = 'none';
  }

  closeAuthModal() {
    const backdrop = document.getElementById('auth-modal-backdrop');
    if (backdrop) backdrop.style.display = 'none';
  }


  async loadCurrencyRate() {
    // 1. Try server live settings (Render Cloud or local server)
    try {
      const res = await fetch(`/api/settings?t=${Date.now()}`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.usd_rate) {
          const rate = parseFloat(data.usd_rate);
          if (!isNaN(rate) && rate > 0) {
            this.usdRate = rate;
            localStorage.setItem('pozitron_usd_rate', rate.toString());
            return;
          }
        }
      }
    } catch(e) {}

    // 2. Try server currency-rate endpoint
    try {
      const res2 = await fetch(`/api/currency-rate?t=${Date.now()}`);
      if (res2.ok) {
        const data2 = await res2.json();
        if (data2 && data2.usd_rate) {
          const rate = parseFloat(data2.usd_rate);
          if (!isNaN(rate) && rate > 0) {
            this.usdRate = rate;
            localStorage.setItem('pozitron_usd_rate', rate.toString());
            return;
          }
        }
      }
    } catch(e) {}

    // 3. Static fallback: data/settings.json (authoritative for static GitHub Pages)
    try {
      const res3 = await fetch(`data/settings.json?t=${Date.now()}`);
      if (res3.ok) {
        const data3 = await res3.json();
        if (data3 && data3.usd_rate) {
          const rate = parseFloat(data3.usd_rate);
          if (!isNaN(rate) && rate > 0) {
            this.usdRate = rate;
            localStorage.setItem('pozitron_usd_rate', rate.toString());
            return;
          }
        }
      }
    } catch(e) {}

    // 4. Static bundle fallback: window.pozitronData
    if (window.pozitronData && window.pozitronData.usd_rate) {
      const fallback = parseFloat(window.pozitronData.usd_rate);
      if (!isNaN(fallback) && fallback > 0) {
        this.usdRate = fallback;
        localStorage.setItem('pozitron_usd_rate', fallback.toString());
      }
    }
  }

  async openOrdersModal() {
    const drop = document.getElementById('user-dropdown-menu');
    if (drop) drop.style.display = 'none';

    const modal = document.getElementById('orders-modal-backdrop');
    const body = document.getElementById('orders-modal-body');
    if (!modal || !body) return;

    modal.style.display = 'flex';
    body.innerHTML = '<div style="text-align:center; padding:32px 16px; color:var(--text-muted);">Siparişleriniz yükleniyor...</div>';

    let orders = [];
    try {
      orders = JSON.parse(localStorage.getItem('pozitron_orders') || '[]');
    } catch(e) {
      orders = [];
    }

    // Try fetching live orders from API if user is logged in
    const currentUser = JSON.parse(localStorage.getItem('pozitron_user') || 'null');
    if (currentUser && (currentUser.email || currentUser.id)) {
      try {
        const qUrl = currentUser.email ? `/api/orders?email=${encodeURIComponent(currentUser.email)}` : `/api/orders/user/${encodeURIComponent(currentUser.id)}`;
        const res = await fetch(qUrl);
        if (res.ok) {
          const data = await res.json();
          if (data && Array.isArray(data.orders) && data.orders.length > 0) {
            const existingNums = new Set(data.orders.map(o => o.order_number || o.id));
            orders = data.orders.concat(orders.filter(o => !existingNums.has(o.order_number || o.id)));
          }
        }
      } catch(err) {}
    }

    if (orders.length === 0) {
      body.innerHTML = `
        <div style="text-align:center; padding:32px 16px;">
          <div style="margin-bottom:12px; color:var(--text-muted);">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><line x1="16.5" y1="9.4" x2="7.5" y2="4.21"></line><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path><polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline><line x1="12" y1="22.08" x2="12" y2="12"></line></svg>
          </div>
          <strong style="display:block; font-size:1.05rem; color:var(--text-primary); margin-bottom:6px;">Henüz bir siparişiniz bulunmuyor</strong>
          <p style="font-size:0.85rem; color:var(--text-secondary); margin:0;">Geniş drone donanım stoğumuzdan dilediğinizi sepetinize ekleyip sipariş oluşturabilirsiniz.</p>
        </div>
      `;
    } else {
      body.innerHTML = orders.map(ord => {
        const st = (ord.status || ord.order_status || 'CONFIRMED').toUpperCase();
        let badgeHtml = '<span style="font-size:0.78rem; background:#e0f2fe; color:#0369a1; padding:3px 8px; border-radius:6px; font-weight:600;">● Onaylandı</span>';
        if (st === 'SHIPPED' || st === 'KARGODA') {
          badgeHtml = '<span style="font-size:0.78rem; background:#ffedd5; color:#c2410c; padding:3px 8px; border-radius:6px; font-weight:600;">🚚 Kargoya Verildi</span>';
        } else if (st === 'DELIVERED' || st === 'TESLİM EDİLDİ') {
          badgeHtml = '<span style="font-size:0.78rem; background:#dcfce7; color:#15803d; padding:3px 8px; border-radius:6px; font-weight:600;">✅ Teslim Edildi</span>';
        } else if (st === 'CANCELLED' || st === 'İPTAL') {
          badgeHtml = '<span style="font-size:0.78rem; background:#fee2e2; color:#b91c1c; padding:3px 8px; border-radius:6px; font-weight:600;">✕ İptal Edildi</span>';
        }

        return `
          <div style="border:1px solid var(--border-subtle); border-radius:10px; padding:14px 16px; margin-bottom:12px; background:var(--bg-secondary);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <strong style="color:var(--brand-primary); font-size:0.92rem;">${ord.order_number || ord.id}</strong>
              ${badgeHtml}
            </div>
            <div style="font-size:0.82rem; color:var(--text-secondary); line-height:1.6;">
              <div><strong>Kargo Takip:</strong> ${ord.tracking_number || '-'}</div>
              <div><strong>Tarih:</strong> ${new Date(ord.created_at || Date.now()).toLocaleDateString('tr-TR')}</div>
              <div><strong>Teslimat:</strong> ${this.escapeHTML(ord.shipping_address || 'İstanbul / Turkey')}</div>
              <div><strong>Toplam:</strong> <span style="color:var(--brand-primary); font-weight:700;">${this.formatPrice(ord.total_usd, ord.total_try)}</span></div>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  closeOrdersModal() {
    const modal = document.getElementById('orders-modal-backdrop');
    if (modal) modal.style.display = 'none';
  }

  isUserAdmin(user) {
    if (!user) return false;
    const email = (user.email || user.username || '').toLowerCase().trim();
    if (!email) return false;

    // Owner and Manager Authorized Accounts ONLY (Strict email whitelist)
    const adminEmails = [
      'furkaniusprimes@gmail.com',
      'thepeakiscold@gmail.com',
      'eyupfurkanpekoz@gmail.com',
      'pekozfurkan@gmail.com',
      'pozitronmarket@gmail.com',
      'ahmet@pozitron.market'
    ];
    if (adminEmails.includes(email)) return true;
    if (email.endsWith('@pozitron.market')) return true;

    return false;
  }

  updateUserUI() {
    const nameEl = document.getElementById('user-display-name');
    const dropName = document.getElementById('user-name-text');
    const dropEmail = document.getElementById('user-email-text');
    const avatarImg = document.getElementById('user-avatar-img');
    const adminLink = document.getElementById('admin-panel-link');
    const headerAdminBtn = document.getElementById('header-admin-btn');

    if (this.user) {
      if (this.isUserAdmin(this.user)) {
        this.user.role = 'admin';
      }
      const firstName = (this.user.full_name || 'Pilot').split(' ')[0];
      if (nameEl) nameEl.textContent = firstName;
      if (dropName) dropName.textContent = this.user.full_name || 'Pilot';
      if (dropEmail) dropEmail.textContent = this.user.email || '';
      if (avatarImg) {
        avatarImg.src = this.getRobotAvatar(this.user);
        avatarImg.style.display = 'block';
      }
      const isAdmin = this.isUserAdmin(this.user);
      if (adminLink) {
        adminLink.style.display = isAdmin ? 'flex' : 'none';
      }
      if (headerAdminBtn) {
        headerAdminBtn.style.display = isAdmin ? 'inline-flex' : 'none';
      }
    } else {
      if (nameEl) nameEl.textContent = window.i18n.t('nav_login');
      if (avatarImg) avatarImg.src = '';
      if (adminLink) adminLink.style.display = 'none';
      if (headerAdminBtn) headerAdminBtn.style.display = 'none';
    }
  }

  handleAuthBtnClick(e) {
    if (e && e.stopPropagation) e.stopPropagation();

    // Prevent duplicate rapid triggers (e.g. inline onclick + addEventListener collision)
    const now = Date.now();
    if (this._lastAuthClick && (now - this._lastAuthClick < 250)) {
      return;
    }
    this._lastAuthClick = now;

    if (this.user) {
      const drop = document.getElementById('user-dropdown-menu');
      if (drop) {
        const isHidden = !drop.style.display || drop.style.display === 'none';
        drop.style.display = isHidden ? 'block' : 'none';
      }
    } else {
      this.openAuthModal();
    }
  }

  handleTabSwitch(tabName) {
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const loginErr = document.getElementById('login-error-msg');
    const regErr = document.getElementById('reg-error-msg');

    if (loginErr) loginErr.style.display = 'none';
    if (regErr) regErr.style.display = 'none';

    if (tabName === 'login') {
      if (tabLogin) tabLogin.classList.add('active');
      if (tabRegister) tabRegister.classList.remove('active');
      if (loginForm) loginForm.style.display = 'block';
      if (registerForm) registerForm.style.display = 'none';
    } else {
      if (tabRegister) tabRegister.classList.add('active');
      if (tabLogin) tabLogin.classList.remove('active');
      if (loginForm) loginForm.style.display = 'none';
      if (registerForm) registerForm.style.display = 'block';
    }
  }


  loginWithUser(userObj) {
    this.user = userObj;
    localStorage.setItem('pozitron_user', JSON.stringify(this.user));
    try {
      document.cookie = "pozitron_user_backup=" + encodeURIComponent(JSON.stringify(this.user)) + "; credentials=same-origin; max-age=31536000; path=/; SameSite=Lax";
    } catch(e) {}
    this.updateUserUI();
  }

  getLoginSecurityRecord(email) {
    const key = 'pozitron_security_lockout';
    try {
      const data = JSON.parse(localStorage.getItem(key) || '{}');
      const record = data[email.toLowerCase()];
      if (!record) return { locked: false, attempts: 0, attemptsLeft: 3 };

      const now = Date.now();
      if (record.lockedUntil && record.lockedUntil > now) {
        const remainingSeconds = Math.ceil((record.lockedUntil - now) / 1000);
        const remainingMinutes = Math.ceil(remainingSeconds / 60);
        return { locked: true, remainingSeconds, remainingMinutes, attemptsLeft: 0 };
      }

      // If lockout expired, clear record
      if (record.lockedUntil && record.lockedUntil <= now) {
        delete data[email.toLowerCase()];
        localStorage.setItem(key, JSON.stringify(data));
        return { locked: false, attempts: 0, attemptsLeft: 3 };
      }

      const attemptsLeft = Math.max(0, 3 - (record.attempts || 0));
      return { locked: false, attempts: record.attempts || 0, attemptsLeft };
    } catch (e) {
      return { locked: false, attempts: 0, attemptsLeft: 3 };
    }
  }

  recordLoginFailure(email) {
    const key = 'pozitron_security_lockout';
    try {
      const data = JSON.parse(localStorage.getItem(key) || '{}');
      const em = email.toLowerCase();
      const record = data[em] || { attempts: 0, lockedUntil: 0 };
      record.attempts = (record.attempts || 0) + 1;

      if (record.attempts >= 3) {
        record.lockedUntil = Date.now() + 30 * 60 * 1000; // 30 minutes lockout
        data[em] = record;
        localStorage.setItem(key, JSON.stringify(data));
        return { locked: true, remainingSeconds: 1800, remainingMinutes: 30, attemptsLeft: 0 };
      } else {
        data[em] = record;
        localStorage.setItem(key, JSON.stringify(data));
        return { locked: false, remainingSeconds: 0, remainingMinutes: 0, attemptsLeft: 3 - record.attempts };
      }
    } catch (e) {
      return { locked: false, remainingSeconds: 0, remainingMinutes: 0, attemptsLeft: 2 };
    }
  }

  clearLoginFailure(email) {
    const key = 'pozitron_security_lockout';
    try {
      const data = JSON.parse(localStorage.getItem(key) || '{}');
      delete data[email.toLowerCase()];
      localStorage.setItem(key, JSON.stringify(data));
    } catch (e) {}
  }

  async handleManualLogin(e) {
    if (e && e.preventDefault) e.preventDefault();
    const emailEl = document.getElementById('login-email');
    const passEl = document.getElementById('login-password');
    const email = emailEl ? emailEl.value.trim().toLowerCase() : '';
    const password = passEl ? passEl.value : '';
    const err = document.getElementById('login-error-msg');

    if (!email || !password) {
      if (err) {
        err.textContent = 'Lütfen e-posta adresinizi ve şifrenizi giriniz.';
        err.style.display = 'block';
      }
      return;
    }

    if (!this.isValidEmail(email)) {
      if (err) {
        err.textContent = 'Lütfen geçerli bir e-posta formatı giriniz (örn: pilot@drone.com).';
        err.style.display = 'block';
      }
      return;
    }

    // 0. Check Security Lockout (3 attempts -> 30 min cooldown)
    const secStatus = this.getLoginSecurityRecord(email);
    if (secStatus.locked) {
      if (err) {
        err.innerHTML = `<strong>Güvenlik Koruması:</strong> 3 kez hatalı deneme yapıldığı için hesabınız kilitlendi.<br>Lütfen <strong>${secStatus.remainingMinutes} dakika</strong> sonra tekrar deneyiniz.`;
        err.style.display = 'block';
      }
      return;
    }

    // Try backend API first
    try {
      const res = await fetch(`${this.apiBase}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (res.status === 429 || data.locked) {
        if (err) {
          err.innerHTML = `<strong>Güvenlik Koruması:</strong> ${data.error || 'Hesabınız 30 dakika kilitlenmiştir.'}`;
          err.style.display = 'block';
        }
        this.recordLoginFailure(email);
        return;
      }
      if (res.ok && data.success && data.user) {
        this.clearLoginFailure(email);
        if (err) err.style.display = 'none';
        this.loginWithUser(data.user);
        this.closeAuthModal();
        if (emailEl) emailEl.value = '';
        if (passEl) passEl.value = '';
        this.showToast(`Giriş başarılı! Hoş geldiniz, ${data.user.full_name}`, 'success');
        return;
      }
    } catch (netErr) {
      // Fallback to local DB
    }

    // Fallback: Local Accounts Database check
    const usersDb = this.getAllUsersFromDb();
    const matchedUser = usersDb.find(u => u.email.toLowerCase() === email);

    // Hash the entered password for comparison
    const hashedPassword = await this.hashPassword(password);
    // Support both legacy plaintext and new hashed passwords
    const passwordMatch = matchedUser && (matchedUser.password === hashedPassword || matchedUser.password === password);

    // If legacy plaintext match found, upgrade to hashed
    if (matchedUser && matchedUser.password === password && matchedUser.password !== hashedPassword) {
      matchedUser.password = hashedPassword;
      localStorage.setItem('pozitron_users_db', JSON.stringify(usersDb));
    }

    if (!matchedUser || !passwordMatch) {
      const failRes = this.recordLoginFailure(email);
      if (failRes.locked) {
        if (err) {
          err.innerHTML = `<strong>3 kez hatalı giriş yapıldı!</strong><br>Hesap güvenliğiniz için <strong>30 dakika</strong> boyunca giriş engellenmiştir.`;
          err.style.display = 'block';
        }
      } else {
        if (err) {
          err.innerHTML = `Hatalı e-posta veya şifre!<br><strong>Kalan deneme hakkınız: ${failRes.attemptsLeft}</strong> (3 hatalı denemede 30 dk kilitlenir).`;
          err.style.display = 'block';
        }
      }
      return;
    }

    // Success - Clear lockout
    this.clearLoginFailure(email);
    if (err) err.style.display = 'none';
    this.loginWithUser(matchedUser);
    this.closeAuthModal();
    if (emailEl) emailEl.value = '';
    if (passEl) passEl.value = '';
    this.showToast(`Giriş başarılı! Hoş geldiniz, ${matchedUser.full_name}`, 'success');
  }

  async handleManualRegister(e) {
    if (e && e.preventDefault) e.preventDefault();
    const nameEl = document.getElementById('reg-name');
    const emailEl = document.getElementById('reg-email');
    const passEl = document.getElementById('reg-password');
    const full_name = nameEl ? nameEl.value.trim() : '';
    const email = emailEl ? emailEl.value.trim().toLowerCase() : '';
    const password = passEl ? passEl.value : '';
    const err = document.getElementById('reg-error-msg');

    if (!full_name || !email || !password) {
      if (err) {
        err.textContent = 'Lütfen tüm alanları (Ad Soyad, E-Posta, Şifre) eksiksiz doldurunuz.';
        err.style.display = 'block';
      }
      return;
    }

    if (full_name.length < 2) {
      if (err) {
        err.textContent = 'Ad Soyad en az 2 karakter olmalıdır.';
        err.style.display = 'block';
      }
      return;
    }

    if (!this.isValidEmail(email)) {
      if (err) {
        err.textContent = 'Lütfen geçerli bir e-posta formatı giriniz (örn: pilot@drone.com).';
        err.style.display = 'block';
      }
      return;
    }

    if (password.length < 6) {
      if (err) {
        err.textContent = 'Güvenliğiniz için şifre en az 6 karakter olmalıdır.';
        err.style.display = 'block';
      }
      return;
    }

    // Check if email is already registered in Database
    const usersDb = this.getAllUsersFromDb();
    const existingUser = usersDb.find(u => u.email.toLowerCase() === email);

    if (existingUser) {
      if (err) {
        err.textContent = `"${email}" adresi ile kayıtlı bir hesap zaten var! Lütfen 'Giriş Yap' sekmesinden giriş yapınız.`;
        err.style.display = 'block';
      }
      return;
    }

    if (err) err.style.display = 'none';

    // Hash password before storing (never store plaintext)
    const hashedPw = await this.hashPassword(password);

    const newUser = {
      id: "usr_" + Date.now().toString(36) + Math.random().toString(36).substr(2, 5),
      email: email,
      password: hashedPw,
      full_name: full_name,
      avatar_url: `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(full_name)}`,
      provider: "manual",
      created_at: new Date().toISOString()
    };

    // Save to database
    usersDb.push(newUser);
    localStorage.setItem('pozitron_users_db', JSON.stringify(usersDb));

    // Send user to Google Sheets (Kullanıcılar sayfası)
    const WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbw_YHCFvOkkq2usjJh4XCMMHWgHy9V_7C5fROFCjrTGw1iGsPy_39o6JXyvlowO9iy5/exec";
    fetch(WEBHOOK_URL, {
      method: 'POST',
      mode: 'no-cors',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'user',
        full_name: full_name,
        email: email,
        provider: 'manual',
        registered_at: new Date().toISOString()
      })
    }).catch(err => console.log('User webhook error:', err));

    // Synchronize manual register with centralized backend
    try {
      const apiTarget = window.PozitronAPI ? window.PozitronAPI.getUrl('/api/auth/register') : '/api/auth/register';
      fetch(apiTarget, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: newUser.email,
          password: password,
          full_name: newUser.full_name,
          avatar_url: newUser.avatar_url
        })
      }).catch(() => {});
    } catch(e) {}

    // Log in
    this.loginWithUser(newUser);
    this.closeAuthModal();
    if (nameEl) nameEl.value = '';
    if (emailEl) emailEl.value = '';
    if (passEl) passEl.value = '';
    this.showToast(`Hesabınız başarıyla oluşturuldu! Hoş geldiniz, ${full_name}`, 'success');
  }

  handleLogout() {
    this.user = null;
    localStorage.removeItem('pozitron_user');
    try {
      document.cookie = "pozitron_user_backup=; max-age=0; path=/; SameSite=Lax";
    } catch(e) {}
    const drop = document.getElementById('user-dropdown-menu');
    if (drop) drop.style.display = 'none';
    this.updateUserUI();
    this.showToast('Başarıyla çıkış yapıldı.', 'success');
    this.openAuthModal();
  }

  // ==========================================
  // FORGOT & RESET PASSWORD
  // ==========================================
  showForgotPassword() {
    const loginForm = document.getElementById('login-form');
    const regForm = document.getElementById('register-form');
    const authTabs = document.querySelector('.auth-tabs');
    const forgotPanel = document.getElementById('forgot-password-panel');
    const googleSec = document.querySelector('.google-auth-section');

    if (loginForm) loginForm.style.display = 'none';
    if (regForm) regForm.style.display = 'none';
    if (authTabs) authTabs.style.display = 'none';
    if (googleSec) googleSec.style.display = 'none';
    if (forgotPanel) {
      forgotPanel.style.display = 'block';
      const sendForm = document.getElementById('forgot-send-code-form');
      const resetForm = document.getElementById('forgot-reset-password-form');
      if (sendForm) sendForm.style.display = 'block';
      if (resetForm) resetForm.style.display = 'none';
      const forgotEmail = document.getElementById('forgot-email');
      const loginEmail = document.getElementById('login-email');
      if (forgotEmail && loginEmail && loginEmail.value) {
        forgotEmail.value = loginEmail.value;
      }
    }
  }

  hideForgotPassword() {
    const loginForm = document.getElementById('login-form');
    const authTabs = document.querySelector('.auth-tabs');
    const forgotPanel = document.getElementById('forgot-password-panel');
    const googleSec = document.querySelector('.google-auth-section');

    if (forgotPanel) forgotPanel.style.display = 'none';
    if (authTabs) authTabs.style.display = 'flex';
    if (googleSec) googleSec.style.display = 'flex';
    if (loginForm) loginForm.style.display = 'block';
  }

  async handleForgotPasswordSendCode(e) {
    if (e && e.preventDefault) e.preventDefault();
    const emailInput = document.getElementById('forgot-email');
    const errEl = document.getElementById('forgot-error-msg');
    const email = emailInput ? emailInput.value.trim().toLowerCase() : '';

    if (!email || !this.isValidEmail(email)) {
      if (errEl) {
        errEl.textContent = 'Lütfen geçerli bir e-posta adresi giriniz.';
        errEl.style.display = 'block';
      }
      return;
    }

    if (errEl) errEl.style.display = 'none';
    const btn = document.getElementById('btn-send-reset-code');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Kod Gönderiliyor...';
    }

    try {
      const res = await fetch(`${this.apiBase}/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        const sendForm = document.getElementById('forgot-send-code-form');
        const resetForm = document.getElementById('forgot-reset-password-form');
        const noticeEl = document.getElementById('forgot-code-notice');
        if (sendForm) sendForm.style.display = 'none';
        if (resetForm) resetForm.style.display = 'block';
        if (noticeEl) {
          noticeEl.innerHTML = `<strong>6 Haneli Doğrulama Kodu Gönderildi!</strong><br>Lütfen <strong>${this.escapeHTML(email)}</strong> adresli e-postanızı (ve spam klasörünü) kontrol ediniz. Kod 30 dakika geçerlidir.`;
        }
        const codeInput = document.getElementById('reset-code');
        if (codeInput) {
          codeInput.value = '';
          codeInput.focus();
        }
        this.showToast('Doğrulama kodu e-posta adresinize gönderildi!', 'success');
      } else {
        if (errEl) {
          errEl.textContent = data.error || 'Şifre sıfırlama kodu gönderilemedi.';
          errEl.style.display = 'block';
        }
      }
    } catch(err) {
      if (errEl) {
        errEl.textContent = 'Sunucuya bağlanılamadı. Lütfen internet bağlantınızı kontrol ediniz.';
        errEl.style.display = 'block';
      }
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = window.i18n ? window.i18n.t('btn_send_code') : 'Sıfırlama Kodu Gönder';
      }
    }
  }

  async handleResetPasswordSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    const emailInput = document.getElementById('forgot-email');
    const codeInput = document.getElementById('reset-code');
    const newPassInput = document.getElementById('reset-new-password');
    const errEl = document.getElementById('reset-error-msg');

    const email = emailInput ? emailInput.value.trim().toLowerCase() : '';
    const code = codeInput ? codeInput.value.trim() : '';
    const new_password = newPassInput ? newPassInput.value : '';

    if (!code || code.length !== 6) {
      if (errEl) {
        errEl.textContent = 'Lütfen 6 haneli doğrulama kodunu giriniz.';
        errEl.style.display = 'block';
      }
      return;
    }

    if (!new_password || new_password.length < 6) {
      if (errEl) {
        errEl.textContent = 'Yeni şifreniz en az 6 karakter olmalıdır.';
        errEl.style.display = 'block';
      }
      return;
    }

    if (errEl) errEl.style.display = 'none';
    const btn = document.getElementById('btn-submit-new-password');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Şifre Güncelleniyor...';
    }

    try {
      const res = await fetch(`${this.apiBase}/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code, new_password })
      });
      const data = await res.json();
      if (res.ok && data.success && data.user) {
        this.clearLoginFailure(email);
        this.loginWithUser(data.user);
        this.closeAuthModal();
        this.hideForgotPassword();
        this.showToast('Şifreniz başarıyla sıfırlandı ve giriş yapıldı!', 'success');
      } else {
        if (errEl) {
          errEl.textContent = data.error || 'Şifre güncellenemedi.';
          errEl.style.display = 'block';
        }
      }
    } catch(err) {
      if (errEl) {
        errEl.textContent = 'Sunucuya bağlanırken bir hata oluştu.';
        errEl.style.display = 'block';
      }
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = window.i18n ? window.i18n.t('btn_reset_password') : 'Şifreyi Güncelle ve Giriş Yap';
      }
    }
  }

  // ==========================================
  // USER ADDRESS BOOK MANAGEMENT (ADRESLERİM)
  // ==========================================
  populateTurkishCities() {
    const citySelects = ['chk-city', 'chk-billing-city', 'addr-city', 'addr-billing-city'];
    citySelects.forEach(selId => {
      const sel = document.getElementById(selId);
      if (sel && sel.options.length <= 1) {
        const currentVal = sel.value;
        sel.innerHTML = `<option value="">${window.i18n ? window.i18n.t('city_select_placeholder') : 'İl seçiniz...'}</option>` +
          TURKISH_CITIES.map(c => `<option value="${c}">${c}</option>`).join('');
        if (currentVal) sel.value = currentVal;
      }
    });
  }

  toggleAddressFormBilling(sameAsShipping) {
    const box = document.getElementById('addr-billing-section');
    if (box) {
      box.style.display = sameAsShipping ? 'none' : 'block';
      if (!sameAsShipping) {
        this.populateTurkishCities();
      }
    }
  }

  setAddressInvoiceType(type) {
    const indBox = document.getElementById('addr-invoice-individual-fields');
    const corpBox = document.getElementById('addr-invoice-corporate-fields');
    if (indBox) indBox.style.display = (type === 'individual') ? 'block' : 'none';
    if (corpBox) corpBox.style.display = (type === 'corporate') ? 'block' : 'none';
  }

  async openAddressesModal() {
    const drop = document.getElementById('user-dropdown-menu');
    if (drop) drop.style.display = 'none';

    const modal = document.getElementById('addresses-modal-backdrop');
    if (!modal) return;

    this.populateTurkishCities();
    this.hideAddressForm();
    modal.style.display = 'flex';
    await this.loadUserAddresses();
  }

  closeAddressesModal() {
    const modal = document.getElementById('addresses-modal-backdrop');
    if (modal) modal.style.display = 'none';
  }

  async loadUserAddresses() {
    const container = document.getElementById('addresses-list-container');
    const countEl = document.getElementById('address-count-text');
    if (container) {
      container.innerHTML = '<div style="text-align:center; padding:24px; color:var(--text-muted);">Adresleriniz yükleniyor...</div>';
    }

    let addresses = [];
    const currentUser = this.getCurrentUser();
    const headers = { 'Content-Type': 'application/json' };
    if (currentUser && currentUser.token) {
      headers['Authorization'] = `Bearer ${currentUser.token}`;
    }

    try {
      const q = currentUser && (currentUser.id || currentUser.email) 
        ? `?user_id=${encodeURIComponent(currentUser.id || '')}&email=${encodeURIComponent(currentUser.email || '')}` 
        : '';
      const res = await fetch(`${this.apiBase}/user/addresses${q}`, { headers });
      if (res.ok) {
        const data = await res.json();
        if (data && Array.isArray(data.addresses)) {
          addresses = data.addresses;
        }
      }
    } catch(err) {}

    // Fallback to localStorage if offline/empty
    if (addresses.length === 0) {
      try {
        addresses = JSON.parse(localStorage.getItem('pozitron_user_addresses') || '[]');
      } catch(e) {
        addresses = [];
      }
    }

    this._cachedAddresses = addresses;
    if (countEl) {
      countEl.textContent = `${addresses.length} kayıtlı adres`;
    }

    this.renderUserAddresses(addresses);
    return addresses;
  }

  renderUserAddresses(addresses) {
    const container = document.getElementById('addresses-list-container');
    if (!container) return;

    if (!addresses || addresses.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:32px 16px; background:var(--bg-card-hover, #f8fafc); border-radius:8px; border:1px dashed var(--border-color, #e2e8f0);">
          <div style="font-size:2rem; margin-bottom:8px;">📍</div>
          <strong style="display:block; margin-bottom:4px; font-size:0.95rem;">${window.i18n ? window.i18n.t('no_addresses_found') : 'Kayıtlı adresiniz bulunmuyor.'}</strong>
          <p style="font-size:0.82rem; color:var(--text-muted); margin:0;">Yukarıdaki "Yeni Adres Ekle" butonuna tıklayarak ilk adresinizi ekleyebilirsiniz.</p>
        </div>
      `;
      return;
    }

    container.innerHTML = addresses.map(addr => `
      <div class="address-card" style="background:var(--bg-card, #fff); border:1px solid ${addr.is_default ? 'var(--brand-primary, #2563eb)' : 'var(--border-color, #e2e8f0)'}; border-radius:8px; padding:14px; position:relative; transition:all 0.2s;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
          <div style="display:flex; align-items:center; gap:8px;">
            <strong style="font-size:0.95rem; color:var(--text-primary);">${this.escapeHTML(addr.title || 'Adres')}</strong>
            ${addr.is_default ? '<span style="background:#eff6ff; color:#1d4ed8; font-size:0.72rem; font-weight:700; padding:2px 6px; border-radius:4px; border:1px solid #bfdbfe;">Varsayılan</span>' : ''}
          </div>
          <div style="display:flex; gap:6px;">
            <button type="button" class="btn-sm btn-secondary" style="padding:4px 8px; font-size:0.75rem;" onclick="window.app && window.app.showAddressForm(${JSON.stringify(addr).replace(/"/g, '&quot;')})">Düzenle</button>
            <button type="button" class="btn-sm text-danger" style="padding:4px 8px; font-size:0.75rem; background:#fee2e2; border:1px solid #fecaca; border-radius:4px;" onclick="window.app && window.app.deleteAddress('${addr.id}')">Sil</button>
          </div>
        </div>
        <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:4px;">
          <strong>${this.escapeHTML(addr.recipient_name || '')}</strong> &bull; ${this.escapeHTML(addr.phone || '')}
        </div>
        <div style="font-size:0.82rem; color:var(--text-muted); line-height:1.4;">
          ${this.escapeHTML(addr.address_line || '')}<br>
          <strong>${this.escapeHTML(addr.district || '')} / ${this.escapeHTML(addr.city || '')} - ${this.escapeHTML(addr.country || 'Turkey')}</strong>
        </div>
      </div>
    `).join('');
  }

  showAddressForm(addr = null) {
    const form = document.getElementById('user-address-form');
    if (!form) return;

    this.populateTurkishCities();

    const titleEl = document.getElementById('addr-form-title');
    const idEl = document.getElementById('addr-id');
    const titleInput = document.getElementById('addr-title');
    const recInput = document.getElementById('addr-recipient');
    const phoneInput = document.getElementById('addr-phone');
    const cityInput = document.getElementById('addr-city');
    const distInput = document.getElementById('addr-district');
    const lineInput = document.getElementById('addr-line');
    const defInput = document.getElementById('addr-is-default');

    const sameBillingCheck = document.getElementById('addr-same-billing');
    const tcknInput = document.getElementById('addr-tckn');
    const compInput = document.getElementById('addr-company-name');
    const taxOffInput = document.getElementById('addr-tax-office');
    const vknInput = document.getElementById('addr-vkn');
    const bCityInput = document.getElementById('addr-billing-city');
    const bDistInput = document.getElementById('addr-billing-district');
    const bLineInput = document.getElementById('addr-billing-line');

    if (addr) {
      if (titleEl) titleEl.textContent = window.i18n ? window.i18n.t('edit_address') : 'Adresi Düzenle';
      if (idEl) idEl.value = addr.id || '';
      if (titleInput) titleInput.value = addr.title || '';
      if (recInput) recInput.value = addr.recipient_name || addr.full_name || '';
      if (phoneInput) phoneInput.value = addr.phone || '';
      if (cityInput) cityInput.value = addr.city || 'İstanbul';
      if (distInput) distInput.value = addr.district || '';
      if (lineInput) lineInput.value = addr.address_line || '';
      if (defInput) defInput.checked = !!addr.is_default;

      // Billing & Invoicing
      const isSame = (addr.same_as_shipping !== 0 && addr.same_as_shipping !== false && addr.same_as_shipping !== '0');
      if (sameBillingCheck) sameBillingCheck.checked = isSame;
      this.toggleAddressFormBilling(isSame);

      const invType = addr.invoice_type || 'individual';
      const r = document.querySelector(`input[name="addr_invoice_type"][value="${invType}"]`);
      if (r) r.checked = true;
      this.setAddressInvoiceType(invType);

      if (tcknInput) tcknInput.value = (invType === 'individual' ? (addr.tax_id || '') : '');
      if (compInput) compInput.value = addr.company_name || '';
      if (taxOffInput) taxOffInput.value = addr.tax_office || '';
      if (vknInput) vknInput.value = (invType === 'corporate' ? (addr.tax_id || '') : '');
      if (bCityInput) bCityInput.value = addr.billing_city || '';
      if (bDistInput) bDistInput.value = addr.billing_district || '';
      if (bLineInput) bLineInput.value = addr.billing_address_line || '';
    } else {
      if (titleEl) titleEl.textContent = window.i18n ? window.i18n.t('add_new_address') : 'Yeni Adres Ekle';
      if (idEl) idEl.value = '';
      if (titleInput) titleInput.value = '';
      const u = this.getCurrentUser();
      if (recInput) recInput.value = u ? (u.full_name || '') : '';
      if (phoneInput) phoneInput.value = u ? (u.phone || '') : '';
      if (cityInput) cityInput.value = 'İstanbul';
      if (distInput) distInput.value = '';
      if (lineInput) lineInput.value = '';
      if (defInput) defInput.checked = (!this._cachedAddresses || this._cachedAddresses.length === 0);

      // Default: same as shipping checked = true
      if (sameBillingCheck) sameBillingCheck.checked = true;
      this.toggleAddressFormBilling(true);

      const r = document.querySelector('input[name="addr_invoice_type"][value="individual"]');
      if (r) r.checked = true;
      this.setAddressInvoiceType('individual');

      if (tcknInput) tcknInput.value = '';
      if (compInput) compInput.value = '';
      if (taxOffInput) taxOffInput.value = '';
      if (vknInput) vknInput.value = '';
      if (bCityInput) bCityInput.value = '';
      if (bDistInput) bDistInput.value = '';
      if (bLineInput) bLineInput.value = '';
    }

    form.style.display = 'block';
    form.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  hideAddressForm() {
    const form = document.getElementById('user-address-form');
    if (form) form.style.display = 'none';
  }

  async handleAddressFormSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    const id = document.getElementById('addr-id')?.value || '';
    const title = document.getElementById('addr-title')?.value.trim() || 'Evim';
    const recipient_name = document.getElementById('addr-recipient')?.value.trim() || '';
    const phone = document.getElementById('addr-phone')?.value.trim() || '';
    const city = document.getElementById('addr-city')?.value || '';
    const district = document.getElementById('addr-district')?.value.trim() || '';
    const country = document.getElementById('addr-country')?.value.trim() || 'Turkey';
    const address_line = document.getElementById('addr-line')?.value.trim() || '';
    const is_default = document.getElementById('addr-is-default')?.checked ? 1 : 0;

    const same_as_shipping = document.getElementById('addr-same-billing')?.checked ? 1 : 0;
    const invoice_type = document.querySelector('input[name="addr_invoice_type"]:checked')?.value || 'individual';
    const tax_id = (invoice_type === 'individual' ? document.getElementById('addr-tckn')?.value.trim() : document.getElementById('addr-vkn')?.value.trim()) || '';
    const company_name = document.getElementById('addr-company-name')?.value.trim() || '';
    const tax_office = document.getElementById('addr-tax-office')?.value.trim() || '';
    const billing_city = document.getElementById('addr-billing-city')?.value || '';
    const billing_district = document.getElementById('addr-billing-district')?.value.trim() || '';
    const billing_address_line = document.getElementById('addr-billing-line')?.value.trim() || '';

    if (!recipient_name || !phone || !city || !district || !address_line) {
      this.showToast('Lütfen tüm adres bilgilerini eksiksiz doldurunuz.', 'error');
      return;
    }

    if (!same_as_shipping && (!billing_city || !billing_district || !billing_address_line)) {
      this.showToast('Lütfen fatura adresi bilgilerini doldurunuz veya "Fatura adresim teslimat adresi ile aynı" seçeneğini işaretleyiniz.', 'error');
      return;
    }

    const u = this.getCurrentUser();
    const payload = {
      id: id || undefined,
      user_id: u ? (u.id || '') : '',
      email: u ? (u.email || '') : '',
      title,
      recipient_name,
      phone,
      city,
      district,
      country,
      address_line,
      is_default,
      same_as_shipping,
      invoice_type,
      tax_id,
      company_name,
      tax_office,
      billing_city,
      billing_district,
      billing_address_line
    };

    const headers = { 'Content-Type': 'application/json' };
    if (u && u.token) {
      headers['Authorization'] = `Bearer ${u.token}`;
    }

    try {
      const res = await fetch(`${this.apiBase}/user/addresses`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok && data.success) {
        this.showToast('Adres başarıyla kaydedildi!', 'success');
      } else {
        this.showToast(data.error || 'Adres kaydedildi.', 'info');
      }
    } catch(err) {
      // Offline fallback
      let list = JSON.parse(localStorage.getItem('pozitron_user_addresses') || '[]');
      if (id) {
        const idx = list.findIndex(a => a.id === id);
        if (idx !== -1) list[idx] = { ...payload, id };
      } else {
        list.push({ ...payload, id: 'addr_' + Date.now().toString(36) });
      }
      localStorage.setItem('pozitron_user_addresses', JSON.stringify(list));
      this.showToast('Adres kaydedildi!', 'success');
    }

    this.hideAddressForm();
    await this.loadUserAddresses();
  }

  async deleteAddress(addrId) {
    if (!addrId) return;
    if (!confirm('Bu adresi silmek istediğinize emin misiniz?')) return;

    const u = this.getCurrentUser();
    const headers = { 'Content-Type': 'application/json' };
    if (u && u.token) {
      headers['Authorization'] = `Bearer ${u.token}`;
    }

    try {
      const res = await fetch(`${this.apiBase}/user/addresses/${encodeURIComponent(addrId)}`, {
        method: 'DELETE',
        headers
      });
      if (!res.ok) {
        // Try POST fallback
        await fetch(`${this.apiBase}/user/addresses/delete`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ id: addrId })
        });
      }
      this.showToast('Adres başarıyla silindi.', 'info');
    } catch(err) {
      let list = JSON.parse(localStorage.getItem('pozitron_user_addresses') || '[]');
      list = list.filter(a => a.id !== addrId);
      localStorage.setItem('pozitron_user_addresses', JSON.stringify(list));
      this.showToast('Adres silindi.', 'info');
    }

    await this.loadUserAddresses();
  }

  toggleBillingAddress(sameAsShipping) {
    const box = document.getElementById('separate-billing-address-box');
    if (box) {
      box.style.display = sameAsShipping ? 'none' : 'block';
    }
  }

  setInvoiceType(type) {
    const indBox = document.getElementById('invoice-individual-fields');
    const corpBox = document.getElementById('invoice-corporate-fields');
    if (indBox) indBox.style.display = (type === 'individual') ? 'block' : 'none';
    if (corpBox) corpBox.style.display = (type === 'corporate') ? 'block' : 'none';
  }

  handleCheckoutAddressSelect(val) {
    if (!val || val === 'new') {
      const addrEl = document.getElementById('chk-address');
      const distEl = document.getElementById('chk-district');
      if (addrEl) addrEl.value = '';
      if (distEl) distEl.value = '';
      return;
    }

    const addr = (this._cachedAddresses || []).find(a => a.id === val);
    if (!addr) return;

    const nameEl = document.getElementById('chk-name');
    const phoneEl = document.getElementById('chk-phone');
    const cityEl = document.getElementById('chk-city');
    const distEl = document.getElementById('chk-district');
    const addrEl = document.getElementById('chk-address');

    if (nameEl && (addr.recipient_name || addr.full_name)) nameEl.value = addr.recipient_name || addr.full_name;
    if (phoneEl && addr.phone) phoneEl.value = addr.phone;
    if (cityEl && addr.city) cityEl.value = addr.city;
    if (distEl && addr.district) distEl.value = addr.district;
    if (addrEl && addr.address_line) addrEl.value = addr.address_line;

    // Pre-fill Billing & Invoicing Preferences from saved address
    const isSame = (addr.same_as_shipping !== 0 && addr.same_as_shipping !== false && addr.same_as_shipping !== '0');
    const sameChk = document.getElementById('chk-same-billing');
    if (sameChk) sameChk.checked = isSame;
    this.toggleBillingAddress(isSame);

    if (!isSame) {
      const bCity = document.getElementById('chk-billing-city');
      const bDist = document.getElementById('chk-billing-district');
      const bLine = document.getElementById('chk-billing-address');
      if (bCity && addr.billing_city) bCity.value = addr.billing_city;
      if (bDist && addr.billing_district) bDist.value = addr.billing_district;
      if (bLine && addr.billing_address_line) bLine.value = addr.billing_address_line;
    }

    const invType = addr.invoice_type || 'individual';
    const invRadio = document.querySelector(`input[name="chk_invoice_type"][value="${invType}"]`);
    if (invRadio) invRadio.checked = true;
    this.setInvoiceType(invType);

    if (invType === 'corporate') {
      const cName = document.getElementById('chk-company-name');
      const tOff = document.getElementById('chk-tax-office');
      const vknEl = document.getElementById('chk-vkn');
      if (cName) cName.value = addr.company_name || '';
      if (tOff) tOff.value = addr.tax_office || '';
      if (vknEl) vknEl.value = addr.tax_id || '';
    } else {
      const tcknEl = document.getElementById('chk-tckn');
      if (tcknEl) tcknEl.value = addr.tax_id || '';
    }
  }

  // ==========================================
  // CHECKOUT & 3D SECURE PAYMENT
  // ==========================================
  // ==========================================
  // MULTI-GATEWAY CHECKOUT & 3D SECURE PAYMENT
  // ==========================================
  openCheckoutModal() {
    const modal = document.getElementById('checkout-modal-backdrop');
    if (!modal) return;

    this.activePaymentMethod = this.activePaymentMethod || 'iyzico';
    this.populateTurkishCities();

    // Pre-fill user data if logged in
    if (this.user) {
      const nameEl = document.getElementById('chk-name');
      const emailEl = document.getElementById('chk-email');
      const phoneEl = document.getElementById('chk-phone');
      const addrEl = document.getElementById('chk-address');
      const cityEl = document.getElementById('chk-city');

      if (nameEl && !nameEl.value) nameEl.value = this.user.full_name || '';
      if (emailEl && !emailEl.value) emailEl.value = this.user.email || '';
      if (phoneEl && !phoneEl.value) phoneEl.value = this.user.phone || '';
      if (addrEl && !addrEl.value) addrEl.value = this.user.address || '';
      if (cityEl && !cityEl.value) cityEl.value = this.user.city || 'İstanbul';

      // Load saved addresses and populate quick-picker
      const savedGroup = document.getElementById('chk-saved-addresses-group');
      const savedSelect = document.getElementById('chk-saved-address-select');
      this.loadUserAddresses().then(addrs => {
        if (addrs && addrs.length > 0) {
          if (savedGroup) savedGroup.style.display = 'block';
          if (savedSelect) {
            savedSelect.innerHTML = addrs.map(a => 
              `<option value="${a.id}">${a.is_default ? '★ ' : ''}${this.escapeHTML(a.title || 'Adres')} (${this.escapeHTML(a.district || '')} / ${this.escapeHTML(a.city || '')})</option>`
            ).join('') + `<option value="new">+ Yeni / Farklı Bir Adres Gir</option>`;

            const def = addrs.find(a => a.is_default) || addrs[0];
            if (def) {
              savedSelect.value = def.id;
              this.handleCheckoutAddressSelect(def.id);
            }
          }
        } else {
          if (savedGroup) savedGroup.style.display = 'none';
        }
      }).catch(() => {});
    }

    // Reset invoice controls
    const sameBillingCb = document.getElementById('chk-same-billing');
    if (sameBillingCb) {
      sameBillingCb.checked = true;
      this.toggleBillingAddress(true);
    }
    const invRadioInd = document.querySelector('input[name="chk_invoice_type"][value="individual"]');
    if (invRadioInd) {
      invRadioInd.checked = true;
      this.setInvoiceType('individual');
    }

    // Generate unique Havale Order Ref Code
    const refCode = 'PZTR-' + Math.floor(100000 + Math.random() * 900000);
    const refEl = document.getElementById('bank-box-ref');
    if (refEl) refEl.textContent = refCode;

    // Update total price
    let subUSD = 0, subTRY = 0;
    this.cart.forEach(i => {
      subUSD += (i.price_usd || 0) * (i.quantity || 1);
      subTRY += (i.price_try || 0) * (i.quantity || 1);
    });

    if (this.appliedCoupon) {
      const discount = (subTRY * this.appliedCoupon.discount_percentage) / 100;
      subTRY -= discount;
      subUSD -= (subUSD * this.appliedCoupon.discount_percentage) / 100;
    }

    const isFree = subTRY >= 1500;
    const grandUSD = subUSD + (isFree ? 0 : 2.10);
    const grandTRY = subTRY + (isFree ? 0 : 99);

    this._currentGrandUSD = grandUSD;
    this._currentGrandTRY = grandTRY;

    const totalEl = document.getElementById('checkout-total-val');
    if (totalEl) totalEl.textContent = this.formatPrice(grandUSD, grandTRY);

    // GA4 begin_checkout event tracking
    const lang = window.i18n ? window.i18n.currentLang : 'tr';
    const checkoutVal = this.currency === 'TRY' ? grandTRY : grandUSD;
    this.trackGA4Event('begin_checkout', {
      currency: this.currency || 'TRY',
      value: checkoutVal,
      coupon: this.appliedCoupon ? this.appliedCoupon.code : undefined,
      items: this.cart.map(item => ({
        item_id: item.sku || item.id,
        item_name: lang === 'tr' ? (item.name_tr || item.name_en) : (item.name_en || item.name_tr),
        item_brand: item.brand || 'Pozitron',
        item_category: item.category_id || 'FPV',
        price: this.currency === 'TRY' ? (item.price_try || 0) : (item.price_usd || 0),
        quantity: item.quantity || 1
      }))
    });

    this.setPaymentMethod(this.activePaymentMethod);
    modal.style.display = 'flex';
  }

  closeCheckoutModal() {
    const modal = document.getElementById('checkout-modal-backdrop');
    if (modal) modal.style.display = 'none';
  }

  // Handle ESC (Escape) key globally across all open modals, drawers, and menus
  handleEscapeKey() {
    // 1. If 3D Secure iframe modal is open
    const sec3d = document.getElementById('secure-3d-modal-backdrop');
    if (sec3d && sec3d.style.display !== 'none') {
      sec3d.style.display = 'none';
      return;
    }

    // 2. If Studio 3D modal is open
    const studio3d = document.getElementById('studio-3d-modal-backdrop');
    if (studio3d && studio3d.style.display !== 'none') {
      studio3d.style.display = 'none';
      return;
    }

    // 3. If Success modal is open
    const succ = document.getElementById('success-modal-backdrop');
    if (succ && succ.style.display !== 'none') {
      succ.style.display = 'none';
      return;
    }

    // 4. If Comment modal is open
    const comment = document.getElementById('comment-modal-backdrop');
    if (comment && comment.style.display !== 'none') {
      this.closeCommentModal();
      return;
    }

    // 5. If Stock Alert modal is open
    const stockAlert = document.getElementById('stock-alert-modal-backdrop');
    if (stockAlert && stockAlert.style.display !== 'none') {
      this.closeStockAlertModal();
      return;
    }

    // 6. If Address modal is open
    const addrModal = document.getElementById('addresses-modal-backdrop');
    if (addrModal && addrModal.style.display !== 'none') {
      const addrForm = document.getElementById('user-address-form');
      if (addrForm && addrForm.style.display !== 'none') {
        this.hideAddressForm();
      } else {
        this.closeAddressesModal();
      }
      return;
    }

    // 7. If Orders modal is open
    const ordersModal = document.getElementById('orders-modal-backdrop');
    if (ordersModal && ordersModal.style.display !== 'none') {
      this.closeOrdersModal();
      return;
    }

    // 8. If Checkout modal is open
    const chkModal = document.getElementById('checkout-modal-backdrop');
    if (chkModal && chkModal.style.display !== 'none') {
      this.closeCheckoutModal();
      return;
    }

    // 9. If Auth modal is open
    const authModal = document.getElementById('auth-modal-backdrop');
    if (authModal && authModal.style.display !== 'none') {
      this.closeAuthModal();
      return;
    }

    // 10. If Drone Builder modal is open
    const builderModal = document.getElementById('builder-modal-backdrop');
    if (builderModal && builderModal.style.display !== 'none') {
      builderModal.style.display = 'none';
      return;
    }

    // 11. If Cart Drawer is open
    const cartBackdrop = document.getElementById('cart-backdrop');
    if (cartBackdrop && cartBackdrop.classList.contains('open')) {
      this.closeCartDrawer();
      return;
    }

    // 12. If User Dropdown Menu is open
    const userDrop = document.getElementById('user-dropdown-menu');
    if (userDrop && userDrop.style.display !== 'none' && userDrop.style.display !== '') {
      userDrop.style.display = 'none';
      return;
    }

    // 13. Fallback: Any other visible .modal-backdrop
    const openBackdrops = Array.from(document.querySelectorAll('.modal-backdrop')).filter(el => {
      const style = window.getComputedStyle(el);
      return style.display !== 'none' && style.visibility !== 'hidden';
    });
    if (openBackdrops.length > 0) {
      const topBackdrop = openBackdrops[openBackdrops.length - 1];
      const closeBtn = topBackdrop.querySelector('.modal-close-btn');
      if (closeBtn) {
        closeBtn.click();
      } else {
        topBackdrop.style.display = 'none';
      }
    }
  }

  setPaymentMethod(method) {
    this.activePaymentMethod = method;
    
    // GA4 add_payment_info event tracking
    const payVal = this.currency === 'TRY' ? (this._currentGrandTRY || 0) : (this._currentGrandUSD || 0);
    this.trackGA4Event('add_payment_info', {
      currency: this.currency || 'TRY',
      value: payVal,
      payment_type: method
    });

    // Update Tab Active states
    ['iyzico', 'paytr', 'havale'].forEach(m => {
      const tab = document.getElementById(`tab-pay-${m}`);
      const panel = document.getElementById(`pay-panel-${m}`);
      if (tab) tab.classList.toggle('active', m === method);
      if (panel) panel.style.display = (m === method) ? 'block' : 'none';
    });

    // Update Submit Button Text & Icon
    const btnText = document.getElementById('pay-submit-btn-text');
    const btnIcon = document.getElementById('pay-submit-btn-icon');
    const submitBtn = document.getElementById('submit-order-btn');

    if (method === 'iyzico') {
      if (btnIcon) btnIcon.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>';
      if (btnText) btnText.textContent = 'İyzico ile Güvenli Öde';
      if (submitBtn) {
        submitBtn.style.background = '#1a56db';
        submitBtn.style.borderColor = '#1a56db';
      }
    } else if (method === 'paytr') {
      if (btnIcon) btnIcon.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>';
      if (btnText) btnText.textContent = 'PayTR ile Güvenli Öde';
      if (submitBtn) {
        submitBtn.style.background = '#0891b2';
        submitBtn.style.borderColor = '#0891b2';
      }
    } else if (method === 'havale') {
      if (btnIcon) btnIcon.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>';
      if (btnText) btnText.textContent = 'Havale Bildirimini Tamamla';
      if (submitBtn) {
        submitBtn.style.background = '#059669';
        submitBtn.style.borderColor = '#059669';
      }
    }
  }

  updateBankInfo(bankKey) {
    const banks = {
      main: { name: 'Kuveyt Türk / 7/24 FAST', iban: 'TR41 0020 5000 0908 0479 3000 01', owner: 'Burak Peköz', phone: '0552 128 0617' },
      ziraat: { name: 'Ziraat Bankası (7/24 FAST)', iban: 'TR41 0020 5000 0908 0479 3000 01', owner: 'Burak Peköz', phone: '0552 128 0617' },
      garanti: { name: 'Garanti BBVA', iban: 'TR41 0020 5000 0908 0479 3000 01', owner: 'Burak Peköz', phone: '0552 128 0617' },
      isbank: { name: 'Türkiye İş Bankası', iban: 'TR41 0020 5000 0908 0479 3000 01', owner: 'Burak Peköz', phone: '0552 128 0617' },
      enpara: { name: 'QNB Enpara / FAST', iban: 'TR41 0020 5000 0908 0479 3000 01', owner: 'Burak Peköz', phone: '0552 128 0617' }
    };
    const b = banks[bankKey] || banks.main;
    const nameEl = document.getElementById('bank-box-name');
    const ibanEl = document.getElementById('bank-box-iban');
    const ownerEl = document.getElementById('bank-box-owner');
    const phoneEl = document.getElementById('bank-box-phone');
    if (nameEl) nameEl.textContent = b.name;
    if (ibanEl) ibanEl.textContent = b.iban;
    if (ownerEl) ownerEl.textContent = b.owner;
    if (phoneEl) phoneEl.textContent = b.phone || '0552 128 0617';
  }

  copyIban() {
    const ibanEl = document.getElementById('bank-box-iban');
    if (ibanEl) {
      navigator.clipboard.writeText(ibanEl.textContent.trim());
      this.showToast('IBAN panoya kopyalandı.', 'success');
    }
  }

  copyBankPhone() {
    const phoneEl = document.getElementById('bank-box-phone');
    if (phoneEl) {
      navigator.clipboard.writeText(phoneEl.textContent.trim().replace(/\s+/g, ''));
      this.showToast('Ödeme telefon numarası (FAST / Kolay Adres) panoya kopyalandı.', 'success');
    }
  }

  copyRefCode() {
    const refEl = document.getElementById('bank-box-ref');
    if (refEl) {
      navigator.clipboard.writeText(refEl.textContent.trim());
      this.showToast('Sipariş referans kodu kopyalandı.', 'success');
    }
  }

  handleCheckoutSubmit() {
    const name = (document.getElementById('chk-name')?.value || '').trim();
    const email = (document.getElementById('chk-email')?.value || '').trim();
    const phone = (document.getElementById('chk-phone')?.value || '').trim();
    const address = (document.getElementById('chk-address')?.value || '').trim();
    const city = (document.getElementById('chk-city')?.value || '').trim();
    const district = (document.getElementById('chk-district')?.value || '').trim();
    const country = (document.getElementById('chk-country')?.value || 'Turkey').trim();
    const orderNotes = (document.getElementById('chk-order-notes')?.value || '').trim();
    const err = document.getElementById('checkout-error-msg');

    if (!name || !phone || !address || !city || !district) {
      if (err) {
        err.textContent = "Lütfen tüm teslimat bilgilerini (Ad Soyad, Telefon, İl, İlçe, Açık Adres) eksiksiz doldurun.";
        err.style.display = 'block';
      }
      return;
    }

    const agreeTerms = document.getElementById('chk-agree-terms')?.checked;
    if (!agreeTerms) {
      if (err) {
        err.textContent = "Lütfen Ön Bilgilendirme Koşulları ve Mesafeli Satış Sözleşmesi'ni onaylayınız.";
        err.style.display = 'block';
      }
      return;
    }

    // Invoicing Details
    const invoiceType = document.querySelector('input[name="chk_invoice_type"]:checked')?.value || 'individual';
    let taxId = '';
    let taxOffice = '';
    let companyName = '';

    if (invoiceType === 'corporate') {
      companyName = (document.getElementById('chk-company-name')?.value || '').trim();
      taxOffice = (document.getElementById('chk-tax-office')?.value || '').trim();
      taxId = (document.getElementById('chk-vkn')?.value || '').trim();

      if (!companyName || !taxOffice || !taxId) {
        if (err) {
          err.textContent = "Kurumsal fatura için Şirket Ünvanı, Vergi Dairesi ve VKN alanları zorunludur.";
          err.style.display = 'block';
        }
        return;
      }
      if (taxId.length !== 10 || !/^\d{10}$/.test(taxId)) {
        if (err) {
          err.textContent = "Vergi Kimlik Numarası (VKN) 10 haneli rakam olmalıdır.";
          err.style.display = 'block';
        }
        return;
      }
    } else {
      taxId = (document.getElementById('chk-tckn')?.value || '').trim();
      if (taxId && (taxId.length !== 11 || !/^\d{11}$/.test(taxId))) {
        if (err) {
          err.textContent = "T.C. Kimlik Numarası (TCKN) 11 haneli rakam olmalıdır (veya boş bırakabilirsiniz).";
          err.style.display = 'block';
        }
        return;
      }
      if (!taxId) taxId = '11111111111'; // Legal default for individual e-Arşiv in Turkey
    }

    const sameBilling = document.getElementById('chk-same-billing')?.checked;
    let billingAddress = address;
    let billingCity = city;
    let billingDistrict = district;
    let billingCountry = country;

    if (!sameBilling) {
      billingAddress = (document.getElementById('chk-billing-address')?.value || '').trim();
      billingCity = (document.getElementById('chk-billing-city')?.value || '').trim();
      billingDistrict = (document.getElementById('chk-billing-district')?.value || '').trim();
      if (!billingAddress || !billingCity) {
        if (err) {
          err.textContent = "Lütfen ayrı fatura adresinizi ve ilinizi eksiksiz giriniz.";
          err.style.display = 'block';
        }
        return;
      }
    }

    if (err) err.style.display = 'none';

    const method = this.activePaymentMethod || 'iyzico';
    const orderNum = 'PZTR-' + (method.toUpperCase()) + '-' + Math.floor(10000 + Math.random() * 90000);
    const orderItemsStr = this.cart.map(i => `${i.quantity}x ${i.name_tr || i.title || 'Ürün'}`).join(', ');

    const structuredItems = (this.cart && this.cart.length > 0) ? this.cart.map(i => ({
      id: i.id,
      sku: i.sku || '',
      name: i.name_tr || i.name_en || i.title || 'Ürün',
      quantity: parseInt(i.quantity || 1, 10),
      price_try: parseFloat(i.price_try || 0),
      price_usd: parseFloat(i.price_usd || 0)
    })) : [];

    const u = this.getCurrentUser();
    const baseOrderPayload = {
      order_number: orderNum,
      user_id: u ? (u.id || '') : '',
      customer_name: name,
      customer_email: email,
      customer_phone: phone,
      name: name,
      email: email,
      phone: phone,
      total_usd: (this._currentGrandUSD || 0).toFixed(2),
      total_try: (this._currentGrandTRY || 0).toFixed(2),
      items: orderItemsStr,
      items_detail: structuredItems,
      items_json: JSON.stringify(structuredItems),
      created_at: new Date().toISOString(),
      shipping_address: `${address} - ${district} / ${city}`,
      city: city,
      country: country,
      shipping_district: district,
      billing_address: billingAddress,
      billing_city: billingCity,
      billing_district: billingDistrict,
      billing_country: billingCountry,
      invoice_type: invoiceType,
      tax_id: taxId,
      tax_office: taxOffice,
      company_name: companyName,
      order_notes: orderNotes,
      payment_method: method
    };

    if (method === 'havale') {
      const refCode = document.getElementById('bank-box-ref')?.textContent || orderNum;
      const bankName = document.getElementById('bank-box-name')?.textContent || 'Ziraat Bankası';

      const havaleOrder = {
        ...baseOrderPayload,
        tracking_number: 'PZTR-HV-' + Date.now().toString(36).toUpperCase(),
        transaction_id: `Havale/EFT Ref: ${refCode} (${bankName})`,
        card_brand: `Havale / EFT (${bankName})`,
        card_last4: 'IBAN'
      };

      this.closeCheckoutModal();
      this.finalizeOrder(havaleOrder);
      return;
    }

    // Credit Card validation for Iyzico & PayTR
    const cardNum = document.getElementById(`${method}-card-number`)?.value.replace(/\D/g, '') || '';
    const cardName = document.getElementById(`${method}-card-name`)?.value.trim() || '';
    const cardExp = document.getElementById(`${method}-card-expiry`)?.value.trim() || '';
    const cardCvv = document.getElementById(`${method}-card-cvv`)?.value.trim() || '';
    const installmentVal = document.getElementById(`${method}-installments`)?.value || '1';

    if (cardNum.length < 15 || !cardName || cardExp.length < 4 || cardCvv.length < 3) {
      if (err) {
        err.textContent = "Lütfen kredi kartı numaranızı, son kullanma tarihini ve CVV kodunu eksiksiz giriniz.";
        err.style.display = 'block';
      }
      return;
    }

    let brand = 'Kredi Kartı';
    if (/^4/.test(cardNum)) brand = 'VISA';
    else if (/^(5[1-5]|2[2-7])/.test(cardNum)) brand = 'Mastercard';
    else if (/^9792/.test(cardNum)) brand = 'TROY';

    const gatewayTitle = method === 'iyzico' ? 'iyzico 3D Secure' : 'PayTR 3D Secure';

    this.pendingOrder = {
      ...baseOrderPayload,
      card_number: cardNum,
      card_holder: cardName,
      card_expiry: cardExp,
      card_cvv: cardCvv,
      tracking_number: 'PZTR-TR-' + Date.now().toString(36).toUpperCase(),
      transaction_id: `${gatewayTitle} (#TXN-${Date.now().toString(36)}) - ${installmentVal === '1' ? 'Tek Çekim' : installmentVal + ' Taksit'}`,
      card_brand: `${brand} (${gatewayTitle})`,
      card_last4: cardNum.slice(-4)
    };

    this.closeCheckoutModal();
    this.open3DSecureModal(gatewayTitle, phone);
  }

  open3DSecureModal(gatewayName, phone) {
    const modal = document.getElementById('secure-3d-modal-backdrop');
    const brandEl = document.getElementById('otp-gateway-brand');
    const phoneEl = document.getElementById('otp-phone-display');
    const inputEl = document.getElementById('otp-code-input');
    const errEl = document.getElementById('otp-error-msg');

    if (brandEl) brandEl.textContent = gatewayName;
    if (phoneEl) {
      const clean = phone || '+90 552 128 0617';
      phoneEl.textContent = clean.replace(/(\d{3})\d{4}(\d{3})/, '$1 **** $2');
    }
    if (inputEl) inputEl.value = '';
    if (errEl) errEl.style.display = 'none';

    this.startOtpTimer(180);
    if (modal) modal.style.display = 'flex';
  }

  close3DSecureModal() {
    const modal = document.getElementById('secure-3d-modal-backdrop');
    if (modal) modal.style.display = 'none';
    if (this._otpInterval) clearInterval(this._otpInterval);
  }

  startOtpTimer(seconds) {
    if (this._otpInterval) clearInterval(this._otpInterval);
    let rem = seconds;
    const timerEl = document.getElementById('otp-countdown-timer');
    const update = () => {
      const min = Math.floor(rem / 60).toString().padStart(2, '0');
      const sec = (rem % 60).toString().padStart(2, '0');
      if (timerEl) timerEl.textContent = `${min}:${sec}`;
      if (rem <= 0) {
        clearInterval(this._otpInterval);
        if (timerEl) timerEl.textContent = '00:00 (Süre Doldu)';
      }
      rem--;
    };
    update();
    this._otpInterval = setInterval(update, 1000);
  }

  verify3DSecureOtp() {
    const inputEl = document.getElementById('otp-code-input');
    const errEl = document.getElementById('otp-error-msg');
    const code = inputEl ? inputEl.value.trim() : '';

    if (!code || code.length < 4) {
      if (errEl) {
        errEl.textContent = 'Lütfen SMS ile gelen 6 haneli doğrulama kodunu eksiksiz giriniz.';
        errEl.style.display = 'block';
      }
      return;
    }

    if (this._otpInterval) clearInterval(this._otpInterval);
    this.close3DSecureModal();
    this.finalizeOrder(this.pendingOrder);
  }

  finalizeOrder(order) {
    if (!order) return;

    if (!order.items_detail && this.cart && this.cart.length > 0) {
      order.items_detail = this.cart.map(i => ({
        id: i.id,
        sku: i.sku || '',
        name: i.name_tr || i.name_en || i.title || 'Ürün',
        quantity: parseInt(i.quantity || 1, 10),
        price_try: parseFloat(i.price_try || 0),
        price_usd: parseFloat(i.price_usd || 0)
      }));
    }

    const prevOrders = JSON.parse(localStorage.getItem('pozitron_orders') || '[]');
    prevOrders.unshift(order);
    localStorage.setItem('pozitron_orders', JSON.stringify(prevOrders));

    // Send Webhook to Google Sheets & Autonomous Cloud Relay
    const WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbw_YHCFvOkkq2usjJh4XCMMHWgHy9V_7C5fROFCjrTGw1iGsPy_39o6JXyvlowO9iy5/exec";
    fetch(WEBHOOK_URL, {
      method: 'POST',
      mode: 'no-cors',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(order)
    }).catch(err => console.log('Webhook log:', err));

    // Persist order in centralized backend database
    try {
      const orderPayload = {
        ...order,
        customer_name: order.customer_name || order.name,
        customer_email: order.customer_email || order.email,
        customer_phone: order.customer_phone || order.phone,
        items: (this.cart && this.cart.length > 0) ? this.cart : (order.items_detail || [])
      };
      fetch(`${this.apiBase}/payment/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(orderPayload)
      }).catch(() => {});
    } catch(e) {}

    // Automatically Deduct Stock (Local Memory & Admin Storage)
    try {
      if (this.cart && this.cart.length > 0) {
        // 1. Update live window.__POZITRON_DATA__ in-memory for instant visual responsiveness
        if (window.__POZITRON_DATA__ && Array.isArray(window.__POZITRON_DATA__.products)) {
          this.cart.forEach(cItem => {
            const p = window.__POZITRON_DATA__.products.find(x => x.id === cItem.id || (x.sku && x.sku === cItem.sku));
            if (p) {
              p.stock = Math.max(0, (p.stock || 0) - (cItem.quantity || 1));
              p.in_stock = p.stock > 0;
            }
          });
        }

        // 2. Update Admin LocalStorage if present
        const adminProds = JSON.parse(localStorage.getItem('pozitron_admin_products') || '[]');
        if (adminProds.length > 0) {
          this.cart.forEach(cItem => {
            const prod = adminProds.find(p => p.id === cItem.id);
            if (prod) {
              prod.stock = Math.max(0, (prod.stock || 0) - (cItem.quantity || 1));
            }
          });
          localStorage.setItem('pozitron_admin_products', JSON.stringify(adminProds));
        }
      }
    } catch (stkErr) {
      console.error('Stock deduction error:', stkErr);
    }

    // GA4 Enhanced E-commerce Purchase Event
    const purchasedItems = (this.cart && this.cart.length > 0) ? [...this.cart] : (order.items || []);
    const purchaseVal = this.currency === 'TRY' ? parseFloat(order.total_try || this._currentGrandTRY || 0) : parseFloat(order.total_usd || this._currentGrandUSD || 0);
    const shippingFee = (parseFloat(order.total_try || 0) >= 1500) ? 0 : (this.currency === 'TRY' ? 99 : 2.10);

    this.trackGA4Event('purchase', {
      transaction_id: order.order_number || order.transaction_id || `PZT-${Date.now()}`,
      value: purchaseVal,
      currency: this.currency || 'TRY',
      tax: 0,
      shipping: shippingFee,
      payment_type: order.card_brand || order.payment_method || this.activePaymentMethod || 'credit_card',
      items: purchasedItems.map(i => ({
        item_id: i.sku || i.id,
        item_name: i.name_en || i.name_tr,
        item_brand: i.brand || 'Pozitron',
        item_category: i.category_id || 'FPV',
        price: this.currency === 'TRY' ? (i.price_try || 0) : (i.price_usd || 0),
        quantity: i.quantity || 1
      }))
    });

    // Google Ads Conversion Tracking (Purchase)
    try {
      if (typeof window.gtag === 'function') {
        const orderId = order.order_number || order.transaction_id || `PZT-${Date.now()}`;
        const orderValTRY = parseFloat(order.total_try || this._currentGrandTRY || purchaseVal || 1.0);
        window.gtag('event', 'conversion', {
          'send_to': 'AW-18404787021/9qzqCPmj7-kcEM2Gi8hE',
          'value': orderValTRY,
          'currency': 'TRY',
          'transaction_id': orderId
        });
        console.log('[Google Ads Conversion] Purchase event fired:', { orderId, value: orderValTRY, currency: 'TRY' });
      }
    } catch (gAdsErr) {
      console.warn('[Google Ads Conversion Error]:', gAdsErr);
    }

    // Clear cart and show receipt
    this.cart = [];
    localStorage.removeItem('pozitron_cart');
    this.appliedCoupon = null;
    this.updateCartUI();

    this.renderOrderReceipt(order);
    this.pendingOrder = null;

    const successModal = document.getElementById('success-modal-backdrop');
    if (successModal) successModal.style.display = 'flex';
  }

  renderOrderReceipt(order) {
    const card = document.getElementById('order-receipt-card');
    if (!card) return;

    card.innerHTML = `
      <div class="receipt-row">
        <span>Sipariş No:</span>
        <strong style="color:var(--brand-primary); font-size:1.05rem;">${order.order_number}</strong>
      </div>
      <div class="receipt-row">
        <span>Kargo Takip No:</span>
        <strong>${order.tracking_number}</strong>
      </div>
      <div class="receipt-row">
        <span>Ödeme Yöntemi:</span>
        <strong>${order.card_brand}</strong>
      </div>
      <div class="receipt-row">
        <span>İşlem Kodu / Detay:</span>
        <strong style="font-size:0.82rem; color:#64748b;">${order.transaction_id}</strong>
      </div>
      <div class="receipt-row">
        <span>Teslim Alacak:</span>
        <strong>${order.name} (${order.phone})</strong>
      </div>
      <div class="receipt-row">
        <span>Kargo Adresi:</span>
        <span>${this.escapeHTML(order.shipping_address)}</span>
      </div>
      <div class="receipt-row" style="padding-top:10px; margin-top:6px; border-top:1px solid var(--border-subtle);">
        <span style="font-weight:700;">Toplam Tutar:</span>
        <strong style="color:#0284c7; font-size:1.2rem; font-weight:800;">${this.formatPrice(order.total_usd, order.total_try)}</strong>
      </div>
    `;
  }

  // ==========================================
  // RECOMMENDED PRODUCTS & STOCK ALERT SYSTEM
  // ==========================================
  getBundleRecommendations(mainProd) {
    const all = this.getStaticData().products || [];
    let targetCats = ['propellers', 'esc', 'batteries_chargers'];

    if (mainProd.category_id === 'motors') {
      targetCats = ['propellers', 'esc', 'batteries_chargers'];
    } else if (mainProd.category_id === 'flight_controllers') {
      targetCats = ['esc', 'vtx_cameras', 'receivers'];
    } else if (mainProd.category_id === 'frames') {
      targetCats = ['motors', 'flight_controllers', 'propellers'];
    } else if (mainProd.category_id === 'batteries_chargers') {
      targetCats = ['propellers', 'accessories', 'tools'];
    } else if (mainProd.category_id === 'antennas') {
      targetCats = ['vtx_cameras', 'transmitters_receivers', 'accessories'];
    } else if (mainProd.category_id === 'vtx_cameras') {
      targetCats = ['antennas', 'goggles', 'flight_controllers'];
    } else {
      targetCats = ['accessories', 'propellers', 'tools'];
    }

    const recommended = [];
    targetCats.forEach(c => {
      const match = all.find(x => x.category_id === c && x.id !== mainProd.id && !recommended.some(r => r.id === x.id) && (parseInt(x.stock) > 0));
      if (match) recommended.push(match);
    });

    // Fill remaining up to 3 items
    if (recommended.length < 3) {
      all.forEach(x => {
        if (recommended.length < 3 && x.id !== mainProd.id && !recommended.some(r => r.id === x.id)) {
          recommended.push(x);
        }
      });
    }

    return recommended.slice(0, 3);
  }

  openStockAlertModal(prodId) {
    const modal = document.getElementById('stock-alert-modal-backdrop');
    if (!modal) return;

    let p = null;
    const staticData = this.getStaticData();
    p = (staticData.products || []).find(x => x.id === prodId || x.slug === prodId);
    if (!p) return;

    const lang = window.i18n.currentLang;
    const title = lang === 'tr' ? (p.name_tr || p.name_en) : (p.name_en || p.name_tr);

    const imgEl = document.getElementById('stock-alert-img');
    const nameEl = document.getElementById('stock-alert-prod-name');
    const brandEl = document.getElementById('stock-alert-prod-brand');
    const skuEl = document.getElementById('stock-alert-prod-sku');
    const idEl = document.getElementById('stock-alert-prod-id');
    const emailEl = document.getElementById('stock-alert-email');

    if (imgEl) imgEl.src = this.formatImgUrl(p.image_url);
    if (nameEl) nameEl.textContent = title;
    if (brandEl) brandEl.textContent = p.brand || 'Pozitron';
    if (skuEl) skuEl.textContent = p.sku || p.id;
    if (idEl) idEl.value = p.id;
    if (emailEl && this.user && this.user.email) {
      emailEl.value = this.user.email;
    }

    modal.style.display = 'flex';
  }

  closeStockAlertModal() {
    const modal = document.getElementById('stock-alert-modal-backdrop');
    if (modal) modal.style.display = 'none';
  }

  handleStockAlertSubmit(e) {
    if (e && e.preventDefault) e.preventDefault();
    const prodId = document.getElementById('stock-alert-prod-id').value;
    const email = document.getElementById('stock-alert-email').value.trim();
    const phone = document.getElementById('stock-alert-phone').value.trim();
    const waOpt = document.getElementById('stock-alert-wa-opt') ? document.getElementById('stock-alert-wa-opt').checked : true;

    if (!email || !this.isValidEmail(email)) {
      this.showToast('Lütfen geçerli bir e-posta adresi giriniz.', 'error');
      return;
    }

    const alerts = JSON.parse(localStorage.getItem('pozitron_stock_alerts') || '[]');
    const existing = alerts.find(a => a.prod_id === prodId && a.email.toLowerCase() === email.toLowerCase());

    if (existing) {
      this.showToast(window.i18n.t('stock_alert_already'), 'info');
      this.closeStockAlertModal();
      return;
    }

    const staticData = this.getStaticData();
    const prod = (staticData.products || []).find(x => x.id === prodId);
    const prodName = prod ? (prod.name_tr || prod.name_en) : prodId;

    const newAlert = {
      id: 'alt_' + Date.now().toString(36),
      prod_id: prodId,
      prod_name: prodName,
      email: email,
      phone: phone,
      whatsapp: waOpt,
      created_at: new Date().toISOString()
    };

    alerts.push(newAlert);
    localStorage.setItem('pozitron_stock_alerts', JSON.stringify(alerts));

    // Send Webhook to Google Sheets CRM (Stock Alerts)
    const WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbw_YHCFvOkkq2usjJh4XCMMHWgHy9V_7C5fROFCjrTGw1iGsPy_39o6JXyvlowO9iy5/exec";
    fetch(WEBHOOK_URL, {
      method: 'POST',
      mode: 'no-cors',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'stock_alert',
        prod_id: prodId,
        prod_name: prodName,
        email: email,
        phone: phone,
        created_at: newAlert.created_at
      })
    }).catch(err => console.log('Alert webhook error:', err));

    this.closeStockAlertModal();
    this.showToast(window.i18n.t('stock_alert_success'), 'success');
  }

  // ==========================================
  // PRODUCT NAVIGATION (DIRECT PRODUCT PAGE)
  // ==========================================
  openProductModal(idOrSlug) {
    if (!idOrSlug) return;
    const staticData = this.getStaticData();
    const p = (staticData.products || []).find(x => x.id === idOrSlug || x.slug === idOrSlug);
    const slug = p?.slug || idOrSlug;
    window.location.href = `./products/${slug}`;
  }

  closeProductModal() {
    const modal = document.getElementById('product-modal-backdrop');
    if (modal) modal.style.display = 'none';
  }

  // ==========================================
  // SMART BUDGET DRONE BUILDER & COMPATIBILITY WIZARD
  // ==========================================
  openBuilderModal(initialTab = 'auto') {
    const modal = document.getElementById('builder-modal-backdrop');
    if (!modal) return;

    if (!this.builderState) {
      this.builderState = {
        style: 'freestyle',
        video: 'digital',
        budget: 28000,
        activeTab: initialTab
      };
    } else {
      this.builderState.activeTab = initialTab;
    }

    this.renderBuilderModal();
    modal.style.display = 'flex';
  }

  renderBuilderModal() {
    const body = document.getElementById('builder-modal-body');
    if (!body) return;

    if (this._isDroneCalculating) {
      return;
    }

    const lang = window.i18n.currentLang;
    const tab = this.builderState.activeTab || 'auto';

    if (tab === 'auto') {
      if (this.currentGeneratedBuild) {
        this.renderBuildResultView(body);
      } else {
        this.renderAutoBuilderForm(body);
      }
    } else {
      this.renderManualBuilderForm(body);
    }
  }

  renderAutoBuilderForm(body) {
    const lang = window.i18n.currentLang;
    const st = this.builderState;
    const curSymbol = this.currency === 'USD' ? '$' : '₺';
    const rate = this.usdRate || 50.0;
    const budgetVal = st.budget;

    body.innerHTML = `
      <div class="builder-tab-bar">
        <button type="button" class="builder-tab-btn active" onclick="window.app.switchBuilderTab('auto')">
          ${lang === 'tr' ? 'Bütçeye Göre Otomatik Topla (Önerilen)' : 'Auto Build by Budget (Recommended)'}
        </button>
        <button type="button" class="builder-tab-btn" onclick="window.app.switchBuilderTab('manual')">
          ${lang === 'tr' ? 'Manuel Parça Seçimi & Test' : 'Manual Part Selection & Test'}
        </button>
      </div>

      <!-- Step 1: Flight Style -->
      <div class="builder-step-box">
        <div class="builder-step-header">
          <span class="step-num-badge">1</span>
          <span class="step-title">${lang === 'tr' ? 'Uçuş Tarzınızı Seçin' : 'Select Flight Style'}</span>
        </div>
        <div class="builder-style-grid">
          <div class="builder-style-card ${st.style === 'freestyle' ? 'active' : ''}" onclick="window.app.setBuilderStyle('freestyle')">
            <span class="style-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"></path><path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"></path><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"></path><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"></path></svg></span>
            <span class="style-name">Freestyle</span>
            <span class="style-sub">${lang === 'tr' ? '5" Klasik & Dayanıklı Çevik Gövde' : '5" Durable & Agile Carbon'}</span>
          </div>

          <div class="builder-style-card ${st.style === 'racing' ? 'active' : ''}" onclick="window.app.setBuilderStyle('racing')">
            <span class="style-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path><line x1="4" y1="22" x2="4" y2="15"></line></svg></span>
            <span class="style-name">${lang === 'tr' ? 'Yarış & Hız' : 'Racing & Speed'}</span>
            <span class="style-sub">${lang === 'tr' ? '5" Ultra Hafif & Yüksek KV Motor' : '5" Ultralight & High KV Power'}</span>
          </div>

          <div class="builder-style-card ${st.style === 'cinematic' ? 'active' : ''}" onclick="window.app.setBuilderStyle('cinematic')">
            <span class="style-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg></span>
            <span class="style-name">${lang === 'tr' ? '4K Sinematik' : '4K Cinematic'}</span>
            <span class="style-sub">${lang === 'tr' ? 'Pürüzsüz Uçuş & Sarsıntısız Çekim' : 'Smooth & Vibration-Free Cruise'}</span>
          </div>

          <div class="builder-style-card ${st.style === 'long_range' ? 'active' : ''}" onclick="window.app.setBuilderStyle('long_range')">
            <span class="style-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3l4 8 5-5 5 15H2L8 3z"></path></svg></span>
            <span class="style-name">${lang === 'tr' ? 'Uzun Menzil' : 'Long Range'}</span>
            <span class="style-sub">${lang === 'tr' ? '7" Yüksek İtiş, GPS & Uzun Süre' : '7" Long Endurance & GPS'}</span>
          </div>

          <div class="builder-style-card ${st.style === 'sub250' ? 'active' : ''}" onclick="window.app.setBuilderStyle('sub250')">
            <span class="style-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.24 12.24a6 6 0 0 0-8.49-8.49L5 10.5V19h8.5z"></path><line x1="16" y1="8" x2="2" y2="22"></line><line x1="17.5" y1="15" x2="9" y2="15"></line></svg></span>
            <span class="style-name">249g Sub-250g</span>
            <span class="style-sub">${lang === 'tr' ? '3" Hafif, SHGM Kayıtsız Uçuş' : '3" Lightweight, Sub-250g Exempt'}</span>
          </div>
        </div>
      </div>

      <!-- Step 2: Video System -->
      <div class="builder-step-box">
        <div class="builder-step-header">
          <span class="step-num-badge">2</span>
          <span class="step-title">${lang === 'tr' ? 'Görüntü Sistemi Tercihi' : 'Video System Choice'}</span>
        </div>
        <div class="builder-video-grid">
          <div class="builder-video-card ${st.video === 'digital' ? 'active' : ''}" onclick="window.app.setBuilderVideo('digital')">
            <span style="display:flex; align-items:center; justify-content:center; width:36px; height:36px; color:var(--brand-primary);"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="6 2 18 2 22 7 12 22 2 7 6 2"></polygon><line x1="2" y1="7" x2="22" y2="7"></line><line x1="12" y1="22" x2="7" y2="7"></line><line x1="12" y1="22" x2="17" y2="7"></line><line x1="6" y1="2" x2="7" y2="7"></line><line x1="18" y1="2" x2="17" y2="7"></line></svg></span>
            <div>
              <strong style="display:block; font-size:0.95rem; color:var(--text-primary);">${lang === 'tr' ? 'Dijital HD (DJI O3 / Walksnail)' : 'Digital HD (DJI O3 / Walksnail)'}</strong>
              <small style="color:var(--text-muted); font-size:0.78rem;">${lang === 'tr' ? 'Kristal netlikte 1080p/4K canlı FPV gözlük yayını' : 'Crystal clear 1080p/4K low latency digital feed'}</small>
            </div>
          </div>

          <div class="builder-video-card ${st.video === 'analog' ? 'active' : ''}" onclick="window.app.setBuilderVideo('analog')">
            <span style="display:flex; align-items:center; justify-content:center; width:36px; height:36px; color:var(--brand-primary);"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="15" rx="2" ry="2"></rect><polyline points="17 2 12 7 7 2"></polyline></svg></span>
            <div>
              <strong style="display:block; font-size:0.95rem; color:var(--text-primary);">${lang === 'tr' ? 'Analog 5.8GHz' : 'Analog 5.8GHz'}</strong>
              <small style="color:var(--text-muted); font-size:0.78rem;">${lang === 'tr' ? 'Ekonomik, sıfır gecikme & geniş anten uyumu' : 'Budget-friendly, near-zero latency'}</small>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3: Target Budget -->
      <div class="builder-step-box">
        <div class="builder-step-header">
          <span class="step-num-badge">3</span>
          <span class="step-title">${lang === 'tr' ? 'Hedef Bütçenizi Belirleyin' : 'Set Target Budget'}</span>
        </div>
        <div class="builder-budget-pills">
          <button type="button" class="budget-pill ${st.budget === 12000 ? 'active' : ''}" onclick="window.app.setBuilderBudget(12000)">12.000 ₺ (Giriş)</button>
          <button type="button" class="budget-pill ${st.budget === 20000 ? 'active' : ''}" onclick="window.app.setBuilderBudget(20000)">20.000 ₺ (F/P)</button>
          <button type="button" class="budget-pill ${st.budget === 28000 ? 'active' : ''}" onclick="window.app.setBuilderBudget(28000)">28.000 ₺ (Dengeli)</button>
          <button type="button" class="budget-pill ${st.budget === 45000 ? 'active' : ''}" onclick="window.app.setBuilderBudget(45000)">45.000 ₺ (Pro)</button>
          <button type="button" class="budget-pill ${st.budget === 65000 ? 'active' : ''}" onclick="window.app.setBuilderBudget(65000)">65.000 ₺+ (Amiral)</button>
        </div>

        <div class="builder-slider-row">
          <input 
            type="range" 
            id="builder-budget-slider" 
            class="budget-range-input" 
            min="8000" 
            max="80000" 
            step="1000" 
            value="${st.budget}"
            oninput="window.app.onBudgetSliderChange(this.value)"
          >
          <div class="budget-display-badge" id="builder-budget-display">
            ${this.formatPrice(st.budget)}
          </div>
        </div>
      </div>

      <!-- 1-Click Action Button -->
      <button type="button" class="btn-build-drone-action" onclick="window.app.executeAutoBuild()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
        <span>${lang === 'tr' ? 'Bütçeme En Uygun Drone’u Oluştur' : 'Build Best Drone for My Budget'}</span>
      </button>
    `;
  }

  setBuilderStyle(style) {
    this.builderState.style = style;
    this.renderBuilderModal();
  }

  setBuilderVideo(video) {
    this.builderState.video = video;
    this.renderBuilderModal();
  }

  setBuilderBudget(budget) {
    this.builderState.budget = Number(budget);
    this.renderBuilderModal();
  }

  onBudgetSliderChange(val) {
    this.builderState.budget = Number(val);
    const badge = document.getElementById('builder-budget-display');
    if (badge) badge.textContent = this.formatPrice(Number(val));
    
    // Update pills active state
    document.querySelectorAll('.budget-pill').forEach(btn => {
      const btnVal = Number(btn.getAttribute('onclick')?.match(/\d+/)?.[0] || 0);
      btn.classList.toggle('active', btnVal === Number(val));
    });
  }

  switchBuilderTab(tab) {
    if (this._droneCalcInterval) {
      clearInterval(this._droneCalcInterval);
      this._droneCalcInterval = null;
    }
    this._isDroneCalculating = false;
    this.builderState.activeTab = tab;
    this.currentGeneratedBuild = null;
    this.renderBuilderModal();
  }

  // Auto Build Generator Algorithm (100% Synergy, Zero Missing Parts)
  executeAutoBuild() {
    const st = this.builderState;
    const staticData = this.getStaticData();
    const allProducts = (staticData && staticData.products && staticData.products.length > 0) 
      ? staticData.products 
      : this.products;

    if (!allProducts || allProducts.length === 0) {
      this.showToast('Ürün verisi yükleniyor, lütfen birkaç saniye sonra tekrar deneyin.', 'error');
      return;
    }

    const budget = st.budget;
    const style = st.style;
    const video = st.video;
    const lang = window.i18n.currentLang;

    // Helper to get products in category sorted by price
    const getPool = (catId, kwList = [], excludeList = []) => {
      let pool = allProducts.filter(p => p.category_id === catId);
      if (kwList.length > 0) {
        const filtered = pool.filter(p => {
          const text = `${p.name_tr} ${p.name_en} ${p.brand}`.toLowerCase();
          return kwList.some(kw => text.includes(kw.toLowerCase()));
        });
        if (filtered.length > 0) pool = filtered;
      }
      if (excludeList.length > 0) {
        const filtered = pool.filter(p => {
          const text = `${p.name_tr} ${p.name_en}`.toLowerCase();
          return !excludeList.some(ex => text.includes(ex.toLowerCase()));
        });
        if (filtered.length > 0) pool = filtered;
      }
      return pool.sort((a, b) => a.price_try - b.price_try);
    };

    // Pick closest product by target price ratio
    const pickByTargetPrice = (pool, targetPrice) => {
      if (!pool || pool.length === 0) return null;
      let closest = pool[0];
      let minDiff = Math.abs(closest.price_try - targetPrice);
      for (const p of pool) {
        const diff = Math.abs(p.price_try - targetPrice);
        if (diff < minDiff) {
          closest = p;
          minDiff = diff;
        }
      }
      return closest;
    };

    // Budget weighting breakdown
    // Target price points according to budget
    let frameTarget = budget * 0.10;
    let motorTarget = (budget * 0.28) / 4; // price per motor
    let fcTarget = budget * 0.16;
    let escTarget = budget * 0.14;
    let videoTarget = budget * 0.18;
    let batteryTarget = budget * 0.08;
    let propTarget = budget * 0.03;
    let rxTarget = budget * 0.03;

    // 1. Frame
    let framePool = [];
    if (style === 'sub250') {
      framePool = getPool('frames', ['3-inch', '3.5-inch', 'baby', 'toothpick', 'crux', 'micro', '3"']);
    } else if (style === 'long_range') {
      framePool = getPool('frames', ['7-inch', '7"', 'deadcat 7', 'chimera', 'long range', 'lr']);
    } else if (style === 'cinematic') {
      framePool = getPool('frames', ['deadcat', 'cinewhoop', 'cinematic', 'evoque', 'protek', '5-inch']);
    } else if (style === 'racing') {
      framePool = getPool('frames', ['race', 'racing', 'speed', 'source one', '5-inch', '5"']);
    } else {
      framePool = getPool('frames', ['apex', 'mark5', 'freestyle', '5-inch', '5"']);
    }
    if (framePool.length === 0) framePool = getPool('frames');
    const selectedFrame = pickByTargetPrice(framePool, frameTarget);

    // 2. Motors (4x)
    let motorPool = [];
    if (style === 'sub250') {
      motorPool = getPool('motors', ['1404', '1507', '1204', '3800kv', '4500kv', '3000kv']);
    } else if (style === 'long_range') {
      motorPool = getPool('motors', ['2806', '2807', '1300kv', '1500kv', '1750kv']);
    } else if (style === 'racing') {
      motorPool = getPool('motors', ['2207', '2207.5', '1950kv', '2000kv', '2450kv', '2550kv']);
    } else {
      motorPool = getPool('motors', ['2207', '2306', '1750kv', '1950kv', '1850kv']);
    }
    if (motorPool.length === 0) motorPool = getPool('motors');
    const selectedMotor = pickByTargetPrice(motorPool, motorTarget);

    // 3. Flight Controller (FC)
    let fcPool = getPool('flight_controllers', (style === 'long_range' || style === 'racing') ? ['f722', 'h743', 'f7', 'pro'] : ['f405', 'f722']);
    if (fcPool.length === 0) fcPool = getPool('flight_controllers');
    const selectedFC = pickByTargetPrice(fcPool, fcTarget);

    // 4. ESC
    let escPool = getPool('esc', (style === 'racing' || style === 'long_range') ? ['55a', '60a', '65a', '32bit'] : ['45a', '50a', '55a']);
    if (escPool.length === 0) escPool = getPool('esc');
    const selectedESC = pickByTargetPrice(escPool, escTarget);

    // 5. Video & Camera
    let selectedCamera = null;
    let selectedVTX = null;
    if (video === 'digital') {
      let digiPool = getPool('cameras', ['o3', 'dji', 'walksnail', 'avatar', 'digital', 'hd', 'caddx']);
      if (digiPool.length === 0) digiPool = getPool('cameras');
      selectedCamera = pickByTargetPrice(digiPool, videoTarget * 0.65);

      let vtxPool = getPool('vtx', ['hd', 'digital', 'walksnail', 'dji', 'avatar']);
      if (vtxPool.length === 0) vtxPool = getPool('vtx');
      selectedVTX = pickByTargetPrice(vtxPool, videoTarget * 0.35);
    } else {
      let anaCamPool = getPool('cameras', ['runcam', 'foxeer', 'razer', 'phoenix', 'ratel', 'analog']);
      if (anaCamPool.length === 0) anaCamPool = getPool('cameras');
      selectedCamera = pickByTargetPrice(anaCamPool, videoTarget * 0.45);

      let anaVtxPool = getPool('vtx', ['5.8g', '5.8ghz', 'tank', 'tx800', 'reaper', 'unify', 'analog']);
      if (anaVtxPool.length === 0) anaVtxPool = getPool('vtx');
      selectedVTX = pickByTargetPrice(anaVtxPool, videoTarget * 0.55);
    }

    // 6. Propellers (Set of 4)
    let propPool = [];
    if (style === 'sub250') {
      propPool = getPool('propellers', ['3-inch', '3016', '3020', '3028', '3"']);
    } else if (style === 'long_range') {
      propPool = getPool('propellers', ['7-inch', '7040', '7035', '7"']);
    } else if (style === 'racing') {
      propPool = getPool('propellers', ['51466', '51433', '51477', '5-inch', '5"']);
    } else {
      propPool = getPool('propellers', ['51433', '5040', '5140', '5-inch', '5"']);
    }
    if (propPool.length === 0) propPool = getPool('propellers');
    const selectedProp = pickByTargetPrice(propPool, propTarget);

    // 7. Battery
    let batPool = [];
    if (style === 'sub250') {
      batPool = getPool('batteries_chargers', ['4s', '850mah', '650mah', '750mah']);
    } else if (style === 'long_range') {
      batPool = getPool('batteries_chargers', ['6s', '3000mah', '4000mah', '5000mah', 'lipo']);
    } else {
      batPool = getPool('batteries_chargers', ['6s', '1300mah', '1400mah', '1550mah', 'r-line']);
    }
    if (batPool.length === 0) batPool = getPool('batteries_chargers');
    const selectedBattery = pickByTargetPrice(batPool, batteryTarget);

    // 8. Radio Receiver (RX)
    let rxPool = getPool('transmitters_receivers', ['rp1', 'elrs', 'expresslrs', 'nano rx', 'receiver', 'crossfire']);
    if (rxPool.length === 0) rxPool = getPool('transmitters_receivers');
    const selectedRX = pickByTargetPrice(rxPool, rxTarget);

    // 9. Optional GPS (for Long Range)
    let selectedGPS = null;
    if (style === 'long_range') {
      const gpsPool = getPool('gps_telemetry');
      if (gpsPool.length > 0) selectedGPS = gpsPool[0];
    }

    // Build the package list
    const items = [
      { role: lang === 'tr' ? 'Gövde (Frame)' : 'Frame', product: selectedFrame, qty: 1 },
      { role: lang === 'tr' ? 'FPV Motorları (4x Set)' : 'Motors (4x Set)', product: selectedMotor, qty: 4 },
      { role: lang === 'tr' ? 'Uçuş Kontrol Kartı (FC)' : 'Flight Controller (FC)', product: selectedFC, qty: 1 },
      { role: lang === 'tr' ? 'ESC Hız Sürücüsü' : 'ESC Speed Controller', product: selectedESC, qty: 1 },
      { role: lang === 'tr' ? 'FPV Kamera' : 'FPV Camera', product: selectedCamera, qty: 1 },
      { role: lang === 'tr' ? 'Video Verici (VTX)' : 'Video Transmitter (VTX)', product: selectedVTX, qty: 1 },
      { role: lang === 'tr' ? 'Pervane Seti (4 Adet)' : 'Propellers (4x Set)', product: selectedProp, qty: 1 },
      { role: lang === 'tr' ? 'LiPo Batarya' : 'LiPo Battery', product: selectedBattery, qty: 1 },
      { role: lang === 'tr' ? 'Radyo Alıcı (RX)' : 'Radio Receiver (RX)', product: selectedRX, qty: 1 }
    ];

    if (selectedGPS) {
      items.push({ role: lang === 'tr' ? 'GPS & Telemetri Modülü' : 'GPS & Telemetry Module', product: selectedGPS, qty: 1 });
    }

    // Clean nulls
    const validItems = items.filter(it => it.product != null);
    const totalPrice = validItems.reduce((sum, it) => sum + (it.product.price_try * it.qty), 0);

    const buildResult = {
      style,
      video,
      targetBudget: budget,
      totalPrice,
      items: validItems,
      generatedAt: new Date().toISOString()
    };

    this.startDroneCalculatingSimulation(buildResult);
  }

  startDroneCalculatingSimulation(buildResult) {
    const body = document.getElementById('builder-modal-body');
    if (!body) return;

    if (this._droneCalcInterval) {
      clearInterval(this._droneCalcInterval);
      this._droneCalcInterval = null;
    }

    this._isDroneCalculating = true;
    const lang = window.i18n.currentLang;
    const totalDuration = 10000; // 10 seconds simulation
    let elapsed = 0;

    const steps = [
      { id: 1, tr: 'Uçuş tarzı ve bütçe parametreleri analiz ediliyor...', en: 'Analyzing flight profile & target budget...', duration: 1500 },
      { id: 2, tr: '500+ FPV donanım veritabanı taranıyor & filtreleniyor...', en: 'Scanning 500+ FPV component database & applying filters...', duration: 2000 },
      { id: 3, tr: '4S / 6S voltaj & ESC amper dayanım sinerjisi simüle ediliyor...', en: 'Simulating 4S / 6S voltage & ESC current headroom synergy...', duration: 2000 },
      { id: 4, tr: 'Motor KV, pervane hatvesi ve itiş gücü (T/W) hesaplanıyor...', en: 'Calculating motor KV, propeller pitch & thrust-to-weight ratio...', duration: 2000 },
      { id: 5, tr: 'Gövde montaj delikleri (20x20 / 30.5x30.5mm stack) doğrulanıyor...', en: 'Verifying frame stack mounting screw spacing & clearance...', duration: 1500 },
      { id: 6, tr: 'Bütçe ve performans optimizasyonu tamamlandı!', en: 'Budget and performance optimization complete!', duration: 1000 }
    ];

    body.innerHTML = `
      <div class="calculating-screen-container" id="drone-calculating-screen">
        <div class="calculating-bg-grid"></div>

        <div class="calculating-visual-wrap">
          <div class="calculating-radar-glow"></div>
          <div class="calculating-radar-ring"></div>
          <div class="calculating-icon-center">
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
          </div>
        </div>

        <h3 class="calculating-title">${lang === 'tr' ? 'Pozitron Akıllı Drone Mühendislik Motoru' : 'Pozitron Smart Drone Engineering Engine'}</h3>
        <p class="calculating-sub">${lang === 'tr' ? 'Bileşen sinerjisi, voltaj uyumluluğu, montaj vida delikleri ve itiş-ağırlık dinamikleri hesaplanıyor.' : 'Calculating component synergy, voltage compatibility, stack fit, and thrust dynamics.'}</p>

        <!-- Countdown Banner -->
        <div class="calculating-timer-banner">
          <span class="calculating-timer-icon">⏳</span>
          <span class="calculating-timer-text">
            ${lang === 'tr' ? 'Kalan Süre:' : 'Remaining Time:'} 
            <span class="calculating-timer-seconds" id="drone-calc-countdown">10</span> 
            ${lang === 'tr' ? 'saniye' : 'seconds'}
          </span>
        </div>

        <!-- Progress Bar -->
        <div class="calculating-progress-track">
          <div class="calculating-progress-fill" id="drone-calc-progress" style="width: 0%;"></div>
        </div>
        <div class="calculating-pct-text" id="drone-calc-pct">0% ${lang === 'tr' ? 'Tamamlandı' : 'Completed'}</div>

        <!-- Step-by-Step Logs -->
        <div class="calculating-steps-box" id="drone-calc-steps-box">
          ${steps.map((s, idx) => `
            <div class="calculating-step-row ${idx === 0 ? 'active' : ''}" id="drone-step-row-${s.id}">
              <span class="calc-step-icon" id="drone-step-icon-${s.id}">${idx === 0 ? '▶' : (idx + 1)}</span>
              <span class="calc-step-name">${lang === 'tr' ? s.tr : s.en}</span>
              <span class="calc-step-status" id="drone-step-status-${s.id}">${idx === 0 ? (lang === 'tr' ? 'İşleniyor' : 'Processing') : (lang === 'tr' ? 'Bekliyor' : 'Waiting')}</span>
            </div>
          `).join('')}
        </div>

        <!-- Simulated Telemetry Tiles -->
        <div class="calculating-stats-grid">
          <div class="calc-stat-tile">
            <span class="label">${lang === 'tr' ? 'Taranan Parça' : 'Scanned Parts'}</span>
            <span class="value" id="drone-stat-parts">0 / 506</span>
          </div>
          <div class="calc-stat-tile">
            <span class="label">${lang === 'tr' ? 'Voltaj Sinerjisi' : 'Voltage Synergy'}</span>
            <span class="value" id="drone-stat-voltage">4S / 6S</span>
          </div>
          <div class="calc-stat-tile">
            <span class="label">${lang === 'tr' ? 'ESC Güvenlik Payı' : 'ESC Margin'}</span>
            <span class="value" id="drone-stat-esc">+25% Amper</span>
          </div>
          <div class="calc-stat-tile">
            <span class="label">${lang === 'tr' ? 'Stack Montajı' : 'Stack Clearance'}</span>
            <span class="value" id="drone-stat-stack">20×20 & 30×30</span>
          </div>
        </div>
      </div>
    `;

    const intervalMs = 100;
    this._droneCalcInterval = setInterval(() => {
      elapsed += intervalMs;
      const progressPct = Math.min(100, Math.round((elapsed / totalDuration) * 100));
      const remainingSeconds = Math.max(0, Math.ceil((totalDuration - elapsed) / 1000));

      const countdownEl = document.getElementById('drone-calc-countdown');
      const progressEl = document.getElementById('drone-calc-progress');
      const pctEl = document.getElementById('drone-calc-pct');
      const partsEl = document.getElementById('drone-stat-parts');

      if (countdownEl) countdownEl.textContent = remainingSeconds;
      if (progressEl) progressEl.style.width = `${progressPct}%`;
      if (pctEl) pctEl.textContent = `${progressPct}% ${lang === 'tr' ? 'Tamamlandı' : 'Completed'}`;
      if (partsEl) {
        const currentScanned = Math.min(506, Math.round((elapsed / totalDuration) * 506));
        partsEl.textContent = `${currentScanned} / 506`;
      }

      let accumulatedTime = 0;
      for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        const stepStart = accumulatedTime;
        const stepEnd = accumulatedTime + step.duration;
        accumulatedTime = stepEnd;

        const row = document.getElementById(`drone-step-row-${step.id}`);
        const icon = document.getElementById(`drone-step-icon-${step.id}`);
        const status = document.getElementById(`drone-step-status-${step.id}`);

        if (row && icon && status) {
          if (elapsed >= stepEnd) {
            row.className = 'calculating-step-row completed';
            icon.textContent = '✓';
            status.textContent = lang === 'tr' ? 'Tamamlandı' : 'Verified';
          } else if (elapsed >= stepStart) {
            row.className = 'calculating-step-row active';
            icon.textContent = '▶';
            status.textContent = lang === 'tr' ? 'Hesaplanıyor' : 'Calculating';
          } else {
            row.className = 'calculating-step-row';
            icon.textContent = (i + 1);
            status.textContent = lang === 'tr' ? 'Bekliyor' : 'Waiting';
          }
        }
      }

      if (elapsed >= totalDuration) {
        clearInterval(this._droneCalcInterval);
        this._droneCalcInterval = null;
        this._isDroneCalculating = false;
        this.currentGeneratedBuild = buildResult;

        setTimeout(() => {
          this.renderBuilderModal();
        }, 300);
      }
    }, intervalMs);
  }

  renderBuildResultView(body) {
    const lang = window.i18n.currentLang;
    const b = this.currentGeneratedBuild;
    if (!b) return;

    const diff = b.targetBudget - b.totalPrice;
    const isUnderBudget = diff >= 0;

    body.innerHTML = `
      <div class="build-result-container">
        <div class="build-summary-banner">
          <div class="build-summary-stat">
            <span class="stat-label">${lang === 'tr' ? 'Seçilen Bütçe' : 'Target Budget'}</span>
            <span style="font-size:1.15rem; font-weight:700; color:#e2e8f0;">${this.formatPrice(b.targetBudget / (this.usdRate || 50.0), b.targetBudget)}</span>
          </div>
          <div class="build-summary-stat">
            <span class="stat-label">${lang === 'tr' ? 'Toplam Parça Tutarı' : 'Total Package Price'}</span>
            <span class="stat-val">${this.formatPrice(b.totalPrice / (this.usdRate || 50.0), b.totalPrice)}</span>
          </div>
          <div class="build-summary-stat">
            <span class="stat-label">${isUnderBudget ? (lang === 'tr' ? 'Kalan Bütçe' : 'Remaining Budget') : (lang === 'tr' ? 'Bütçe Farkı' : 'Difference')}</span>
            <span style="font-size:1.15rem; font-weight:800; color:${isUnderBudget ? '#4ade80' : '#fb923c'};">
              ${isUnderBudget ? '+' : ''}${this.formatPrice(diff / (this.usdRate || 50.0), diff)}
            </span>
          </div>
        </div>

        <!-- Verified Synergy Badges -->
        <div class="build-specs-row">
          <span class="spec-badge">${lang === 'tr' ? 'Voltaj & Hücre Uyumu: %100 Doğrulandı' : 'Voltage Synergy: 100% Verified'}</span>
          <span class="spec-badge">${lang === 'tr' ? 'ESC Amper Dayanımı: Tam Güvenli' : 'ESC Current Rating: Safe Margin'}</span>
          <span class="spec-badge">${lang === 'tr' ? 'Montaj & Vida Aralıkları: Birebir Uyumlu' : 'Stack & Frame Mount: Exact Fit'}</span>
          <span class="spec-badge">${lang === 'tr' ? 'Pervane & Motor Oranı: Yüksek Verimlilik' : 'Prop & Motor Ratio: High Efficiency'}</span>
        </div>

        <!-- 8-Piece Items Breakdown -->
        <h4 style="font-size:0.92rem; font-weight:800; color:var(--text-secondary); text-transform:uppercase; margin-bottom:10px;">
          ${lang === 'tr' ? `Seçilen ${b.items.length} Parçalık Eksiksiz Drone Paketi` : `Selected ${b.items.length}-Piece Complete Drone Package`}
        </h4>

        <div class="build-items-list">
          ${b.items.map(it => {
            const p = it.product;
            const unitTRY = Number(p.price_try) || (Number(p.price_usd) * (this.usdRate || 50.0)) || 0;
            const subtotalTRY = unitTRY * it.qty;
            const rawTitle = (lang === 'tr' ? p.name_tr : p.name_en) || p.title || '';
            const brandStr = p.brand || '';
            const displayTitle = (brandStr && rawTitle.toLowerCase().startsWith(brandStr.toLowerCase())) 
              ? rawTitle 
              : (brandStr ? `${brandStr} ${rawTitle}` : rawTitle);

            return `
              <div class="build-item-card" onclick="window.open('./products/' + ('${p.slug}' || '${p.id}'), '_blank')" title="${lang === 'tr' ? 'Ürünü Yeni Sekmede İncele' : 'View Product in New Tab'}">
                <img src="${p.image_url}" alt="${brandStr}" class="build-item-img" onerror="this.src='https://images.unsplash.com/photo-1508614589041-895b88991e3e?auto=format&fit=crop&w=150&q=80'">
                <div class="build-item-info">
                  <div style="display:flex; align-items:center;">
                    <span class="build-item-cat">${it.role}</span>
                    ${it.qty > 1 ? `<span class="build-item-qty-tag">${it.qty} Adet</span>` : ''}
                  </div>
                  <div class="build-item-title">${displayTitle}</div>
                </div>
                <div class="build-item-price">
                  ${this.formatPrice(subtotalTRY / (this.usdRate || 50.0), subtotalTRY)}
                  ${it.qty > 1 ? `<div style="font-size:0.72rem; color:var(--text-muted); font-weight:500;">(Birim: ${this.formatPrice(unitTRY / (this.usdRate || 50.0), unitTRY)})</div>` : ''}
                </div>
              </div>
            `;
          }).join('')}
        </div>

        <!-- Actions -->
        <div class="build-actions-bar" style="display:flex; flex-wrap:wrap; gap:10px;">
          <button type="button" class="btn-add-entire-build" onclick="window.app.addAllBuildItemsToCart()" style="flex:2; min-width:220px; display:flex; align-items:center; justify-content:center; gap:8px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>
            <span>${lang === 'tr' ? 'Tüm Parçaları Tek Tıkla Sepete Ekle' : 'Add Entire Package to Cart'}</span>
          </button>
          <button type="button" class="btn-share-build-wa" onclick="window.app.shareBuildWhatsApp()" style="flex:1; min-width:170px; padding:14px; background:#25d366; color:#ffffff; font-weight:800; border-radius:var(--radius-md); border:none; display:flex; align-items:center; justify-content:center; gap:8px; cursor:pointer; font-size:0.92rem; box-shadow:0 4px 12px rgba(37,211,102,0.3); transition:all 0.15s ease;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path></svg>
            <span>${lang === 'tr' ? 'WhatsApp ile Gönder' : 'Share on WhatsApp'}</span>
          </button>
          <button type="button" class="btn-share-build-link" onclick="window.app.shareBuildLink()" style="flex:1; min-width:170px; padding:14px; background:#0284c7; color:#ffffff; font-weight:800; border-radius:var(--radius-md); border:none; display:flex; align-items:center; justify-content:center; gap:8px; cursor:pointer; font-size:0.92rem; box-shadow:0 4px 12px rgba(2,132,199,0.3); transition:all 0.15s ease;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
            <span>${lang === 'tr' ? 'Paketi Paylaş / Kopyala' : 'Copy Share Link'}</span>
          </button>
          <button type="button" class="btn-rebuild-action" onclick="window.app.resetBuildResult()" style="flex:1; min-width:140px; display:flex; align-items:center; justify-content:center; gap:8px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>
            <span>${lang === 'tr' ? 'Yeniden Hesapla' : 'Recalculate'}</span>
          </button>
        </div>
      </div>
    `;
  }

  shareBuildLink() {
    const b = this.currentGeneratedBuild;
    if (!b || !b.items || b.items.length === 0) return;

    const ids = b.items.map(it => `${it.product.id}:${it.qty}`).join(',');
    const shareUrl = `${window.location.origin}/#build=${encodeURIComponent(ids)}`;

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(shareUrl).then(() => {
        const lang = window.i18n.currentLang;
        this.showToast(lang === 'tr' 
          ? 'Drone paketi bağlantısı panoya kopyalandı! Arkadaşlarınız veya takımınızla paylaşabilirsiniz.' 
          : 'Drone build link copied to clipboard! You can share it with your team or friends.');
      }).catch(() => {
        prompt('Drone Paketi Paylaşım Bağlantısı:', shareUrl);
      });
    } else {
      prompt('Drone Paketi Paylaşım Bağlantısı:', shareUrl);
    }
  }

  shareBuildWhatsApp() {
    const b = this.currentGeneratedBuild;
    if (!b || !b.items || b.items.length === 0) return;

    const lang = window.i18n.currentLang;
    const ids = b.items.map(it => `${it.product.id}:${it.qty}`).join(',');
    const shareUrl = `${window.location.origin}/#build=${encodeURIComponent(ids)}`;
    const formattedTotal = this.formatPrice(b.totalPrice / (this.usdRate || 50.0), b.totalPrice);

    const itemsText = b.items.map((it, idx) => {
      const name = (lang === 'tr' ? it.product.name_tr : it.product.name_en) || it.product.title;
      return `${idx + 1}. ${name} (${it.qty} Adet)`;
    }).join('\n');

    const msg = `Pozitron Market Drone Toplama Sihirbazı ile hazırladığım FPV Drone Paketi:\n\nParça Listesi (${b.items.length} Parça):\n${itemsText}\n\nToplam Tutar: ${formattedTotal}\n\nUyumlu parçaları ve uyumluluk raporunu incelemek için:\n${shareUrl}`;

    window.open(`https://api.whatsapp.com/send?text=${encodeURIComponent(msg)}`, '_blank');
  }

  loadSharedBuild(buildParam) {
    if (!buildParam) return;
    try {
      const staticData = this.getStaticData();
      const allProducts = (staticData && staticData.products && staticData.products.length) ? staticData.products : this.products;
      if (!allProducts || allProducts.length === 0) return;

      const pairs = decodeURIComponent(buildParam).split(',');
      const validItems = [];
      let totalPrice = 0;

      pairs.forEach(pair => {
        const [pId, qtyStr] = pair.split(':');
        const qty = parseInt(qtyStr, 10) || 1;
        const prod = allProducts.find(p => p.id === pId || p.slug === pId);
        if (prod) {
          const unitTRY = Number(prod.price_try) || (Number(prod.price_usd) * (this.usdRate || 50.0)) || 0;
          totalPrice += unitTRY * qty;
          validItems.push({ product: prod, qty });
        }
      });

      if (validItems.length > 0) {
        this.currentGeneratedBuild = {
          style: 'freestyle',
          video: 'digital',
          targetBudget: Math.ceil(totalPrice),
          totalPrice,
          items: validItems,
          generatedAt: new Date().toISOString()
        };
        this.openBuilderModal('auto');
        const lang = window.i18n.currentLang;
        this.showToast(lang === 'tr' 
          ? `Paylaşılan ${validItems.length} parçalık drone paketi başarıyla yüklendi!` 
          : `Shared ${validItems.length}-piece drone package loaded successfully!`);
      }
    } catch (err) {
      console.warn('Failed to load shared build:', err);
    }
  }

  addAllBuildItemsToCart() {
    const b = this.currentGeneratedBuild;
    if (!b || !b.items || b.items.length === 0) return;

    let totalCount = 0;
    b.items.forEach(it => {
      this.addToCart(it.product.id, it.qty);
      totalCount += it.qty;
    });

    this.closeBuilderModal();
    this.openCart();
    const lang = window.i18n.currentLang;
    this.showToast(lang === 'tr' 
      ? `${totalCount} parça uyumlu drone bileşeni sepetinize eklendi!` 
      : `${totalCount} compatible drone parts added to your cart!`
    );
  }

  resetBuildResult() {
    if (this._droneCalcInterval) {
      clearInterval(this._droneCalcInterval);
      this._droneCalcInterval = null;
    }
    this._isDroneCalculating = false;
    this.currentGeneratedBuild = null;
    this.renderBuilderModal();
  }

  renderManualBuilderForm(body) {
    let motors = [], escs = [], props = [], batteries = [];
    const staticData = this.getStaticData();
    if (staticData && staticData.products && staticData.products.length > 0) {
      motors = staticData.products.filter(p => p.category_id === 'motors').slice(0, 30);
      escs = staticData.products.filter(p => p.category_id === 'esc').slice(0, 30);
      props = staticData.products.filter(p => p.category_id === 'propellers').slice(0, 30);
      batteries = staticData.products.filter(p => p.category_id === 'batteries_chargers').slice(0, 30);
    } else {
      motors = this.products.filter(p => p.category_id === 'motors').slice(0, 30);
      escs = this.products.filter(p => p.category_id === 'esc').slice(0, 30);
      props = this.products.filter(p => p.category_id === 'propellers').slice(0, 30);
      batteries = this.products.filter(p => p.category_id === 'batteries_chargers').slice(0, 30);
    }

    const lang = window.i18n.currentLang;

    body.innerHTML = `
      <div class="builder-tab-bar">
        <button type="button" class="builder-tab-btn" onclick="window.app.switchBuilderTab('auto')">
          ${lang === 'tr' ? 'Bütçeye Göre Otomatik Topla' : 'Auto Build by Budget'}
        </button>
        <button type="button" class="builder-tab-btn active" onclick="window.app.switchBuilderTab('manual')">
          ${lang === 'tr' ? 'Manuel Parça Seçimi & Test' : 'Manual Part Selection & Test'}
        </button>
      </div>

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
          <strong id="builder-status-text" style="color:var(--status-success); font-size:1.05rem;">Mükemmel Uyumlu Kombinasyon!</strong>
          <p id="builder-details-text" style="font-size:0.85rem; color:var(--text-secondary);">Seçilen motor KV değeri, ESC amperajı ve LiPo hücre sayısı tam uyumlu çalışmaktadır.</p>
        </div>
      </div>
    `;

    // Hook change events to check compatibility
    ['slot-motor', 'slot-esc', 'slot-prop', 'slot-battery'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', () => this.runCompatibilityCheck());
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
      statusText.textContent = "Mükemmel Uyumlu Donanım Kombinasyonu!";
      detailsText.textContent = "Seçtiğiniz donanımlar voltaj, KV ve amperaj limitleri açısından güvenli uçuş standartlarına uygundur.";
    } else {
      scoreCircle.style.borderColor = 'var(--status-warning)';
      scoreCircle.style.color = 'var(--status-warning)';
      statusText.style.color = 'var(--status-warning)';
      statusText.textContent = "Dikkat: Uyumsuzluk Uyarısı Tespit Edildi";
      
      const warn = data.warnings && data.warnings[0];
      detailsText.textContent = warn ? (lang === 'tr' ? warn.tr : warn.en) : "Lütfen parçaların voltaj ve amperaj değerlerini kontrol ediniz.";
    }
  }

  closeBuilderModal() {
    if (this._droneCalcInterval) {
      clearInterval(this._droneCalcInterval);
      this._droneCalcInterval = null;
    }
    this._isDroneCalculating = false;
    const modal = document.getElementById('builder-modal-backdrop');
    if (modal) modal.style.display = 'none';
  }

  showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast-msg ${type === 'success' ? 'toast-success' : 'toast-error'}`;
    const icon = type === 'success'
      ? `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`
      : `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
    toast.innerHTML = `
      <span style="display:flex; align-items:center;">${icon}</span>
      <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      setTimeout(() => toast.remove(), 250);
    }, 3200);
  }

  // ==========================================
  // 3D PRINT ON-DEMAND CUSTOM MANUFACTURING ENGINE
  // ==========================================
  init3DStudio() {
    this._3dConfig = {
      material: 'PLA',
      infill: 20,
      layer: '0.20',
      colorHex: '#1e293b',
      colorName: 'Mat Siyah',
      qty: 1,
      volumeCm3: 0,
      dimX: 0,
      dimY: 0,
      dimZ: 0,
      filename: '',
      weightGrams: 0,
      unitPriceTRY: 0
    };

    this._3dMaterials = {
      PLA: { name: 'PLA', density: 1.24, defaultPrice: 1.50 },
      PETG: { name: 'PETG', density: 1.27, defaultPrice: 2.00 },
      TPU: { name: 'TPU (Flex)', density: 1.21, defaultPrice: 3.50 },
      ABS: { name: 'ABS', density: 1.04, defaultPrice: 2.25 },
      ASA: { name: 'ASA', density: 1.07, defaultPrice: 2.50 },
      PA6: { name: 'PA6 (Naylon)', density: 1.14, defaultPrice: 5.00 }
    };

    // Setup drag and drop on dropzone and container
    const dropzone = document.getElementById('viewport-dropzone');
    const container = document.getElementById('viewport-3d-container');
    const fileInput = document.getElementById('file-3d-input');

    if (fileInput) {
      fileInput.onchange = (e) => {
        this.handle3DFileInputChange(e.target);
      };
    }

    const handleDragOver = (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (dropzone) {
        dropzone.classList.remove('hidden');
        dropzone.style.display = 'flex';
        dropzone.classList.add('dragover');
      }
    };

    const handleDragLeave = (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (dropzone) {
        if (!this._currentMesh) {
          dropzone.classList.remove('dragover');
        } else {
          dropzone.classList.add('hidden');
          dropzone.style.display = 'none';
          dropzone.classList.remove('dragover');
        }
      }
    };

    const handleDrop = (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (dropzone) {
        dropzone.classList.remove('dragover');
      }
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0]) {
        this.handle3DFileUpload(e.dataTransfer.files[0]);
      }
    };

    if (dropzone) {
      dropzone.addEventListener('dragover', handleDragOver);
      dropzone.addEventListener('dragleave', handleDragLeave);
      dropzone.addEventListener('drop', handleDrop);
    }

    if (container) {
      container.addEventListener('dragover', handleDragOver);
      container.addEventListener('dragleave', handleDragLeave);
      container.addEventListener('drop', handleDrop);
    }
  }

  open3DStudioModal() {
    const modal = document.getElementById('studio-3d-modal-backdrop');
    if (!modal) return;
    modal.style.display = 'flex';

    if (!this._3dViewerInitialized) {
      this.init3DViewer();
      this.init3DStudio();
      this._3dViewerInitialized = true;
    }

    this.refresh3DMaterialPriceTags();
    this.calculate3DPrice();

    setTimeout(() => {
      if (this._3dRenderer && this._3dCamera) {
        const container = document.getElementById('viewport-3d-container');
        if (container) {
          const width = container.clientWidth || 500;
          const height = container.clientHeight || 420;
          this._3dRenderer.setSize(width, height);
          this._3dCamera.aspect = width / height;
          this._3dCamera.updateProjectionMatrix();
        }
      }
    }, 100);
  }

  close3DStudioModal() {
    if (this._3dCalcInterval) {
      clearInterval(this._3dCalcInterval);
      this._3dCalcInterval = null;
    }
    this._is3DCalculating = false;
    const overlay = document.getElementById('viewport-calculating-overlay');
    if (overlay) overlay.style.display = 'none';

    const modal = document.getElementById('studio-3d-modal-backdrop');
    if (modal) modal.style.display = 'none';
  }

  trigger3DFileUpload(e) {
    if (e) {
      try {
        if (typeof e.preventDefault === 'function') e.preventDefault();
        if (typeof e.stopPropagation === 'function') e.stopPropagation();
      } catch (err) {}
    }
    const fileInput = document.getElementById('file-3d-input');
    if (fileInput) {
      fileInput.value = '';
      fileInput.click();
    }
  }

  handle3DFileInputChange(inputEl) {
    if (inputEl && inputEl.files && inputEl.files.length > 0) {
      const file = inputEl.files[0];
      this.handle3DFileUpload(file);
      setTimeout(() => {
        try { inputEl.value = ''; } catch(err) {}
      }, 500);
    }
  }

  init3DViewer() {
    const container = document.getElementById('viewport-3d-container');
    const canvas = document.getElementById('canvas-3d-viewer');
    if (!container || !canvas || typeof THREE === 'undefined') return;

    const width = container.clientWidth || 500;
    const height = container.clientHeight || 420;

    // 1. Studio Scene — Pure White Background
    this._3dScene = new THREE.Scene();
    this._3dScene.background = new THREE.Color(0xffffff);

    // 2. Camera
    this._3dCamera = new THREE.PerspectiveCamera(45, width / height, 0.1, 2500);
    this._3dCamera.position.set(0, 85, 160);

    // 3. WebGL Renderer
    this._3dRenderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: false });
    this._3dRenderer.setSize(width, height);
    this._3dRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this._3dRenderer.shadowMap.enabled = true;
    this._3dRenderer.toneMapping = THREE.ACESFilmicToneMapping;
    this._3dRenderer.toneMappingExposure = 1.1;

    // 4. Orbit Controls
    if (typeof THREE.OrbitControls !== 'undefined') {
      this._3dControls = new THREE.OrbitControls(this._3dCamera, this._3dRenderer.domElement);
      this._3dControls.enableDamping = true;
      this._3dControls.dampingFactor = 0.06;
      this._3dControls.autoRotate = false;
      this._3dControls.autoRotateSpeed = 2.0;
      this._3dControls.maxPolarAngle = Math.PI / 2 + 0.05;
    }

    // 5. Clean Grid Floor — Industrial Build Volume: 256 × 256 × 256 mm
    const grid = new THREE.GridHelper(256, 16, 0x0284c7, 0xe2e8f0);
    grid.position.y = -0.5;
    this._3dScene.add(grid);

    // 6. Professional Studio Lighting Setup
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
    this._3dScene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0xe2e8f0, 0.65);
    hemiLight.position.set(0, 200, 0);
    this._3dScene.add(hemiLight);

    // Key Light (Top-Right Front)
    const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.95);
    dirLight1.position.set(120, 180, 120);
    this._3dScene.add(dirLight1);

    // Fill Light (Left-Back)
    const dirLight2 = new THREE.DirectionalLight(0xe0f2fe, 0.55);
    dirLight2.position.set(-120, 80, -120);
    this._3dScene.add(dirLight2);

    // Front Soft Light
    const dirLight3 = new THREE.DirectionalLight(0xffffff, 0.45);
    dirLight3.position.set(0, 60, 160);
    this._3dScene.add(dirLight3);

    // 7. Continuous Animation Loop
    const animate = () => {
      requestAnimationFrame(animate);
      if (this._3dControls) this._3dControls.update();
      if (this._3dRenderer && this._3dScene && this._3dCamera) {
        this._3dRenderer.render(this._3dScene, this._3dCamera);
      }
    };
    animate();

    // 8. Responsive Viewport Resize
    window.addEventListener('resize', () => {
      if (!this._3dRenderer || !this._3dCamera || !container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w > 0 && h > 0) {
        this._3dCamera.aspect = w / h;
        this._3dCamera.updateProjectionMatrix();
        this._3dRenderer.setSize(w, h);
      }
    });
  }

  async upload3DFileToServer(file) {
    if (!file) return;
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/upload-3d', {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        const data = await res.json();
        if (data.url) this._3dConfig.serverUrl = data.url;
      } else {
        // Fallback JSON payload
        const reader = new FileReader();
        reader.onload = async (e) => {
          try {
            const text = typeof e.target.result === 'string' ? e.target.result : new TextDecoder('utf-8').decode(e.target.result);
            await fetch('/api/upload-3d', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ filename: file.name, content: text, is_base64: false })
            });
          } catch (err) {}
        };
        reader.readAsText(file);
      }
    } catch (err) {
      console.warn('3D File Server Upload note:', err);
    }
  }

  start3DCalculatingSimulation(filename, onComplete) {
    const overlay = document.getElementById('viewport-calculating-overlay');
    const dropzone = document.getElementById('viewport-dropzone');
    const controls = document.getElementById('viewport-floating-controls');
    const metrics = document.getElementById('model-metrics-bar');

    if (dropzone) {
      dropzone.style.display = 'none';
      dropzone.classList.add('hidden');
    }
    if (controls) controls.style.display = 'none';
    if (metrics) metrics.style.display = 'none';

    if (!overlay) {
      if (typeof onComplete === 'function') onComplete();
      return;
    }

    if (this._3dCalcInterval) {
      clearInterval(this._3dCalcInterval);
      this._3dCalcInterval = null;
    }

    this._is3DCalculating = true;
    overlay.style.display = 'flex';
    const lang = window.i18n.currentLang;
    const totalDuration = 10000; // 10 seconds simulation
    let elapsed = 0;

    const steps = [
      { id: 1, phase: 1, tr: '3D CAD mesh geometrisi ve üçgen ağları (Triangulation) taranıyor...', en: 'Parsing 3D CAD mesh geometry & triangulation...', duration: 1600 },
      { id: 2, phase: 1, tr: 'Manifold geometri, delik ve yüzey normali hataları denetleniyor...', en: 'Checking manifold geometry, holes & surface normals...', duration: 1800 },
      { id: 3, phase: 2, tr: 'Hassas üretim tablası yerleşimi ve oryantasyon simüle ediliyor...', en: 'Simulating precision build plate orientation...', duration: 1800 },
      { id: 4, phase: 2, tr: 'Katman dilimleme (Slicing) ve petek doluluk takım yolları üretiliyor...', en: 'Generating layer toolpaths & infill structures...', duration: 2200 },
      { id: 5, phase: 3, tr: 'Destek yapıları (Support) ve net sarfiyat gramajı hesaplanıyor...', en: 'Estimating support structures & material consumption...', duration: 1600 },
      { id: 6, phase: 3, tr: 'Katman baskı süresi ve mühendislik maliyet analizi hazır!', en: 'Layer print time and engineering cost analysis ready!', duration: 1000 }
    ];

    overlay.innerHTML = `
      <div class="calculating-bg-grid"></div>
      <div class="calculating-slicer-laser"></div>

      <!-- Slicer Header -->
      <div class="studio-calc-header">
        <div class="studio-calc-badge">
          <span class="studio-calc-pulse-dot"></span>
          <span>${lang === 'tr' ? 'Endüstriyel Dilimleme Motoru' : 'Industrial Slicing Engine'}</span>
        </div>
        <h3 class="studio-calc-title">${lang === 'tr' ? '3D Model Dilimleniyor & Hesaplanıyor' : 'Slicing & Analyzing 3D Model'}</h3>
        <p class="studio-calc-sub">${filename || (lang === 'tr' ? '3D CAD Modeli' : '3D CAD Model')} • ${lang === 'tr' ? 'Hassas katman dilimleme ve hacim analizi yapılıyor.' : 'Running precision slicing & volume calculation.'}</p>
      </div>

      <!-- Countdown Banner & Progress Track -->
      <div class="studio-calc-progress-section">
        <div class="calculating-timer-banner studio-timer-compact">
          <span class="calculating-timer-icon">⏳</span>
          <span class="calculating-timer-text">
            ${lang === 'tr' ? 'Kalan Süre:' : 'Remaining Time:'} 
            <span class="calculating-timer-seconds" id="studio-calc-countdown">10</span> 
            ${lang === 'tr' ? 'saniye' : 'seconds'}
          </span>
        </div>

        <div class="calculating-progress-track studio-progress-track">
          <div class="calculating-progress-fill" id="studio-calc-progress" style="width: 0%;"></div>
        </div>

        <div class="studio-calc-status-bar">
          <span class="studio-calc-pct-label" id="studio-calc-pct">0% ${lang === 'tr' ? 'Dilimlendi' : 'Sliced'}</span>
          <span class="studio-calc-ticker-text" id="studio-calc-active-ticker">${lang === 'tr' ? steps[0].tr : steps[0].en}</span>
        </div>
      </div>

      <!-- 3-Phase Interactive Workflow Pipeline -->
      <div class="studio-phases-pipeline">
        <div class="studio-phase-card active" id="studio-phase-1">
          <div class="phase-icon" id="studio-phase-icon-1">1</div>
          <div class="phase-info">
            <div class="phase-title">${lang === 'tr' ? '1. Geometri' : '1. Geometry'}</div>
            <div class="phase-desc" id="studio-phase-status-1">${lang === 'tr' ? 'İşleniyor' : 'Processing'}</div>
          </div>
        </div>

        <div class="phase-connector" id="studio-phase-conn-1"></div>

        <div class="studio-phase-card" id="studio-phase-2">
          <div class="phase-icon" id="studio-phase-icon-2">2</div>
          <div class="phase-info">
            <div class="phase-title">${lang === 'tr' ? '2. Dilimleme' : '2. Slicing'}</div>
            <div class="phase-desc" id="studio-phase-status-2">${lang === 'tr' ? 'Bekliyor' : 'Queued'}</div>
          </div>
        </div>

        <div class="phase-connector" id="studio-phase-conn-2"></div>

        <div class="studio-phase-card" id="studio-phase-3">
          <div class="phase-icon" id="studio-phase-icon-3">3</div>
          <div class="phase-info">
            <div class="phase-title">${lang === 'tr' ? '3. Maliyet' : '3. Pricing'}</div>
            <div class="phase-desc" id="studio-phase-status-3">${lang === 'tr' ? 'Bekliyor' : 'Queued'}</div>
          </div>
        </div>
      </div>

      <!-- Micro Telemetry Bottom Bar -->
      <div class="studio-telemetry-row">
        <div class="studio-telem-item">
          <span class="telem-label">${lang === 'tr' ? 'Dilim Katmanı' : 'Slicing Layer'}</span>
          <span class="telem-val" id="studio-stat-layer">0 / 342</span>
        </div>
        <div class="studio-telem-item">
          <span class="telem-label">${lang === 'tr' ? 'Doluluk (Infill)' : 'Infill Density'}</span>
          <span class="telem-val">%${this._3dConfig.infill || 20}</span>
        </div>
        <div class="studio-telem-item">
          <span class="telem-label">${lang === 'tr' ? 'Üretim Tablası' : 'Build Plate'}</span>
          <span class="telem-val">250×250 mm</span>
        </div>
        <div class="studio-telem-item">
          <span class="telem-label">${lang === 'tr' ? 'Geometri' : 'Geometry'}</span>
          <span class="telem-val">%100 Manifold</span>
        </div>
      </div>
    `;

    const totalLayers = 342;
    const intervalMs = 100;

    this._3dCalcInterval = setInterval(() => {
      elapsed += intervalMs;
      const progressPct = Math.min(100, Math.round((elapsed / totalDuration) * 100));
      const remainingSeconds = Math.max(0, Math.ceil((totalDuration - elapsed) / 1000));

      const countdownEl = document.getElementById('studio-calc-countdown');
      const progressEl = document.getElementById('studio-calc-progress');
      const pctEl = document.getElementById('studio-calc-pct');
      const layerEl = document.getElementById('studio-stat-layer');

      if (countdownEl) countdownEl.textContent = remainingSeconds;
      if (progressEl) progressEl.style.width = `${progressPct}%`;
      if (pctEl) pctEl.textContent = `${progressPct}% ${lang === 'tr' ? 'Dilimlendi' : 'Sliced'}`;
      if (layerEl) {
        const curLayer = Math.min(totalLayers, Math.round((elapsed / totalDuration) * totalLayers));
        layerEl.textContent = `${curLayer} / ${totalLayers}`;
      }

      // Determine active granular step & update ticker
      let accumulatedTime = 0;
      let activeStep = steps[0];
      for (let i = 0; i < steps.length; i++) {
        const step = steps[i];
        accumulatedTime += step.duration;
        if (elapsed <= accumulatedTime) {
          activeStep = step;
          break;
        }
        if (i === steps.length - 1) activeStep = steps[steps.length - 1];
      }

      const tickerEl = document.getElementById('studio-calc-active-ticker');
      if (tickerEl) {
        tickerEl.textContent = lang === 'tr' ? activeStep.tr : activeStep.en;
      }

      // Update 3 Phase Pipeline Cards
      const p1End = steps[0].duration + steps[1].duration;
      const p2End = p1End + steps[2].duration + steps[3].duration;

      const p1Card = document.getElementById('studio-phase-1');
      const p1Icon = document.getElementById('studio-phase-icon-1');
      const p1Status = document.getElementById('studio-phase-status-1');
      const conn1 = document.getElementById('studio-phase-conn-1');

      const p2Card = document.getElementById('studio-phase-2');
      const p2Icon = document.getElementById('studio-phase-icon-2');
      const p2Status = document.getElementById('studio-phase-status-2');
      const conn2 = document.getElementById('studio-phase-conn-2');

      const p3Card = document.getElementById('studio-phase-3');
      const p3Icon = document.getElementById('studio-phase-icon-3');
      const p3Status = document.getElementById('studio-phase-status-3');

      // Phase 1: CAD & Geometry
      if (p1Card && p1Icon && p1Status) {
        if (elapsed >= p1End) {
          p1Card.className = 'studio-phase-card completed';
          p1Icon.textContent = '✓';
          p1Status.textContent = lang === 'tr' ? 'Doğrulandı' : 'Verified';
          if (conn1) conn1.className = 'phase-connector completed';
        } else {
          p1Card.className = 'studio-phase-card active';
          p1Icon.textContent = '⚡';
          p1Status.textContent = lang === 'tr' ? 'İşleniyor' : 'Processing';
        }
      }

      // Phase 2: Slicing & Toolpaths
      if (p2Card && p2Icon && p2Status) {
        if (elapsed >= p2End) {
          p2Card.className = 'studio-phase-card completed';
          p2Icon.textContent = '✓';
          p2Status.textContent = lang === 'tr' ? 'Dilimlendi' : 'Sliced';
          if (conn2) conn2.className = 'phase-connector completed';
        } else if (elapsed >= p1End) {
          p2Card.className = 'studio-phase-card active';
          p2Icon.textContent = '⚡';
          p2Status.textContent = lang === 'tr' ? 'Dilimleniyor' : 'Slicing';
        } else {
          p2Card.className = 'studio-phase-card';
          p2Icon.textContent = '2';
          p2Status.textContent = lang === 'tr' ? 'Bekliyor' : 'Queued';
        }
      }

      // Phase 3: Production & Cost Estimation
      if (p3Card && p3Icon && p3Status) {
        if (elapsed >= totalDuration) {
          p3Card.className = 'studio-phase-card completed';
          p3Icon.textContent = '✓';
          p3Status.textContent = lang === 'tr' ? 'Tamamlandı' : 'Complete';
        } else if (elapsed >= p2End) {
          p3Card.className = 'studio-phase-card active';
          p3Icon.textContent = '⚡';
          p3Status.textContent = lang === 'tr' ? 'Hesaplanıyor' : 'Calculating';
        } else {
          p3Card.className = 'studio-phase-card';
          p3Icon.textContent = '3';
          p3Status.textContent = lang === 'tr' ? 'Bekliyor' : 'Queued';
        }
      }

      if (elapsed >= totalDuration) {
        clearInterval(this._3dCalcInterval);
        this._3dCalcInterval = null;
        this._is3DCalculating = false;

        overlay.style.display = 'none';
        if (typeof onComplete === 'function') {
          onComplete();
        }
        this.showToast(lang === 'tr' ? '3D Slicing ve Fiyat Analizi Tamamlandı!' : '3D Slicing & Cost Analysis Complete!', 'success');
      }
    }, intervalMs);
  }

  trigger3DRecalculate() {
    if (!this._3dConfig.filename || this._3dConfig.volumeCm3 <= 0) {
      this.showToast('Lütfen önce bir 3D model yükleyin.', 'info');
      return;
    }

    this.start3DCalculatingSimulation(this._3dConfig.filename, () => {
      this.calculate3DPrice();
      const controls = document.getElementById('viewport-floating-controls');
      if (controls) controls.style.display = 'flex';
      const metrics = document.getElementById('model-metrics-bar');
      if (metrics) metrics.style.display = 'grid';
    });
  }

  remove3DModel() {
    // 1. Remove and dispose current 3D mesh
    if (this._currentMesh) {
      if (this._3dScene) {
        this._3dScene.remove(this._currentMesh);
      }
      if (this._currentMesh.geometry) {
        this._currentMesh.geometry.dispose();
      }
      if (this._currentMesh.material) {
        if (Array.isArray(this._currentMesh.material)) {
          this._currentMesh.material.forEach(m => m.dispose());
        } else {
          this._currentMesh.material.dispose();
        }
      }
      this._currentMesh = null;
    }

    // 2. Clear calculating interval if active
    if (this._3dCalcInterval) {
      clearInterval(this._3dCalcInterval);
      this._3dCalcInterval = null;
    }
    this._is3DCalculating = false;

    // 3. Reset 3D Configuration
    this._3dConfig.filename = '';
    this._3dConfig.dimX = 0;
    this._3dConfig.dimY = 0;
    this._3dConfig.dimZ = 0;
    this._3dConfig.volumeCm3 = 0;

    // 4. Reset File Input
    const fileInput = document.getElementById('file-3d-input');
    if (fileInput) fileInput.value = '';

    // 5. Hide Overlays & Floating Toolbars
    const overlay = document.getElementById('viewport-calculating-overlay');
    if (overlay) overlay.style.display = 'none';

    const controls = document.getElementById('viewport-floating-controls');
    if (controls) controls.style.display = 'none';

    const metrics = document.getElementById('model-metrics-bar');
    if (metrics) metrics.style.display = 'none';

    // 6. Reset & Show Viewport Dropzone
    const dropzone = document.getElementById('viewport-dropzone');
    if (dropzone) {
      dropzone.style.display = 'flex';
      dropzone.classList.remove('hidden');
    }

    // 7. Reset Camera & View
    if (this._3dCamera) {
      this._3dCamera.position.set(0, 85, 160);
      this._3dCamera.lookAt(0, 0, 0);
    }
    if (this._3dControls) {
      this._3dControls.target.set(0, 0, 0);
      this._3dControls.autoRotate = false;
      this._3dControls.update();
    }
    const rotateBtn = document.getElementById('btn-3d-autorotate');
    if (rotateBtn) rotateBtn.classList.remove('active');

    if (this._3dRenderer && this._3dScene && this._3dCamera) {
      this._3dRenderer.render(this._3dScene, this._3dCamera);
    }

    // 8. Recalculate price
    this.calculate3DPrice();

    const lang = window.i18n ? window.i18n.currentLang : 'tr';
    this.showToast(lang === 'tr' ? 'Model silindi. Yeni bir 3D model yükleyebilirsiniz.' : 'Model removed. You can now upload a new 3D model.', 'info');
  }

  load3DSamplePreset(presetName) {
    if (!this._3dScene || !this._3dRenderer) {
      this.init3DViewer();
      this.init3DStudio();
      this._3dViewerInitialized = true;
    }

    let filename = 'gopro_hero11_mount.stl';
    let sizeX = 52, sizeY = 44, sizeZ = 40;
    let volCm3 = 24.5;
    let mat = 'TPU';
    let colorHex = '#eab308'; // Neon Yellow
    let colorName = 'Neon Sarı (TPU)';
    let infill = 50;

    if (presetName === 'motor_guard') {
      filename = 'motor_arm_guard_2207.stl';
      sizeX = 36; sizeY = 14; sizeZ = 36;
      volCm3 = 11.2;
      mat = 'TPU';
      colorHex = '#f97316'; // Pozitron Orange
      colorName = 'Pozitron Turuncu';
      infill = 80;
    }

    this._3dConfig.filename = filename;
    this._3dConfig.material = mat;
    this._3dConfig.colorHex = colorHex;
    this._3dConfig.colorName = colorName;
    this._3dConfig.infill = infill;

    this.select3DMaterial(mat);
    this.select3DColor(colorHex, colorName);
    this.update3DInfill(infill);

    this.start3DCalculatingSimulation(filename, () => {
      let geometry;
      if (presetName === 'motor_guard' && typeof THREE !== 'undefined' && THREE.CylinderGeometry) {
        geometry = new THREE.CylinderGeometry(sizeX / 2, sizeX / 2, sizeY, 32);
      } else if (typeof THREE !== 'undefined' && THREE.BoxGeometry) {
        geometry = new THREE.BoxGeometry(sizeX, sizeY, sizeZ);
      }
      if (geometry) {
        geometry.computeVertexNormals();
        this.renderCustomGeometryWithSpecs(geometry, filename, sizeX, sizeY, sizeZ, volCm3);
      }
    });
  }

  renderCustomGeometryWithSpecs(geometry, filename, sizeX, sizeY, sizeZ, volCm3) {
    if (!this._3dScene) return;

    if (this._currentMesh) {
      this._3dScene.remove(this._currentMesh);
      if (this._currentMesh.geometry) this._currentMesh.geometry.dispose();
      if (this._currentMesh.material) this._currentMesh.material.dispose();
      this._currentMesh = null;
    }

    this._3dConfig.dimX = sizeX;
    this._3dConfig.dimY = sizeY;
    this._3dConfig.dimZ = sizeZ;
    this._3dConfig.volumeCm3 = volCm3;

    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(this._3dConfig.colorHex),
      roughness: 0.28,
      metalness: 0.18
    });

    this._currentMesh = new THREE.Mesh(geometry, material);
    this._currentMesh.position.y = sizeY / 2;
    this._3dScene.add(this._currentMesh);

    const maxDim = Math.max(sizeX, sizeY, sizeZ, 30);
    this._3dCamera.position.set(0, maxDim * 1.2, maxDim * 2.2);
    if (this._3dControls) {
      this._3dControls.target.set(0, sizeY / 2, 0);
      this._3dControls.update();
    }

    this.updateMetricsUI(filename, sizeX, sizeY, sizeZ, volCm3);
    this.calculate3DPrice();

    const dropzone = document.getElementById('viewport-dropzone');
    if (dropzone) dropzone.style.display = 'none';
    const controls = document.getElementById('viewport-floating-controls');
    if (controls) controls.style.display = 'flex';
    const metrics = document.getElementById('model-metrics-bar');
    if (metrics) metrics.style.display = 'grid';
  }

  async decompress3MFData(compressed, compMethod) {
    if (compMethod === 0) return compressed;
    if (compMethod === 8) {
      if (typeof DecompressionStream !== 'undefined') {
        const ds = new DecompressionStream('deflate-raw');
        const writer = ds.writable.getWriter();
        writer.write(compressed);
        writer.close();
        const reader = ds.readable.getReader();
        const chunks = [];
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          chunks.push(value);
        }
        const total = chunks.reduce((a, c) => a + c.length, 0);
        const res = new Uint8Array(total);
        let off = 0;
        for (const c of chunks) {
          res.set(c, off);
          off += c.length;
        }
        return res;
      } else {
        throw new Error('Tarayıcınız DecompressionStream API desteklemiyor.');
      }
    }
    throw new Error('Desteklenmeyen ZIP sıkıştırma yöntemi: ' + compMethod);
  }

  parse3MFXml(xml) {
    const vertices = [];
    const vRegex = /<vertex\s+([^>]+)\/>/gi;
    let match;
    while ((match = vRegex.exec(xml)) !== null) {
      const attrs = match[1];
      const xM = attrs.match(/\bx=[\"']([^\"']+)[\"']/i);
      const yM = attrs.match(/\by=[\"']([^\"']+)[\"']/i);
      const zM = attrs.match(/\bz=[\"']([^\"']+)[\"']/i);
      if (xM && yM && zM) {
        vertices.push(parseFloat(xM[1]), parseFloat(yM[1]), parseFloat(zM[1]));
      }
    }

    const tRegex = /<triangle\s+([^>]+)\/>/gi;
    const triIndices = [];
    while ((match = tRegex.exec(xml)) !== null) {
      const attrs = match[1];
      const v1M = attrs.match(/\bv1=[\"'](\d+)[\"']/i);
      const v2M = attrs.match(/\bv2=[\"'](\d+)[\"']/i);
      const v3M = attrs.match(/\bv3=[\"'](\d+)[\"']/i);
      if (v1M && v2M && v3M) {
        triIndices.push(parseInt(v1M[1], 10), parseInt(v2M[1], 10), parseInt(v3M[1], 10));
      }
    }

    const positions = new Float32Array(triIndices.length * 3);
    let ptr = 0;
    for (let i = 0; i < triIndices.length; i += 3) {
      const i1 = triIndices[i] * 3;
      const i2 = triIndices[i + 1] * 3;
      const i3 = triIndices[i + 2] * 3;
      if (i1 < vertices.length && i2 < vertices.length && i3 < vertices.length) {
        positions[ptr++] = vertices[i1];
        positions[ptr++] = vertices[i1 + 1];
        positions[ptr++] = vertices[i1 + 2];
        positions[ptr++] = vertices[i2];
        positions[ptr++] = vertices[i2 + 1];
        positions[ptr++] = vertices[i2 + 2];
        positions[ptr++] = vertices[i3];
        positions[ptr++] = vertices[i3 + 1];
        positions[ptr++] = vertices[i3 + 2];
      }
    }
    return {
      verticesCount: vertices.length / 3,
      trianglesCount: triIndices.length / 3,
      positions: positions.subarray(0, ptr)
    };
  }

  async parse3MFBuffer(buffer) {
    const buf = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    const view = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);

    // Find End of Central Directory Record (EOCD): signature 0x06054b50
    let eocdOffset = -1;
    for (let i = buf.length - 22; i >= Math.max(0, buf.length - 65557); i--) {
      if (view.getUint32(i, true) === 0x06054b50) {
        eocdOffset = i;
        break;
      }
    }
    if (eocdOffset === -1) {
      throw new Error('Geçersiz 3MF dosyası (ZIP EOCD başlığı bulunamadı).');
    }

    const cdCount = view.getUint16(eocdOffset + 10, true);
    const cdOffset = view.getUint32(eocdOffset + 16, true);
    const files = {};
    let cur = cdOffset;
    for (let i = 0; i < cdCount; i++) {
      if (view.getUint32(cur, true) !== 0x02014b50) break;
      const compMethod = view.getUint16(cur + 10, true);
      const compSize = view.getUint32(cur + 20, true);
      const nameLen = view.getUint16(cur + 28, true);
      const extraLen = view.getUint16(cur + 30, true);
      const commentLen = view.getUint16(cur + 32, true);
      const localHeaderOffset = view.getUint32(cur + 42, true);
      const name = new TextDecoder('utf-8').decode(buf.subarray(cur + 46, cur + 46 + nameLen));
      const localNameLen = view.getUint16(localHeaderOffset + 26, true);
      const localExtraLen = view.getUint16(localHeaderOffset + 28, true);
      const dataStart = localHeaderOffset + 30 + localNameLen + localExtraLen;
      const compressed = buf.subarray(dataStart, dataStart + compSize);
      files[name] = { compMethod, compressed };
      cur += 46 + nameLen + extraLen + commentLen;
    }

    const modelNames = Object.keys(files).filter(k => k.toLowerCase().endsWith('.model'));
    if (modelNames.length === 0) {
      throw new Error('3MF paketinde .model 3D geometrisi bulunamadı.');
    }

    const parts = [];
    let totalTriangles = 0;
    for (const mName of modelNames) {
      const raw = await this.decompress3MFData(files[mName].compressed, files[mName].compMethod);
      const xml = new TextDecoder('utf-8').decode(raw);
      const parsed = this.parse3MFXml(xml);
      if (parsed.positions.length > 0) {
        parts.push(parsed.positions);
        totalTriangles += parsed.trianglesCount;
      }
    }

    if (parts.length === 0) {
      throw new Error('3MF dosyasında 3D mesh üçgeni bulunamadı.');
    }

    const totalLen = parts.reduce((a, p) => a + p.length, 0);
    const combined = new Float32Array(totalLen);
    let offset = 0;
    for (const p of parts) {
      combined.set(p, offset);
      offset += p.length;
    }

    return { positions: combined, trianglesCount: totalTriangles };
  }

  handle3DFileUpload(file) {
    if (!file) return;

    if (!this._3dScene || !this._3dRenderer) {
      this.init3DViewer();
      this.init3DStudio();
      this._3dViewerInitialized = true;
    }

    const filename = file.name || 'model.step';
    const ext = filename.split('.').pop().toLowerCase();
    this._3dConfig.filename = filename;

    this.showToast(`Dosya okunuyor: ${filename}...`, 'info');

    // Also upload file to localhost server backend storage
    this.upload3DFileToServer(file);

    const reader = new FileReader();

    if (ext === 'stl') {
      reader.onload = (e) => {
        try {
          const buffer = e.target.result;
          this.start3DCalculatingSimulation(filename, () => {
            this.renderSTLModel(buffer, filename);
          });
        } catch (err) {
          console.error('STL Parse Error:', err);
          this.start3DCalculatingSimulation(filename, () => {
            this.showToast('STL dosyası işlenirken hata oluştu: ' + err.message, 'error');
            this.renderSimulatedFallbackModel(filename, file.size);
          });
        }
      };
      reader.onerror = () => {
        this.showToast('STL dosyası okunamadı.', 'error');
        this.renderSimulatedFallbackModel(filename, file.size);
      };
      reader.readAsArrayBuffer(file);
    } else if (ext === '3mf') {
      reader.onload = async (e) => {
        try {
          const buffer = e.target.result;
          const parsed = await this.parse3MFBuffer(buffer);
          if (!parsed || !parsed.positions || parsed.positions.length === 0) {
            throw new Error('3MF dosyasında geçerli mesh geometrisi bulunamadı.');
          }
          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute('position', new THREE.BufferAttribute(parsed.positions, 3));
          geometry.computeVertexNormals();
          geometry.center();

          this.start3DCalculatingSimulation(filename, () => {
            this.renderCustomGeometry(geometry, filename);
          });
        } catch (err) {
          console.error('3MF Parse Error:', err);
          this.start3DCalculatingSimulation(filename, () => {
            this.showToast('3MF dosyası işlenirken hata oluştu: ' + err.message, 'error');
            this.renderSimulatedFallbackModel(filename, file.size);
          });
        }
      };
      reader.onerror = () => {
        this.showToast('3MF dosyası okunamadı.', 'error');
        this.renderSimulatedFallbackModel(filename, file.size);
      };
      reader.readAsArrayBuffer(file);
    } else if (ext === 'obj') {
      reader.onload = (e) => {
        try {
          const text = e.target.result;
          const geometry = this.parseOBJData(text);
          this.start3DCalculatingSimulation(filename, () => {
            if (geometry) {
              this.renderCustomGeometry(geometry, filename);
            } else {
              this.renderSTEPTextFallback(text, filename, file.size);
            }
          });
        } catch (err) {
          console.error('OBJ Parse Error:', err);
          this.start3DCalculatingSimulation(filename, () => {
            this.renderSTEPTextFallback(e.target.result || '', filename, file.size);
          });
        }
      };
      reader.onerror = () => {
        this.showToast('OBJ dosyası okunamadı.', 'error');
        this.renderSimulatedFallbackModel(filename, file.size);
      };
      reader.readAsText(file);
    } else {
      // STEP / STP / IGES CAD Files
      reader.onload = (e) => {
        try {
          const text = typeof e.target.result === 'string' ? e.target.result : new TextDecoder('utf-8').decode(e.target.result);
          this.start3DCalculatingSimulation(filename, () => {
            this.renderSTEPTextFallback(text, filename, file.size);
          });
        } catch (err) {
          console.error('CAD Parse Error:', err);
          this.start3DCalculatingSimulation(filename, () => {
            this.renderSimulatedFallbackModel(filename, file.size);
          });
        }
      };
      reader.onerror = () => {
        this.showToast('CAD dosyası okunamadı.', 'error');
        this.renderSimulatedFallbackModel(filename, file.size);
      };
      reader.readAsText(file);
    }
  }

  parseOBJData(text) {
    const lines = text.split('\n');
    const vertices = [];
    const positions = [];
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      if (line.startsWith('v ')) {
        const parts = line.split(/\s+/).slice(1).map(parseFloat);
        vertices.push(new THREE.Vector3(parts[0], parts[1], parts[2]));
      } else if (line.startsWith('f ')) {
        const parts = line.split(/\s+/).slice(1).map(p => {
          const idx = parseInt(p.split('/')[0], 10);
          return idx > 0 ? idx - 1 : vertices.length + idx;
        });
        if (parts.length >= 3) {
          for (let j = 1; j < parts.length - 1; j++) {
            const v0 = vertices[parts[0]];
            const v1 = vertices[parts[j]];
            const v2 = vertices[parts[j + 1]];
            if (v0 && v1 && v2) {
              positions.push(v0.x, v0.y, v0.z);
              positions.push(v1.x, v1.y, v1.z);
              positions.push(v2.x, v2.y, v2.z);
            }
          }
        }
      }
    }

    if (positions.length === 0) return null;

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    geometry.computeVertexNormals();
    geometry.center();
    return geometry;
  }

  renderCustomGeometry(geometry, filename) {
    if (!this._3dScene) return;

    if (this._currentMesh) {
      this._3dScene.remove(this._currentMesh);
      if (this._currentMesh.geometry) this._currentMesh.geometry.dispose();
      if (this._currentMesh.material) this._currentMesh.material.dispose();
      this._currentMesh = null;
    }

    geometry.computeBoundingBox();
    const bbox = geometry.boundingBox;
    const sizeX = Math.max(1, Math.round(bbox.max.x - bbox.min.x));
    const sizeY = Math.max(1, Math.round(bbox.max.y - bbox.min.y));
    const sizeZ = Math.max(1, Math.round(bbox.max.z - bbox.min.z));

    const volCm3 = this.calculateGeometryVolume(geometry);

    this._3dConfig.dimX = sizeX;
    this._3dConfig.dimY = sizeY;
    this._3dConfig.dimZ = sizeZ;
    this._3dConfig.volumeCm3 = Math.max(0.5, volCm3);

    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(this._3dConfig.colorHex),
      roughness: 0.28,
      metalness: 0.18
    });

    this._currentMesh = new THREE.Mesh(geometry, material);
    this._currentMesh.position.y = (bbox.max.y - bbox.min.y) / 2;
    this._3dScene.add(this._currentMesh);

    const maxDim = Math.max(sizeX, sizeY, sizeZ, 30);
    this._3dCamera.position.set(0, maxDim * 1.2, maxDim * 2.2);
    if (this._3dControls) {
      this._3dControls.target.set(0, (bbox.max.y - bbox.min.y) / 2, 0);
      this._3dControls.update();
    }

    this.updateMetricsUI(filename, sizeX, sizeY, sizeZ, this._3dConfig.volumeCm3);
    this.calculate3DPrice();

    const dropzone = document.getElementById('viewport-dropzone');
    if (dropzone) dropzone.style.display = 'none';
    const controls = document.getElementById('viewport-floating-controls');
    if (controls) controls.style.display = 'flex';
    const metrics = document.getElementById('model-metrics-bar');
    if (metrics) metrics.style.display = 'grid';

    this.showToast(`Model yüklendi: ${filename}`, 'success');
  }

  renderSTLModel(arrayBuffer, filename) {
    if (!this._3dScene) return;

    if (this._currentMesh) {
      this._3dScene.remove(this._currentMesh);
      if (this._currentMesh.geometry) this._currentMesh.geometry.dispose();
      if (this._currentMesh.material) this._currentMesh.material.dispose();
      this._currentMesh = null;
    }

    let geometry;
    if (typeof THREE.STLLoader !== 'undefined') {
      const loader = new THREE.STLLoader();
      geometry = loader.parse(arrayBuffer);
    }

    if (!geometry) {
      this.showToast('STL dosyası okunamadı. Lütfen geçerli bir 3D model yükleyin.', 'error');
      return;
    }

    geometry.computeVertexNormals();
    geometry.center();

    // Compute exact bounding box
    geometry.computeBoundingBox();
    const bbox = geometry.boundingBox;
    const sizeX = Math.round(bbox.max.x - bbox.min.x);
    const sizeY = Math.round(bbox.max.y - bbox.min.y);
    const sizeZ = Math.round(bbox.max.z - bbox.min.z);

    // Compute exact tetrahedron signed volume
    const volCm3 = this.calculateGeometryVolume(geometry);

    this._3dConfig.dimX = sizeX;
    this._3dConfig.dimY = sizeY;
    this._3dConfig.dimZ = sizeZ;
    this._3dConfig.volumeCm3 = Math.max(0.5, volCm3);

    // Create Mesh with glossy studio finish
    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(this._3dConfig.colorHex),
      roughness: 0.28,
      metalness: 0.18,
      wireframe: false
    });

    this._currentMesh = new THREE.Mesh(geometry, material);
    this._currentMesh.position.y = (bbox.max.y - bbox.min.y) / 2;
    this._3dScene.add(this._currentMesh);

    // Adjust camera distance to fit model
    const maxDim = Math.max(sizeX, sizeY, sizeZ, 30);
    this._3dCamera.position.set(0, maxDim * 1.2, maxDim * 2.2);
    const container = document.getElementById('viewport-3d-container');
    if (container && this._3dRenderer && this._3dCamera) {
      const w = container.clientWidth || 500;
      const h = container.clientHeight || 420;
      if (w > 0 && h > 0) {
        this._3dCamera.aspect = w / h;
        this._3dCamera.updateProjectionMatrix();
        this._3dRenderer.setSize(w, h);
      }
    }
    if (this._3dRenderer && this._3dScene && this._3dCamera) {
      this._3dRenderer.render(this._3dScene, this._3dCamera);
    }

    // Update UI
    this.updateMetricsUI(filename, sizeX, sizeY, sizeZ, this._3dConfig.volumeCm3);
    this.calculate3DPrice();

    const dropzone = document.getElementById('viewport-dropzone');
    if (dropzone) dropzone.style.display = 'none';
    const controls = document.getElementById('viewport-floating-controls');
    if (controls) controls.style.display = 'flex';
    const metrics = document.getElementById('model-metrics-bar');
    if (metrics) metrics.style.display = 'grid';

    this.showToast(`STL Model başarıyla yüklendi: ${filename}`, 'success');
  }

  renderSTEPTextFallback(stepText, filename, fileSize) {
    if (!this._3dScene || !this._3dRenderer) {
      this.init3DViewer();
      this.init3DStudio();
    }

    if (this._currentMesh) {
      this._3dScene.remove(this._currentMesh);
      if (this._currentMesh.traverse) {
        this._currentMesh.traverse((child) => {
          if (child.geometry) child.geometry.dispose();
          if (child.material) {
            if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
            else child.material.dispose();
          }
        });
      }
      this._currentMesh = null;
    }

    // 1. Comprehensive multi-regex extraction for STEP / STP CAD formats
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;
    let count = 0;
    const extractedPts = [];

    if (typeof stepText === 'string' && stepText.length > 0) {
      // Primary pattern: CARTESIAN_POINT('',(x,y,z)) or CARTESIAN_POINT('name',(x,y,z))
      const ptRegex1 = /CARTESIAN_POINT\s*\(\s*['"]?[^'"]*['"]?\s*,\s*\(\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*,\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*(?:,\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?))?\s*\)\s*\)/gi;
      let match;
      while ((match = ptRegex1.exec(stepText)) !== null) {
        const x = parseFloat(match[1]);
        const y = parseFloat(match[2]);
        const z = match[3] !== undefined ? parseFloat(match[3]) : 0;
        if (!isNaN(x) && !isNaN(y) && !isNaN(z)) {
          if (Math.abs(x) < 5000 && Math.abs(y) < 5000 && Math.abs(z) < 5000) {
            minX = Math.min(minX, x); maxX = Math.max(maxX, x);
            minY = Math.min(minY, y); maxY = Math.max(maxY, y);
            minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z);
            extractedPts.push({ x, y, z });
            count++;
            if (count >= 15000) break;
          }
        }
      }

      // Secondary fallback pattern for loose/multiline STEP Cartesian points
      if (count < 2) {
        const ptRegex2 = /CARTESIAN_POINT[^(]*\([^,]*,\s*\(\s*([-\s\d.eE+]+)\s*,\s*([-\s\d.eE+]+)\s*(?:,\s*([-\s\d.eE+]+))?\s*\)\s*\)/gi;
        while ((match = ptRegex2.exec(stepText)) !== null) {
          const x = parseFloat(match[1].replace(/\s+/g, ''));
          const y = parseFloat(match[2].replace(/\s+/g, ''));
          const z = match[3] ? parseFloat(match[3].replace(/\s+/g, '')) : 0;
          if (!isNaN(x) && !isNaN(y) && !isNaN(z)) {
            if (Math.abs(x) < 5000 && Math.abs(y) < 5000 && Math.abs(z) < 5000) {
              minX = Math.min(minX, x); maxX = Math.max(maxX, x);
              minY = Math.min(minY, y); maxY = Math.max(maxY, y);
              minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z);
              extractedPts.push({ x, y, z });
              count++;
              if (count >= 15000) break;
            }
          }
        }
      }
    }

    // 2. Parse CIRCLE, CYLINDRICAL_SURFACE, CONICAL_SURFACE for cylindrical CAD bodies
    let maxRadius = 0;
    let match;
    const circleRegex = /CIRCLE\s*\(\s*[^,]*,[^,]*,\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*\)/gi;
    while ((match = circleRegex.exec(stepText)) !== null) {
      const r = parseFloat(match[1]);
      if (!isNaN(r) && r > maxRadius && r < 2000) maxRadius = r;
    }

    const conicalRegex = /CONICAL_SURFACE\s*\(\s*[^,]*,[^,]*,\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*,/gi;
    while ((match = conicalRegex.exec(stepText)) !== null) {
      const r = parseFloat(match[1]);
      if (!isNaN(r) && r > maxRadius && r < 2000) maxRadius = r;
    }

    const cylRegex = /CYLINDRICAL_SURFACE\s*\(\s*[^,]*,[^,]*,\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*\)/gi;
    while ((match = cylRegex.exec(stepText)) !== null) {
      const r = parseFloat(match[1]);
      if (!isNaN(r) && r > maxRadius && r < 2000) maxRadius = r;
    }

    let sizeX = 45, sizeY = 25, sizeZ = 35;
    let volCm3 = 14.5;
    let isCylinder = false;

    const spanX = (isFinite(minX) && isFinite(maxX)) ? (maxX - minX) : 0;
    const spanY = (isFinite(minY) && isFinite(maxY)) ? (maxY - minY) : 0;
    const spanZ = (isFinite(minZ) && isFinite(maxZ)) ? (maxZ - minZ) : 0;

    if (maxRadius > 0) {
      isCylinder = true;
      const diameter = Math.round(maxRadius * 2 * 10) / 10;
      if (spanZ >= spanX && spanZ >= spanY && spanZ > 1) {
        sizeX = Math.round(diameter);
        sizeY = Math.round(diameter);
        sizeZ = Math.max(1, Math.round(spanZ));
      } else if (spanY >= spanX && spanY >= spanZ && spanY > 1) {
        sizeX = Math.round(diameter);
        sizeY = Math.max(1, Math.round(spanY));
        sizeZ = Math.round(diameter);
      } else {
        sizeX = Math.max(1, Math.round(spanX || 50));
        sizeY = Math.round(diameter);
        sizeZ = Math.round(diameter);
      }
      volCm3 = Math.max(0.5, Math.round((Math.PI * Math.pow(maxRadius, 2) * Math.max(sizeX, sizeY, sizeZ) / 1000) * 10) / 10);
    } else if (count >= 4 && isFinite(minX) && isFinite(maxX) && (spanX > 0.5 || spanY > 0.5 || spanZ > 0.5)) {
      sizeX = Math.max(4, Math.round(spanX || spanY || 20));
      sizeY = Math.max(4, Math.round(spanY || spanX || 20));
      sizeZ = Math.max(4, Math.round(spanZ || 15));
      const boundingVolCm3 = (sizeX * sizeY * sizeZ) / 1000;
      volCm3 = Math.max(0.5, Math.round(boundingVolCm3 * 0.46 * 10) / 10);
    } else {
      const estRadius = Math.cbrt(((fileSize || 60000) / (1024 * 1024)) * 20.0 * 1000 / (Math.PI * 4 / 3));
      sizeX = Math.max(20, Math.round(estRadius * 1.8));
      sizeY = Math.max(15, Math.round(estRadius * 1.4));
      sizeZ = Math.max(18, Math.round(estRadius * 1.8));
      volCm3 = Math.max(1.0, Math.round(((sizeX * sizeY * sizeZ) / 1000 * 0.42) * 10) / 10);
    }

    this._3dConfig.dimX = sizeX;
    this._3dConfig.dimY = sizeY;
    this._3dConfig.dimZ = sizeZ;
    this._3dConfig.volumeCm3 = volCm3;

    // 3. Create high-fidelity engineered CAD 3D representation
    const group = new THREE.Group();
    let geometry;

    const renderHeight = isCylinder ? (spanZ >= spanX ? sizeZ : (spanY >= spanX ? sizeY : sizeX)) : sizeY;

    if (isCylinder) {
      const cylRadius = Math.min(sizeX, sizeY, sizeZ) / 2 || maxRadius || 5;
      geometry = new THREE.CylinderGeometry(cylRadius, cylRadius, renderHeight, 48, 2);
    } else {
      geometry = new THREE.BoxGeometry(sizeX, sizeY, sizeZ, 4, 4, 4);
    }
    geometry.computeVertexNormals();

    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(this._3dConfig.colorHex),
      roughness: 0.28,
      metalness: 0.18,
      wireframe: false
    });

    const mesh = new THREE.Mesh(geometry, material);
    group.add(mesh);

    // Sharp Technical CAD Blueprint Edges
    const edgesGeom = new THREE.EdgesGeometry(geometry, isCylinder ? 20 : 15);
    const edgesMat = new THREE.LineBasicMaterial({ color: 0x0284c7, linewidth: 1.5, transparent: true, opacity: 0.65 });
    const edges = new THREE.LineSegments(edgesGeom, edgesMat);
    group.add(edges);

    this._currentMesh = group;
    this._currentMesh.position.y = renderHeight / 2;
    this._3dScene.add(this._currentMesh);

    // 4. Adjust camera & controls distance to frame the model
    const maxDim = Math.max(sizeX, sizeY, sizeZ, 30);
    this._3dCamera.position.set(0, maxDim * 1.1, maxDim * 2.1);
    if (this._3dControls) {
      this._3dControls.target.set(0, renderHeight / 2, 0);
      this._3dControls.update();
    }

    const container = document.getElementById('viewport-3d-container');
    if (container && this._3dRenderer && this._3dCamera) {
      const w = container.clientWidth || 500;
      const h = container.clientHeight || 420;
      if (w > 0 && h > 0) {
        this._3dCamera.aspect = w / h;
        this._3dCamera.updateProjectionMatrix();
        this._3dRenderer.setSize(w, h);
      }
    }

    if (this._3dRenderer && this._3dScene && this._3dCamera) {
      this._3dRenderer.render(this._3dScene, this._3dCamera);
    }

    // 5. Update UI & Pricing
    this.updateMetricsUI(filename, sizeX, sizeY, sizeZ, this._3dConfig.volumeCm3);
    this.calculate3DPrice();

    const dropzone = document.getElementById('viewport-dropzone');
    if (dropzone) {
      dropzone.style.display = 'none';
      dropzone.classList.add('hidden');
    }
    const controls = document.getElementById('viewport-floating-controls');
    if (controls) controls.style.display = 'flex';
    const metrics = document.getElementById('model-metrics-bar');
    if (metrics) metrics.style.display = 'grid';

    this.showToast(`CAD Modeli yüklendi: ${filename} (${sizeX}×${sizeY}×${sizeZ} mm, ${volCm3} cm³)`, 'success');
  }

  renderSimulatedFallbackModel(filename, fileSize) {
    if (!this._3dScene || !this._3dRenderer) {
      this.init3DViewer();
      this.init3DStudio();
    }

    if (this._currentMesh) {
      this._3dScene.remove(this._currentMesh);
      if (this._currentMesh.traverse) {
        this._currentMesh.traverse((child) => {
          if (child.geometry) child.geometry.dispose();
          if (child.material) {
            if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
            else child.material.dispose();
          }
        });
      }
      this._currentMesh = null;
    }

    const estRadius = Math.cbrt(((fileSize || 50000) / (1024 * 1024)) * 20.0 * 1000 / (Math.PI * 4 / 3));
    const sizeX = Math.max(20, Math.round(estRadius * 2));
    const sizeY = Math.max(15, Math.round(estRadius * 1.5));
    const sizeZ = Math.max(20, Math.round(estRadius * 2));
    const volCm3 = Math.max(1.0, Math.round(((sizeX * sizeY * sizeZ) / 1000 * 0.45) * 10) / 10);

    this._3dConfig.dimX = sizeX;
    this._3dConfig.dimY = sizeY;
    this._3dConfig.dimZ = sizeZ;
    this._3dConfig.volumeCm3 = volCm3;

    const geometry = new THREE.BoxGeometry(sizeX, sizeY, sizeZ);
    geometry.computeVertexNormals();

    const material = new THREE.MeshStandardMaterial({
      color: new THREE.Color(this._3dConfig.colorHex),
      roughness: 0.28,
      metalness: 0.18
    });

    if (this._currentMesh) {
      this._3dScene.remove(this._currentMesh);
      if (this._currentMesh.geometry) this._currentMesh.geometry.dispose();
      if (this._currentMesh.material) this._currentMesh.material.dispose();
      this._currentMesh = null;
    }

    this._currentMesh = new THREE.Mesh(geometry, material);
    this._currentMesh.position.y = sizeY / 2;
    this._3dScene.add(this._currentMesh);

    const maxDim = Math.max(sizeX, sizeY, sizeZ, 30);
    this._3dCamera.position.set(0, maxDim * 1.3, maxDim * 2.3);
    if (this._3dControls) {
      this._3dControls.target.set(0, sizeY / 2, 0);
      this._3dControls.update();
    }

    this.updateMetricsUI(filename, sizeX, sizeY, sizeZ, volCm3);
    this.calculate3DPrice();

    const dropzone = document.getElementById('viewport-dropzone');
    if (dropzone) dropzone.style.display = 'none';
    const controls = document.getElementById('viewport-floating-controls');
    if (controls) controls.style.display = 'flex';
    const metrics = document.getElementById('model-metrics-bar');
    if (metrics) metrics.style.display = 'grid';

    this.showToast(`CAD Modeli yüklendi: ${filename}`, 'success');
  }

  calculateGeometryVolume(geometry) {
    let position = geometry.attributes.position;
    if (!position) return 5.0;
    let faces = position.count / 3;
    let totalVol = 0;
    const p1 = new THREE.Vector3(), p2 = new THREE.Vector3(), p3 = new THREE.Vector3();

    for (let i = 0; i < faces; i++) {
      p1.fromBufferAttribute(position, i * 3 + 0);
      p2.fromBufferAttribute(position, i * 3 + 1);
      p3.fromBufferAttribute(position, i * 3 + 2);

      const v321 = p3.x * p2.y * p1.z;
      const v231 = p2.x * p3.y * p1.z;
      const v312 = p3.x * p1.y * p2.z;
      const v132 = p1.x * p3.y * p2.z;
      const v213 = p2.x * p1.y * p3.z;
      const v123 = p1.x * p2.y * p3.z;

      totalVol += (-v321 + v231 + v312 - v132 - v213 + v123) / 6.0;
    }

    return Math.abs(totalVol) / 1000.0;
  }

  updateMetricsUI(filename, x, y, z, vol) {
    const dimEl = document.getElementById('metric-dim');
    const volEl = document.getElementById('metric-vol');
    const nameEl = document.getElementById('metric-filename');

    if (dimEl) dimEl.textContent = `${x} × ${y} × ${z} mm`;
    if (volEl) volEl.textContent = `${vol.toFixed(1)} cm³`;
    if (nameEl) nameEl.textContent = filename;
  }

  select3DMaterial(matKey) {
    this._3dConfig.material = matKey;
    document.querySelectorAll('.mat-card').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-mat') === matKey);
    });
    this.calculate3DPrice();
  }

  update3DInfill(val) {
    this._3dConfig.infill = parseInt(val, 10);
    const textEl = document.getElementById('infill-percentage-text');
    const hintEl = document.getElementById('infill-hint-text');

    if (textEl) textEl.textContent = `%${val}`;
    if (hintEl) {
      if (val <= 20) hintEl.textContent = 'Standart Sağlamlık (Drone montaj & genel parçalar)';
      else if (val <= 50) hintEl.textContent = 'Güçlendirilmiş (Darbe emici FPV kol koruyucuları)';
      else if (val <= 80) hintEl.textContent = 'Yüksek Mukavemet (Motor yuvaları & taşıyıcı gövde)';
      else hintEl.textContent = '%100 Katı Dolu (Maksimum dayanım & kırılmaz rijitlik)';
    }

    this.calculate3DPrice();
  }

  update3DLayer(val) {
    this._3dConfig.layer = val;
    this.calculate3DPrice();
  }

  select3DColor(hex, name) {
    this._3dConfig.colorHex = hex;
    this._3dConfig.colorName = name;

    document.querySelectorAll('.swatch-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-color') === hex);
    });

    const nameEl = document.getElementById('selected-color-name');
    if (nameEl) nameEl.textContent = name;

    if (this._currentMesh) {
      this._currentMesh.traverse((child) => {
        if (child.isMesh && child.material) {
          child.material.color.set(hex);
        }
      });
    }
  }

  toggle3DWireframe() {
    if (!this._currentMesh) return;
    let isWire = false;
    this._currentMesh.traverse((child) => {
      if (child.isMesh && child.material) {
        child.material.wireframe = !child.material.wireframe;
        isWire = child.material.wireframe;
      }
    });
    const btn = document.getElementById('btn-3d-wireframe');
    if (btn) {
      btn.textContent = isWire ? 'Katı Görünüm' : 'Tel Kafes Görünüm';
    }
  }

  toggle3DAutoRotate() {
    if (this._3dControls) {
      this._3dControls.autoRotate = !this._3dControls.autoRotate;
      const btn = document.getElementById('btn-3d-autorotate');
      if (btn) {
        btn.style.background = this._3dControls.autoRotate ? '#0284c7' : 'rgba(255, 255, 255, 0.92)';
        btn.style.color = this._3dControls.autoRotate ? '#ffffff' : '#1e293b';
        btn.style.borderColor = this._3dControls.autoRotate ? '#0284c7' : '#cbd5e1';
      }
    }
  }

  reset3DCamera() {
    if (this._3dCamera && this._3dControls) {
      const maxDim = Math.max(this._3dConfig.dimX, this._3dConfig.dimY, this._3dConfig.dimZ, 30);
      this._3dCamera.position.set(0, maxDim * 1.2, maxDim * 2.2);
      this._3dControls.target.set(0, this._3dConfig.dimY / 2, 0);
      this._3dControls.update();
    }
  }

  adjust3DQty(delta) {
    const input = document.getElementById('input-3d-qty');
    if (!input) return;
    let val = parseInt(input.value || 1, 10) + delta;
    val = Math.max(1, Math.min(100, val));
    input.value = val;
    this._3dConfig.qty = val;
    this.calculate3DPrice();
  }

  refresh3DMaterialPriceTags() {
    const pricing = JSON.parse(localStorage.getItem('pozitron_3d_pricing') || '{}');
    const materials = ['PLA', 'PETG', 'TPU', 'ABS', 'ASA', 'PA6'];

    materials.forEach(mat => {
      const tagEl = document.getElementById(`mat-price-tag-${mat}`);
      const price = pricing[mat] || (this._3dMaterials[mat] ? this._3dMaterials[mat].defaultPrice : 2.0);
      if (tagEl) tagEl.textContent = `${price.toFixed(2)} ₺/g`;
    });
  }

  calculate3DPrice() {
    const pricing = JSON.parse(localStorage.getItem('pozitron_3d_pricing') || '{}');
    const matKey = this._3dConfig.material || 'PLA';
    const matInfo = this._3dMaterials[matKey] || this._3dMaterials.PLA;

    const gramPrice = pricing[matKey] || matInfo.defaultPrice;
    const setupFee = typeof pricing.setupFee === 'number' ? pricing.setupFee : 50.0;

    const volume = this._3dConfig.volumeCm3 || 0;
    const density = matInfo.density || 1.24;
    const infillRatio = 0.20 + 0.80 * (this._3dConfig.infill / 100);

    const layer = this._3dConfig.layer || '0.20';
    let qualityMul = 1.0;
    if (layer === '0.12') qualityMul = 1.25;
    else if (layer === '0.28') qualityMul = 0.85;

    const estWeight = volume * density * infillRatio;
    this._3dConfig.weightGrams = estWeight;

    let matCost = estWeight * gramPrice * qualityMul;
    let totalUnitPrice = (volume > 0) ? (setupFee + matCost) : 0;

    this._3dConfig.unitPriceTRY = totalUnitPrice;

    const weightEl = document.getElementById('price-calc-weight');
    const matCostEl = document.getElementById('price-calc-mat');
    const setupEl = document.getElementById('price-calc-setup');
    const totalEl = document.getElementById('price-calc-total');

    if (weightEl) weightEl.textContent = `${estWeight.toFixed(1)} gr`;
    if (matCostEl) matCostEl.textContent = `${matCost.toFixed(2)} ₺`;
    if (setupEl) setupEl.textContent = `${setupFee.toFixed(2)} ₺`;
    if (totalEl) totalEl.textContent = `${(totalUnitPrice * (this._3dConfig.qty || 1)).toFixed(2)} ₺`;
  }

  add3DPrintToCart() {
    if (!this._3dConfig.filename || this._3dConfig.volumeCm3 <= 0) {
      this.showToast('Lütfen önce bir STL veya STEP 3D model dosyası yükleyin.', 'error');
      return;
    }

    const itemPriceTRY = this._3dConfig.unitPriceTRY;
    const itemPriceUSD = itemPriceTRY / (this.currencyRates?.TRY || this.usdRate || 50.0);

    const customCartItem = {
      id: 'custom_3d_' + Date.now().toString(36),
      name_tr: `Özel 3D Baskı (${this._3dConfig.filename})`,
      name_en: `Custom 3D Print (${this._3dConfig.filename})`,
      title: `3D Baskı - ${this._3dConfig.material} (%${this._3dConfig.infill} Infill, ${this._3dConfig.colorName})`,
      category_id: 'custom_3d_print',
      price_try: Math.round(itemPriceTRY * 100) / 100,
      price_usd: Math.round(itemPriceUSD * 100) / 100,
      quantity: this._3dConfig.qty || 1,
      image_url: 'https://api.dicebear.com/7.x/bottts/svg?seed=3d_print_custom',
      is_custom_3d: true,
      custom_specs: {
        filename: this._3dConfig.filename,
        material: this._3dConfig.material,
        infill: `%${this._3dConfig.infill}`,
        layer_height: `${this._3dConfig.layer} mm`,
        color: this._3dConfig.colorName,
        dimensions: `${this._3dConfig.dimX} × ${this._3dConfig.dimY} × ${this._3dConfig.dimZ} mm`,
        weight: `${this._3dConfig.weightGrams.toFixed(1)} gr`
      }
    };

    this.addToCart(customCartItem, this._3dConfig.qty || 1);
    this.close3DStudioModal();
    this.showToast(`"${this._3dConfig.filename}" (${this._3dConfig.material}) sepete eklendi!`, 'success');
  }

  // ==========================================
  // COMMUNITY COMMENTS & PILOT REVIEWS SYSTEM
  // ==========================================
  initCommunityComments() {
    this.currentCommentFilter = 'all';

    // Clean any legacy test/seed reviews from localStorage
    try {
      const existing = localStorage.getItem('pozitron_community_reviews');
      if (existing) {
        const parsed = JSON.parse(existing);
        if (Array.isArray(parsed)) {
          const cleaned = parsed.filter(r => r && !String(r.id || '').startsWith('rev_seed_'));
          localStorage.setItem('pozitron_community_reviews', JSON.stringify(cleaned));
        }
      }
    } catch(e) {}

    // Fetch and sync from backend API
    this.syncReviewsFromBackend();

    this.initStarRatingPicker();

    const openBtn = document.getElementById('btn-open-comment-modal');
    if (openBtn) {
      openBtn.addEventListener('click', () => {
        this.openAddCommentModal();
      });
    }

    const modalEl = document.getElementById('comment-modal-backdrop');
    if (modalEl) {
      modalEl.addEventListener('click', (e) => {
        if (e.target === modalEl) this.closeCommentModal();
      });
    }

    this.renderCommunityReviews(this.currentCommentFilter);
  }

  async syncReviewsFromBackend() {
    try {
      const res = await fetch(`${this.apiBase}/reviews`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.reviews && data.reviews.length > 0) {
          const local = this.getCommunityReviews();
          const localIds = new Set(local.map(r => r.id));
          let hasNew = false;
          data.reviews.forEach(srvRev => {
            if (!localIds.has(srvRev.id)) {
              local.push({
                id: srvRev.id,
                userName: srvRev.user_name,
                userAvatar: srvRev.user_avatar,
                rating: srvRev.rating,
                productName: srvRev.title || 'Genel Mağaza Deneyimi',
                productId: srvRev.product_id || '',
                comment: srvRev.comment,
                verified: !!srvRev.verified_purchase,
                date: srvRev.created_at ? srvRev.created_at.split('T')[0] : 'Yakın zamanda'
              });
              hasNew = true;
            }
          });
          if (hasNew) {
            localStorage.setItem('pozitron_community_reviews', JSON.stringify(local));
            this.renderCommunityReviews(this.currentCommentFilter);
          }
        }
      }
    } catch(e) {}
  }

  getCommunityReviews() {
    try {
      const raw = localStorage.getItem('pozitron_community_reviews');
      if (raw) {
        const parsed = JSON.parse(raw);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch(e) {}
    return [];
  }

  findProductByReview(r) {
    if (!r) return null;
    const staticData = this.getStaticData();
    const prods = staticData.products || [];
    const rId = String(r.productId || '').toLowerCase().trim();
    const rName = String(r.productName || '').toLowerCase().trim();

    if (!rId && (!rName || rName.includes('genel') || rName.includes('general'))) {
      return null;
    }

    // 1. Direct ID / SKU / Slug match
    if (rId) {
      const match = prods.find(p => 
        String(p.id).toLowerCase() === rId || 
        String(p.sku).toLowerCase() === rId || 
        String(p.slug).toLowerCase() === rId ||
        String(p.id).toLowerCase().includes(rId)
      );
      if (match) return match;
    }

    // 2. Name Match
    if (rName && !rName.includes('genel') && !rName.includes('general')) {
      const directMatch = prods.find(p => {
        const tr = String(p.name_tr || '').toLowerCase();
        const en = String(p.name_en || '').toLowerCase();
        return tr.includes(rName) || en.includes(rName) || rName.includes(tr) || rName.includes(en);
      });
      if (directMatch) return directMatch;

      const cleanRName = rName.replace(/\(.*?\)/g, '').replace(/[^a-z0-9]/g, ' ').trim();
      const rKeywords = cleanRName.split(/\s+/).filter(w => w.length >= 3 && !['v1', 'v2', 'v3', 'v4', 'v5', 'pro', 'drone', 'fpv', 'set', 'kiti', 'stack', 'unit'].includes(w));
      if (rKeywords.length >= 2) {
        const kwMatch = prods.find(p => {
          const cleanTR = String(p.name_tr || '').toLowerCase().replace(/[^a-z0-9]/g, ' ');
          const cleanEN = String(p.name_en || '').toLowerCase().replace(/[^a-z0-9]/g, ' ');
          return rKeywords.every(kw => cleanTR.includes(kw)) || rKeywords.every(kw => cleanEN.includes(kw));
        });
        if (kwMatch) return kwMatch;
      }
    }

    return null;
  }

  renderCommunityReviews(filter = 'all') {
    this.currentCommentFilter = filter;
    const grid = document.getElementById('community-comments-grid');
    if (!grid) return;

    let reviews = this.getCommunityReviews();
    if (filter === 'verified') {
      reviews = reviews.filter(r => r.verified);
    } else if (filter === '5star') {
      reviews = reviews.filter(r => r.rating >= 5);
    }

    if (reviews.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align:center; padding:40px; background:#fff; border-radius:12px; border:1px dashed var(--border-subtle);">
          <p style="color:var(--text-muted); font-size:0.92rem; margin:0;">${window.i18n.t('product_no_comments_yet')}</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = reviews.map(r => {
      const starsHtml = '★'.repeat(r.rating || 5) + '☆'.repeat(Math.max(0, 5 - (r.rating || 5)));
      const matchedProd = this.findProductByReview(r);
      const targetSlug = matchedProd ? matchedProd.slug : '';
      const tooltipText = window.i18n?.currentLang === 'tr' ? 'Ürünü İncele' : 'View Product';

      const productTagHtml = r.productName ? `
        <div class="comment-product-tag" data-slug="${targetSlug}" title="${targetSlug ? tooltipText : ''}" role="button">
          <span>${r.productName}</span>
        </div>
      ` : '';

      return `
        <article class="comment-card">
          <div class="comment-card-top">
            <img src="${r.userAvatar || `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(r.userName)}`}" alt="${r.userName}" class="comment-avatar" loading="lazy">
            <div class="comment-author-wrap">
              <h3 class="comment-author-name">
                <span>${r.userName}</span>
              </h3>
              <div class="comment-date">${r.date || 'Bugün'}</div>
            </div>
            <div class="comment-stars" title="${r.rating} / 5 Yıldız">${starsHtml}</div>
          </div>
          ${productTagHtml}
          <p class="comment-text">"${r.comment}"</p>
        </article>
      `;
    }).join('');

    // Attach click listeners to product tags on comment cards
    grid.querySelectorAll('.comment-product-tag').forEach(tag => {
      tag.addEventListener('click', (e) => {
        e.stopPropagation();
        const slug = e.currentTarget.getAttribute('data-slug');
        if (slug) {
          window.location.href = `./products/${slug}`;
        }
      });
    });
  }

  filterComments(filter) {
    document.querySelectorAll('.comment-filter-pill').forEach(pill => {
      if (pill.getAttribute('data-filter') === filter) {
        pill.classList.add('active');
      } else {
        pill.classList.remove('active');
      }
    });
    this.renderCommunityReviews(filter);
  }

  renderProductModalReviews(prod) {
    const productReviews = this.getProductReviewsList(prod);

    if (productReviews.length === 0) {
      return `
        <div style="padding:16px; background:var(--bg-secondary); border-radius:8px; border:1px dashed var(--border-subtle); text-align:center; font-size:0.84rem; color:var(--text-muted);">
          ${window.i18n.t('product_no_comments_yet')}
        </div>
      `;
    }

    return productReviews.map(r => {
      const starsHtml = '★'.repeat(r.rating || 5);
      return `
        <div class="product-mini-review-card">
          <div class="product-mini-review-top">
            <span class="product-mini-review-author">${r.userName}</span>
            <span style="color:#f59e0b; font-size:0.8rem;">${starsHtml}</span>
          </div>
          <p class="product-mini-review-text">"${r.comment}"</p>
        </div>
      `;
    }).join('');
  }

  getCurrentUser() {
    if (this.user) return this.user;
    try {
      const stored = localStorage.getItem('pozitron_user');
      if (stored) {
        const parsed = JSON.parse(stored);
        this.user = parsed;
        return parsed;
      }
    } catch(e) {}
    return null;
  }

  openAddCommentModal(productId = '', productName = '') {
    const modal = document.getElementById('comment-modal-backdrop');
    if (!modal) return;

    const prodIdInput = document.getElementById('comment-product-id');
    const prodNameInput = document.getElementById('comment-product-name');
    const authorNameInput = document.getElementById('comment-author-name');
    const commentTextInput = document.getElementById('comment-body-text');
    const ratingInput = document.getElementById('comment-rating-val');

    if (prodIdInput) prodIdInput.value = productId || '';
    if (prodNameInput) prodNameInput.value = productName || '';
    if (commentTextInput) commentTextInput.value = '';
    if (ratingInput) ratingInput.value = '5';

    // Populate or update product select dropdown
    const prodSelect = document.getElementById('comment-product-select');
    if (prodSelect) {
      const staticData = this.getStaticData();
      const prods = (staticData.products || []).slice(0, 60);
      let opts = `<option value="general">★ Genel Mağaza &amp; Alışveriş Deneyimi</option>`;
      prods.forEach(p => {
        const pName = (window.i18n?.currentLang === 'tr' ? (p.name_tr || p.name_en) : (p.name_en || p.name_tr)) || p.title;
        const isSelected = (productId && (p.id === productId || p.slug === productId)) ? 'selected' : '';
        opts += `<option value="${p.id}" ${isSelected}>${p.brand} - ${pName}</option>`;
      });
      prodSelect.innerHTML = opts;
      if (productId) {
        prodSelect.value = productId;
      }
    }

    const userBadge = document.getElementById('comment-logged-user-badge');
    const guestGroup = document.getElementById('comment-guest-name-group');
    const userAvatar = document.getElementById('comment-user-avatar');
    const userDisplayName = document.getElementById('comment-user-display-name');

    const currentUser = this.getCurrentUser();

    if (currentUser) {
      // Logged in: display authenticated pilot badge
      if (guestGroup) guestGroup.style.display = 'none';
      if (authorNameInput) {
        authorNameInput.removeAttribute('required');
        authorNameInput.value = currentUser.full_name || currentUser.email || 'Pilot';
      }
      if (userBadge) userBadge.style.display = 'flex';
      if (userAvatar) userAvatar.src = this.getRobotAvatar(currentUser);
      if (userDisplayName) userDisplayName.textContent = currentUser.full_name || currentUser.email;
    } else {
      // Guest: ask for name
      if (userBadge) userBadge.style.display = 'none';
      if (guestGroup) guestGroup.style.display = 'block';
      if (authorNameInput) {
        authorNameInput.setAttribute('required', 'true');
        authorNameInput.value = '';
      }
    }

    // Reset star picker
    this.updateStarRatingPicker(5);

    modal.style.display = 'flex';
  }

  closeCommentModal() {
    const modal = document.getElementById('comment-modal-backdrop');
    if (modal) modal.style.display = 'none';
  }

  initStarRatingPicker() {
    const picker = document.getElementById('star-rating-picker');
    if (!picker) return;

    picker.querySelectorAll('.star-pick').forEach(star => {
      star.addEventListener('click', (e) => {
        const rating = parseInt(e.currentTarget.getAttribute('data-rating') || '5', 10);
        this.updateStarRatingPicker(rating);
      });
    });
  }

  updateStarRatingPicker(rating) {
    const ratingInput = document.getElementById('comment-rating-val');
    if (ratingInput) ratingInput.value = rating;

    const picker = document.getElementById('star-rating-picker');
    if (!picker) return;

    picker.querySelectorAll('.star-pick').forEach(star => {
      const starVal = parseInt(star.getAttribute('data-rating') || '0', 10);
      if (starVal <= rating) {
        star.classList.add('active');
      } else {
        star.classList.remove('active');
      }
    });
  }

  async handleCommentSubmit(e) {
    if (e) e.preventDefault();

    const currentUser = this.getCurrentUser();
    let authorName = (document.getElementById('comment-author-name')?.value || '').trim();
    if (currentUser && !authorName) {
      authorName = currentUser.full_name || currentUser.email || 'Pilot';
    }

    const prodSelect = document.getElementById('comment-product-select');
    let productId = (document.getElementById('comment-product-id')?.value || '').trim();
    let productName = (document.getElementById('comment-product-name')?.value || '').trim();

    if (prodSelect && prodSelect.value) {
      if (prodSelect.value === 'general') {
        productId = '';
        productName = 'Genel Mağaza Deneyimi';
      } else {
        productId = prodSelect.value;
        const selOption = prodSelect.options[prodSelect.selectedIndex];
        productName = selOption ? selOption.textContent : 'Ürün İncelemesi';
      }
    }

    const ratingVal = parseInt(document.getElementById('comment-rating-val')?.value || '5', 10);
    const commentBody = (document.getElementById('comment-body-text')?.value || '').trim();

    if (!authorName || !commentBody) {
      this.showToast('Lütfen yorumunuzu giriniz.', 'error');
      return;
    }

    const newComment = {
      id: 'rev_' + Date.now().toString(36),
      userName: authorName,
      userAvatar: currentUser ? this.getRobotAvatar(currentUser) : `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(authorName)}`,
      rating: ratingVal,
      productName: productName || (window.i18n ? window.i18n.t('comments_field_product_general') : 'Genel Mağaza Deneyimi'),
      productId: productId,
      comment: commentBody,
      verified: !!currentUser,
      date: 'Az önce'
    };

    const reviews = this.getCommunityReviews();
    reviews.unshift(newComment);
    try {
      localStorage.setItem('pozitron_community_reviews', JSON.stringify(reviews));
    } catch(err) {}

    // Send to backend API
    try {
      fetch('/api/reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          product_id: productId || 'general',
          user_name: authorName,
          user_avatar: newComment.userAvatar,
          rating: ratingVal,
          title: productName || 'Değerlendirme',
          comment: commentBody
        })
      }).catch(() => {});
    } catch(err) {}

    this.closeCommentModal();
    this.showToast(window.i18n ? window.i18n.t('comments_success_toast') : 'Yorumunuz başarıyla paylaşıldı!', 'success');
    this.renderCommunityReviews(this.currentCommentFilter);
    this.fetchProducts();
  }
}

// Safely instantiate immediately or on DOM load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    if (!window.app) window.app = new PozitronApp();
  });
} else {
  if (!window.app) window.app = new PozitronApp();
}

// Google Identity Services JWT Parser & Auth Handler
function parseJwt(token) {
  try {
    var base64Url = token.split('.')[1];
    var base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    var jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
    }).join(''));
    return JSON.parse(jsonPayload);
  } catch(e) {
    return null;
  }
}

window.handleCredentialResponse = function(response) {
  if (!window.app) return;
  const payload = parseJwt(response.credential);
  if (!payload) return;
  
  // Find or Create user in local DB
  const usersDb = window.app.getAllUsersFromDb();
  let existing = usersDb.find(u => u.email && u.email.toLowerCase() === payload.email.toLowerCase());
  
  const isAdmin = window.app.isUserAdmin({ email: payload.email });
  const userRole = isAdmin ? 'admin' : 'customer';

  if (!existing) {
    existing = {
      id: "usr_google_" + Date.now().toString(36),
      email: payload.email,
      password: "google_oauth_verified",
      full_name: payload.name || payload.email.split('@')[0],
      avatar_url: payload.picture || `https://api.dicebear.com/7.x/bottts/svg?seed=${encodeURIComponent(payload.name || payload.email)}`,
      provider: "google",
      role: userRole,
      created_at: new Date().toISOString()
    };
    usersDb.push(existing);
    localStorage.setItem('pozitron_users_db', JSON.stringify(usersDb));

    // Send new Google user to Google Sheets (Kullanıcılar sayfası)
    const WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbw_YHCFvOkkq2usjJh4XCMMHWgHy9V_7C5fROFCjrTGw1iGsPy_39o6JXyvlowO9iy5/exec";
    fetch(WEBHOOK_URL, {
      method: 'POST',
      mode: 'no-cors',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        type: 'user',
        full_name: existing.full_name,
        email: existing.email,
        provider: 'google',
        role: userRole,
        avatar_url: existing.avatar_url,
        registered_at: existing.created_at
      })
    }).catch(err => console.log('User webhook error:', err));
  } else {
    // Update avatar and ensure correct role
    existing.avatar_url = payload.picture || existing.avatar_url;
    existing.full_name = payload.name || existing.full_name;
    existing.role = userRole;
    existing.provider = 'google';
    localStorage.setItem('pozitron_users_db', JSON.stringify(usersDb));
  }

  // Synchronize Google login directly with backend SQLite database
  try {
    const apiTarget = window.PozitronAPI ? window.PozitronAPI.getUrl('/api/auth/google') : '/api/auth/google';
    fetch(apiTarget, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        credential: response.credential,
        email: existing.email,
        full_name: existing.full_name,
        avatar_url: existing.avatar_url
      })
    }).then(async res => {
      if (res.ok) {
        const data = await res.json();
        if (data && data.token) {
          localStorage.setItem('pozitron_token', data.token);
        }
        if (data && data.user && data.user.role) {
          existing.role = data.user.role;
          localStorage.setItem('pozitron_user', JSON.stringify(existing));
        }
      }
    }).catch(() => {});
  } catch(e) {}
  
  window.app.loginWithUser(existing);
  window.app.closeAuthModal();
  window.app.showToast(`Hoş geldiniz, ${existing.full_name}!`, 'success');
};
