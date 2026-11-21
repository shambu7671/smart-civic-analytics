const loginForm = document.getElementById('login-form');
if (loginForm) loginForm.addEventListener('submit', async event => {
  event.preventDefault();
  const name = document.getElementById('name').value.trim();
  const password = document.getElementById('password').value;
  try {
    const result = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ name, password })
    });
    location.href = result.data.role === 'ADMIN' ? '/admin/dashboard' : '/citizen/dashboard';
  } catch (error) {
    showAlert(error.message, 'danger');
  }
});

document.querySelectorAll('[data-demo-endpoint]').forEach(button => button.addEventListener('click', async () => {
  button.disabled = true;
  try {
    const result = await api(button.dataset.demoEndpoint, {
      method: 'POST',
      body: JSON.stringify({})
    });
    location.href = result.data.role === 'ADMIN' ? '/admin/dashboard' : '/citizen/dashboard';
  } catch (error) {
    showAlert(error.message, 'danger');
    button.disabled = false;
  }
}));

const registerForm = document.getElementById('register-form');
if (registerForm) registerForm.addEventListener('submit', async event => {
  event.preventDefault();
  const name = document.getElementById('name').value.trim();
  const password = document.getElementById('password').value;
  if (password.length < 8) return showAlert('Password must contain at least 8 characters.', 'danger');
  try {
    const result = await api('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, password })
    });
    location.href = result.data.role === 'ADMIN' ? '/admin/dashboard' : '/citizen/dashboard';
  } catch (error) {
    showAlert(error.message, 'danger');
  }
});
