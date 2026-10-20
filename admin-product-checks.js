/* Product quality flags are saved to the server, never just the current browser. */
window.setProductChecked = async function (checkbox) {
  const checked = checkbox.checked;
  const label = checkbox.nextElementSibling;
  const previousText = label.textContent;
  checkbox.disabled = true;
  label.textContent = 'Kaydediliyor…';
  try {
    const response = await fetch('/api/admin/products/check', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: checkbox.dataset.id, checked, content_hash: checkbox.dataset.hash })
    });
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error(data.error || 'Kontrol durumu kaydedilemedi.');
    checkbox.checked = data.quality_checked;
    checkbox.dataset.hash = data.quality_hash;
    label.textContent = data.quality_checked ? 'Kontrol edildi' : 'Bekliyor';
    checkbox.closest('label').title = data.quality_notes || 'Henüz kontrol edilmedi.';
    showToast('Kontrol durumu kaydedildi.', 'success');
  } catch (error) {
    checkbox.checked = !checked;
    label.textContent = previousText;
    showToast(error.message || 'Kontrol durumu kaydedilemedi.', 'error');
  } finally {
    checkbox.disabled = false;
  }
};
