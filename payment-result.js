'use strict';
(() => {
  const receipt = new URLSearchParams(window.location.search).get('r') || '';
  const message = document.getElementById('payment-message');
  const order = document.getElementById('order');
  const button = document.getElementById('refresh-payment');
  let attempts = 0;
  let timer;
  let loading = false;
  async function refresh() {
    if (loading) return;
    loading = true;
    button.disabled = true;
    clearTimeout(timer);
    try {
      if (!/^[0-9a-f]{64}$/.test(receipt)) throw new Error('Ödeme kaydı bulunamadı. Destek ekibimizle iletişime geçin.');
      const response = await fetch('https://api.pozitronmarket.com/api/iyzico/status?r=' + encodeURIComponent(receipt), { cache: 'no-store' });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || 'Ödeme durumu alınamadı.');
      order.textContent = 'Sipariş: ' + result.order_number + ' · ' + Number(result.total_try).toLocaleString('tr-TR', { style: 'currency', currency: 'TRY' });
      if (result.payment_status === 'PAID') {
        message.textContent = result.order_status === 'PAYMENT_REVIEW'
          ? 'Ödemeniz alındı. Siparişiniz destek ekibimizin incelemesini bekliyor. Tekrar ödeme yapmayın.'
          : 'Ödemeniz doğrulandı. Siparişiniz işleme alındı. Teşekkür ederiz.';
        button.hidden = true;
      } else if (result.payment_status === 'FAILED') {
        message.textContent = 'Ödeme tamamlanamadı. Kartınızda tahsilat görüyorsanız tekrar ödeme yapmadan destek ekibimize ulaşın.';
      } else {
        message.textContent = 'Ödeme henüz doğrulanmadı veya iyzico incelemesi sürüyor. Lütfen tekrar ödeme yapmayın.';
        if (++attempts < 12) timer = setTimeout(refresh, 5000);
      }
    } catch (error) {
      message.textContent = error.message;
    } finally {
      loading = false;
      button.disabled = false;
    }
  }
  button.addEventListener('click', refresh);
  refresh();
})();
