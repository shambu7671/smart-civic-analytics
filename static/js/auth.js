const firebaseApiBase = 'https://identitytoolkit.googleapis.com/v1/accounts';

async function firebaseConfig() {
  const response = await fetch('/api/auth/config');
  const body = await response.json();
  if (!response.ok || !body.success) throw new Error(body.error || body.message || 'Firebase is not configured.');
  return body.data;
}

async function firebaseRequest(action, apiKey, payload) {
  const response = await fetch(`${firebaseApiBase}:${action}?key=${encodeURIComponent(apiKey)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const body = await response.json();
  if (!response.ok) {
    const code = body.error?.message || '';
    const messages = {
      EMAIL_EXISTS: 'An account with this email already exists.',
      INVALID_LOGIN_CREDENTIALS: 'Invalid email or password.',
      INVALID_PASSWORD: 'Invalid email or password.',
      USER_DISABLED: 'This account has been disabled.',
      TOO_MANY_ATTEMPTS_TRY_LATER: 'Too many attempts. Please try again later.',
      WEAK_PASSWORD: 'Choose a stronger password.'
    };
    throw new Error(messages[code] || 'Firebase Authentication could not complete the request.');
  }
  return body;
}

const loginForm = document.getElementById('login-form');
if (loginForm) loginForm.addEventListener('submit', async event => {
  event.preventDefault();
  const email = document.getElementById('email').value.trim();
  const password = document.getElementById('password').value;
  try {
    const { api_key: apiKey } = await firebaseConfig();
    const identity = await firebaseRequest('signInWithPassword', apiKey, { email, password, returnSecureToken: true });
    if (!identity.emailVerified) throw new Error('Verify your email address before signing in.');
    const result = await api('/api/auth/login', {
      method: 'POST', body: JSON.stringify({
        id_token: identity.idToken,
        mobile: localStorage.getItem('registration_mobile') || ''
      })
    });
    localStorage.removeItem('registration_mobile');
    location.href = result.data.role === 'ADMIN' ? '/admin/dashboard' : '/citizen/dashboard';
  } catch (error) {
    showAlert(error.message, 'danger');
  }
});

const registerForm = document.getElementById('register-form');
if (registerForm) registerForm.addEventListener('submit', async event => {
  event.preventDefault();
  const name = document.getElementById('name').value.trim();
  const email = document.getElementById('email').value.trim();
  const mobile = document.getElementById('mobile').value.trim();
  const password = document.getElementById('password').value;
  const confirmPassword = document.getElementById('confirm_password').value;
  if (password !== confirmPassword) return showAlert('Passwords do not match.', 'danger');
  try {
    const { api_key: apiKey } = await firebaseConfig();
    const identity = await firebaseRequest('signUp', apiKey, { email, password, returnSecureToken: true });
    await firebaseRequest('update', apiKey, { idToken: identity.idToken, displayName: name, returnSecureToken: true });
    await firebaseRequest('sendOobCode', apiKey, { requestType: 'VERIFY_EMAIL', idToken: identity.idToken });
    localStorage.setItem('registration_mobile', mobile);
    showAlert('Account created. Check your email, verify it, then sign in.', 'success');
    registerForm.reset();
  } catch (error) {
    showAlert(error.message, 'danger');
  }
});
