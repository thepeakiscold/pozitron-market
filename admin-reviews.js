/* Authenticated moderation of store and product reviews. */
(() => {
  let page = 1;
  let generation = 0;
  const el = id => document.getElementById(id);
  async function request(path, options = {}) {
    const base = typeof getApiBaseUrl === 'function' ? getApiBaseUrl().replace(/\/+$/, '') : '';
    const headers = { Accept: 'application/json' };
    const token = localStorage.getItem('pozitron_token');
    const key = localStorage.getItem('pozitron_admin_key');
    if (token) headers.Authorization = `Bearer ${token}`;
    if (key) headers['X-Admin-Key'] = key;
    if (options.body) headers['Content-Type'] = 'application/json';
    const response = await fetch(`${base}${path}`, { ...options, headers, cache: 'no-store' });
    let data;
    try { data = await response.json(); } catch (_) { throw new Error('Yorum yönetimi için güncel sunucu bağlantısı gerekiyor.'); }
    if (!response.ok) throw new Error(data.error || 'Yorumlar yüklenemedi.');
    return data;
  }
  window.loadAdminReviews = async (requestedPage = 1) => {
    const current = ++generation;
    page = requestedPage;
    el('review-feedback').textContent = 'Yorumlar yükleniyor…';
    el('admin-review-list').replaceChildren();
    el('review-prev').disabled = true;
    el('review-next').disabled = true;
    try {
      const query = new URLSearchParams({ page: String(page), limit: '20', search: el('review-search').value.trim(), status: el('review-status').value });
      const data = await request(`/api/admin/reviews?${query}`);
      if (current !== generation) return;
      if (page > 1 && !data.reviews.length) return window.loadAdminReviews(page - 1);
      el('review-feedback').textContent = data.total ? `${data.total} yorum` : 'Bu görünümde yorum bulunamadı.';
      el('review-page-info').textContent = `Sayfa ${page} / ${Math.max(1, Math.ceil(data.total / 20))}`;
      el('review-prev').disabled = page <= 1;
      el('review-next').disabled = page * 20 >= data.total;
      for (const review of data.reviews) {
        const card = document.createElement('article');
        card.style.cssText = 'border:1px solid var(--border-color,#e2e8f0); border-radius:10px; padding:18px; overflow-wrap:anywhere;';
        const heading = document.createElement('h3');
        heading.textContent = `${review.user_name} · ${review.rating}/5`;
        const details = document.createElement('p');
        const date = new Date(review.created_at);
        details.textContent = `${review.product_name || 'Genel mağaza yorumu'} · ${Number.isNaN(date.getTime()) ? review.created_at : date.toLocaleString('tr-TR')}`;
        const title = document.createElement('strong');
        title.textContent = review.title || '';
        const body = document.createElement('p');
        body.textContent = review.comment;
        body.style.whiteSpace = 'pre-wrap';
        body.style.margin = '12px 0';
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'admin-btn-primary';
        button.textContent = review.deleted_at ? 'Geri Al' : 'Yorumu Sil';
        button.style.background = review.deleted_at ? '#0284c7' : '#b91c1c';
        button.addEventListener('click', async () => {
          const restoring = !!review.deleted_at;
          if (!restoring && !confirm(`${review.user_name} adlı kişinin yorumu yayından kaldırılsın mı? Silinenler bölümünden geri alabilirsiniz.`)) return;
          button.disabled = true;
          try {
            await request(`/api/admin/reviews/${restoring ? 'restore' : 'delete'}`, { method: 'POST', body: JSON.stringify({ id: review.id }) });
            await window.loadAdminReviews(page);
            if (typeof showToast === 'function') showToast(restoring ? 'Yorum yeniden yayımlandı.' : 'Yorum yayından kaldırıldı.', 'success');
          } catch (error) {
            el('review-feedback').textContent = error.message;
            button.disabled = false;
          }
        });
        card.append(heading, details, title, body, button);
        el('admin-review-list').append(card);
      }
    } catch (error) {
      if (current === generation) el('review-feedback').textContent = error.message;
    }
  };
  el('review-search-form').addEventListener('submit', event => { event.preventDefault(); window.loadAdminReviews(1); });
  el('review-prev').addEventListener('click', () => window.loadAdminReviews(page - 1));
  el('review-next').addEventListener('click', () => window.loadAdminReviews(page + 1));
})();
