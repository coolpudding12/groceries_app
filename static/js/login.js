let currentUsername = '';
let currentRaw = '';
let currentPin = '';

const STEP_SUBTITLES = {
  'step-username': 'Enter your list name to get started.',
  'step-pin':      'Welcome back — enter your PIN',
  'step-new-user': 'Create your new grocery list',
};

function showStep(stepId) {
  ['step-username', 'step-pin', 'step-new-user', 'step-card'].forEach(id => {
    document.getElementById(id).style.display = 'none';
  });
  document.getElementById(stepId).style.display = 'block';
  const subtitle = document.getElementById('step-subtitle');
  if (subtitle) subtitle.textContent = STEP_SUBTITLES[stepId] || '';
}

function checkUsername() {
  const raw = document.getElementById('username-input').value.trim();
  if (!raw) {
    showError('username-error', 'Please enter a username.');
    return;
  }
  const form = new FormData();
  form.append('action', 'check_username');
  form.append('username', raw);
  fetch('/login', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'error') {
        showError('username-error', data.message);
      } else if (data.status === 'has_pin') {
        currentRaw = raw;
        currentUsername = raw;
        document.getElementById('display-name-pin').textContent = raw;
        showStep('step-pin');
      } else if (data.status === 'login_ok') {
        window.location.href = '/';
      } else if (data.status === 'new_user') {
        currentRaw = raw;
        document.getElementById('display-name-new').textContent = raw;
        showStep('step-new-user');
      }
    });
}

function verifyPin() {
  const form = new FormData();
  form.append('action', 'verify_pin');
  form.append('username', currentRaw);
  form.append('pin', document.getElementById('login-pin-value') ?
    document.getElementById('login-pin-value').value :
    document.getElementById('pin-slider1').value + '-' + document.getElementById('pin-slider2').value);
  fetch('/login', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'login_ok') {
        window.location.href = '/';
      } else {
        document.getElementById('pin-error').style.display = 'block';
      }
    });
}

function createAccount() {
  const usePIN = document.getElementById('pin-toggle').checked;
  const pin = usePIN ?
    document.getElementById('create-slider1').value + '-' + document.getElementById('create-slider2').value
    : '';
  const form = new FormData();
  form.append('action', 'create_account');
  form.append('username', currentRaw);
  if (usePIN) form.append('pin', pin);
  fetch('/login', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'created') {
        document.getElementById('card-username').textContent = data.username;
        if (data.has_pin) {
          document.getElementById('card-pin').textContent = data.pin_display;
          document.getElementById('card-pin-section').style.display = 'block';
        } else {
          document.getElementById('card-pin-section').style.display = 'none';
        }
        showStep('step-card');
      }
    });
}

function togglePinSection() {
  const section = document.getElementById('create-pin-section');
  section.style.display = document.getElementById('pin-toggle').checked ? 'block' : 'none';
}

function updateLoginPin() {
  const v1 = document.getElementById('pin-slider1').value;
  const v2 = document.getElementById('pin-slider2').value;
  document.getElementById('pin-val1').textContent = v1;
  document.getElementById('pin-val2').textContent = v2;
}

function updateCreatePin() {
  const v1 = document.getElementById('create-slider1').value;
  const v2 = document.getElementById('create-slider2').value;
  document.getElementById('create-val1').textContent = v1;
  document.getElementById('create-val2').textContent = v2;
}

function resetToStart() {
  document.getElementById('username-input').value = '';
  showStep('step-username');
}

function showError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.style.display = 'block';
}

function downloadCard() {
  const card = document.getElementById('login-card');
  html2canvas(card, { backgroundColor: '#fff8f0', scale: 2 }).then(canvas => {
    const link = document.createElement('a');
    link.download = currentRaw + '-grocery-login.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
  });
}
