const itemCount = parseInt(document.getElementById('main-list').dataset.count);
let lastItemCount = itemCount;

if (sessionStorage.getItem('hintDismissed') === 'true') {
  document.getElementById('shop-hint').style.display = 'none';
} else if (itemCount > 0) {
  document.getElementById('shop-hint').style.display = 'flex';
}

// Auto-dismiss undo bar if present
document.addEventListener('DOMContentLoaded', () => {
  const undoBar = document.getElementById('undo-bar');
  if (undoBar) {
    setTimeout(() => {
      undoBar.style.opacity = '0';
      setTimeout(() => undoBar.style.display = 'none', 500);
      fetch('/dismiss_undo');
    }, 5000);
    history.replaceState(null, '', '/');
  }
});

function previewPhoto(input) {
  const p = document.getElementById('preview');
  if (input.files && input.files[0]) {
    const r = new FileReader();
    r.onload = e => { p.src = e.target.result; p.style.display = 'block'; };
    r.readAsDataURL(input.files[0]);
  }
}

function openMisc() {
  document.getElementById('misc-panel').classList.add('open');
  document.getElementById('misc-overlay').classList.add('open');
}

function closeMisc() {
  document.getElementById('misc-panel').classList.remove('open');
  document.getElementById('misc-overlay').classList.remove('open');
  location.reload();
}

function openUserMenu() {
  document.getElementById('user-menu').style.display = 'block';
  document.getElementById('user-menu-overlay').style.display = 'block';
}

function closeUserMenu() {
  document.getElementById('user-menu').style.display = 'none';
  document.getElementById('user-menu-overlay').style.display = 'none';
}

function openPinSetup() {
  closeUserMenu();
  document.getElementById('pin-setup').style.display = 'block';
  document.getElementById('pin-setup-overlay').style.display = 'block';
}

function closePinSetup() {
  document.getElementById('pin-setup').style.display = 'none';
  document.getElementById('pin-setup-overlay').style.display = 'none';
}

function updateNewPin() {
  document.getElementById('new-pin-val1').textContent = document.getElementById('new-pin-slider1').value;
  document.getElementById('new-pin-val2').textContent = document.getElementById('new-pin-slider2').value;
}

(function() {
  const slider = document.getElementById('shop-slider');
  if (!slider) return;
  const track = slider.parentElement;
  let dragging = false;
  let startX = 0;
  let currentX = 0;
  const maxX = () => track.offsetWidth - slider.offsetWidth - 8;

  function start(x) {
    dragging = true;
    startX = x - currentX;
    slider.style.cursor = 'grabbing';
  }

  function move(x) {
    if (!dragging) return;
    currentX = Math.min(Math.max(0, x - startX), maxX());
    slider.style.left = (4 + currentX) + 'px';
    const pct = currentX / maxX();
    track.style.background = `linear-gradient(to right, #ffe0b2 ${Math.round(pct*100)}%, #fff3e0 ${Math.round(pct*100)}%)`;
    if (pct >= 0.95) {
      dragging = false;
      slider.style.left = (4 + maxX()) + 'px';
      slider.textContent = '🚀';
      sessionStorage.setItem('shopStartTime', Date.now());
      setTimeout(() => window.location.href = '/shop', 400);
    }
  }

  function end() {
    if (!dragging) return;
    dragging = false;
    slider.style.cursor = 'grab';
    currentX = 0;
    slider.style.transition = 'left 0.3s';
    slider.style.left = '4px';
    track.style.background = '#fff3e0';
    setTimeout(() => slider.style.transition = '', 300);
  }

  slider.addEventListener('mousedown', e => start(e.clientX));
  window.addEventListener('mousemove', e => move(e.clientX));
  window.addEventListener('mouseup', end);
  slider.addEventListener('touchstart', e => { e.preventDefault(); start(e.touches[0].clientX); }, {passive: false});
  window.addEventListener('touchmove', e => move(e.touches[0].clientX));
  window.addEventListener('touchend', end);
})();

function savePin() {
  const pin = document.getElementById('new-pin-slider1').value + '-' +
              document.getElementById('new-pin-slider2').value;
  const form = new FormData();
  form.append('action', 'set_pin');
  form.append('pin', pin);
  fetch('/set_pin', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'ok') {
        closePinSetup();
        alert('PIN saved! Re-download your list card to save the new details.');
        location.reload();
      }
    });
}

function openLeaderboard() {
  closeUserMenu();
  fetch('/leaderboard')
    .then(r => r.json())
    .then(data => {
      const list = document.getElementById('home-leaderboard-list');
      if (data.scores.length === 0) {
        list.innerHTML = '<p style="font-size:13px;color:var(--muted);text-align:center;">No scores yet - complete a shop in record time to be the first!</p>';
      } else {
        list.innerHTML = data.scores.map((s, i) => `
          <div style="display:flex;align-items:center;justify-content:space-between;
                      padding:10px 14px;background:${i === 0 ? '#f0f9f0' : 'var(--cream)'};
                      border-radius:10px;margin-bottom:6px;">
            <span style="font-family:'Righteous',sans-serif;font-size:15px;color:var(--text);">
              ${i + 1}. ${s.arcade_name}
            </span>
            <span style="font-family:'Righteous',sans-serif;font-size:15px;color:var(--green);">
              ${s.score.toLocaleString()} pts
            </span>
          </div>
        `).join('');
      }
      document.getElementById('leaderboard-sheet').style.display = 'block';
      document.getElementById('leaderboard-overlay').style.display = 'block';
    });
}

function closeLeaderboard() {
  document.getElementById('leaderboard-sheet').style.display = 'none';
  document.getElementById('leaderboard-overlay').style.display = 'none';
}

function redownloadCard() {
  closeUserMenu();
  const username = PAGE_DATA.displayName;
  const pinDisplay = PAGE_DATA.pinDisplay;
  const showPin = pinDisplay && pinDisplay !== 'None';

  const card = document.createElement('div');
  card.style.cssText = 'background:#fff8f0;border:2px solid #e8d5b0;border-radius:20px;padding:28px 32px;text-align:center;font-family:DM Sans,sans-serif;position:fixed;left:-9999px;top:0;width:300px;';
  card.innerHTML = `
    <p style="font-size:11px;color:#aaa;margin-bottom:6px;letter-spacing:1px;text-transform:uppercase;">Aisle Get It!</p>
    <p style="font-size:11px;color:#aaa;margin-bottom:12px;">grocerylist.devkeo.com</p>
    <div style="border-top:1px solid #e8d5b0;margin:12px 0;"></div>
    <p style="font-size:12px;color:#aaa;margin-bottom:4px;">Username</p>
    <p style="font-size:24px;font-weight:700;color:#3a7d44;margin-bottom:12px;">${username}</p>
    ${showPin ? `
      <div style="border-top:1px solid #e8d5b0;margin:12px 0;"></div>
      <p style="font-size:12px;color:#aaa;margin-bottom:4px;">PIN</p>
      <p style="font-size:28px;font-weight:700;letter-spacing:8px;color:#333;">${pinDisplay}</p>
    ` : ''}
  `;
  document.body.appendChild(card);
  setTimeout(() => {
    html2canvas(card, { backgroundColor: '#fff8f0', scale: 2, width: 300 }).then(canvas => {
      const link = document.createElement('a');
      link.download = username + '-grocery-login.png';
      link.href = canvas.toDataURL('image/png');
      link.click();
      document.body.removeChild(card);
    });
  }, 100);
}

function addItem() {
  const input = document.getElementById('item-input');
  const name = input.value.trim();
  if (!name) return;
  const form = new FormData();
  form.append('item', name);
  const photoInput = document.getElementById('photo-input');
  if (photoInput.files[0]) {
    form.append('photo', photoInput.files[0]);
  }
  fetch('/add', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'ok') {
        lastItemCount += 1;
        const hint = document.getElementById('shop-hint');
        if (sessionStorage.getItem('hintDismissed') !== 'true') {
          hint.style.display = 'flex';
        }
        const mainList = document.getElementById('main-list');
        mainList.dataset.count = parseInt(mainList.dataset.count) + 1;
        const count = parseInt(mainList.dataset.count);
        lastItemCount = count;
        const ul = document.getElementById('main-list');
        const li = document.createElement('li');
        li.style.cssText = 'background:var(--card);border:2px solid var(--border);border-radius:var(--radius);padding:12px 14px;margin-bottom:10px;display:flex;align-items:center;box-shadow:0 2px 8px rgba(0,0,0,0.04);';
        li.innerHTML = `<span style="flex:1;font-size:17px;font-weight:600;">${data.item.name}</span>
          <a href="/delete/${count - 1}" style="color:var(--red);font-size:22px;line-height:1;margin-left:10px;opacity:0.7;">×</a>`;
        ul.appendChild(li);
        input.value = '';
        document.getElementById('photo-input').value = '';
        document.getElementById('preview').style.display = 'none';
        const countEl = document.querySelector('p[style*="text-transform:uppercase"]');
        if (countEl) countEl.textContent = count + ' ITEM' + (count !== 1 ? 'S' : '') + ' ON YOUR LIST';
      } else {
        alert(data.message);
      }
    })
    .catch(err => console.error('Error:', err));
}

function confirmDeleteList() {
  closeUserMenu();
  if (confirm('Are you sure? This will permanently delete your list and data for all users. This cannot be undone.')) {
    fetch('/delete_list', { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          window.location.href = '/login?deleted=1';
        }
      });
  }
}

function clearSelectedMisc() {
  const checked = [...document.querySelectorAll('.misc-checkbox:checked')].map(cb => cb.value);
  if (checked.length === 0) {
    alert('Select some items first.');
    return;
  }
  const form = new FormData();
  form.append('items', JSON.stringify(checked));
  fetch('/misc/clear_selected', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'ok') {
        checked.forEach(name => {
          document.querySelectorAll('.misc-checkbox').forEach(cb => {
            if (cb.value === name) cb.closest('li').remove();
          });
        });
      }
    });
}

function addMiscItem() {
  const input = document.getElementById('misc-input');
  const name = input.value.trim();
  if (!name) return;
  const form = new FormData();
  form.append('misc_item', name);
  fetch('/misc/add', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'ok') {
        const ul = document.querySelector('#misc-panel ul');
        const li = document.createElement('li');
        li.style.cssText = 'background:var(--card);border:2px solid var(--border);border-radius:10px;padding:6px 10px;margin-bottom:6px;display:flex;align-items:center;gap:12px;';
        li.innerHTML = `
          <input type="checkbox" class="misc-checkbox" value="${name}"
            style="width:18px;height:18px;accent-color:var(--green);cursor:pointer;flex-shrink:0;">
          <span style="flex:1;font-size:18px;font-weight:600;">${name}</span>
          <button onclick="deleteMiscItem(this, '${name}')"
            style="background:none;border:none;color:var(--red);font-size:20px;cursor:pointer;line-height:1;padding:0;flex-shrink:0;">×</button>
        `;
        ul.appendChild(li);
        input.value = '';
      }
    });
}

function deleteMiscItem(btn, name) {
  const form = new FormData();
  form.append('items', JSON.stringify([name]));
  fetch('/misc/clear_selected', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'ok') {
        btn.closest('li').remove();
      }
    });
}
