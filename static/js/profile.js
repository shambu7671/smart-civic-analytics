document.addEventListener('DOMContentLoaded', async () => {
  const el = document.getElementById('profile-data');
  if (!el) return;
  try {
    const response = await api('/api/auth/me');
    const user = response.data;
    el.innerHTML = `<dl class="row"><dt class="col-sm-3">Name</dt><dd class="col-sm-9">${esc(user.name)}</dd><dt class="col-sm-3">Role</dt><dd class="col-sm-9">${esc(user.role)}</dd></dl>`;
  } catch (error) {
    el.innerHTML = `<div class="alert alert-danger">${esc(error.message)}</div>`;
  }
});
