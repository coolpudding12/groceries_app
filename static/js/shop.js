const ticked = new Set();
let shopStartTime = null;

let wakeLock = null;
async function requestWakeLock() {
  try {
    wakeLock = await navigator.wakeLock.request('screen');
  } catch (err) {
    console.log('Wake lock not supported:', err);
  }
}
requestWakeLock();

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') {
    requestWakeLock();
  }
});

shopStartTime = sessionStorage.getItem('shopStartTime');

function toggleItem(cb) {
  const li = cb.closest('li');
  li.classList.toggle('done', cb.checked);
  const name = li.querySelector('span').textContent.trim();
  if (cb.checked) {
    ticked.add(name);
  } else {
    ticked.delete(name);
  }
  const allItems = document.querySelectorAll('.shop-item input[type="checkbox"]');
  const allTicked = [...allItems].every(c => c.checked);
  if (allTicked && allItems.length > 0) {
    setTimeout(() => showAllTickedPrompt(), 500);
  }
}

function showAllTickedPrompt() {
  document.getElementById('all-ticked-overlay').style.display = 'flex';
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function isSuspiciousShop(itemsCount, timeSeconds) {
  const avg = timeSeconds / itemsCount;
  if (avg < 3) return true;
  if (timeSeconds < itemsCount * 2) return true;
  return false;
}

function askSuspiciousConfirmation() {
  return new Promise(resolve => {
    const overlay = document.getElementById('suspicious-overlay');
    overlay.style.display = 'flex';
    document.getElementById('suspicious-yes').onclick = () => {
      overlay.style.display = 'none';
      resolve(true);
    };
    document.getElementById('suspicious-no').onclick = () => {
      overlay.style.display = 'none';
      resolve(false);
    };
  });
}

const encouragements = [
  "Nice!", "Legend!", "Speedy!", "On fire!", "Crushing it!",
  "Superstar!", "Swift!", "Nailed it!", "Impressive!", "Zooming!"
];

function getEncouragement() {
  return encouragements[Math.floor(Math.random() * encouragements.length)];
}

async function showResults() {
  const endTime = Date.now();
  const startTime = parseInt(shopStartTime) || endTime;
  const elapsed = Math.floor((endTime - startTime) / 1000);
  const tickedCount = ticked.size;
  const score = tickedCount > 0 ? Math.round((tickedCount * 100000) / Math.max(elapsed / 60, 0.1)) : 0;
  document.getElementById('result-score').textContent = score.toLocaleString();
  document.getElementById('result-time').textContent = `${getEncouragement()} ${tickedCount} items purchased in ${formatTime(elapsed)}`;

  window._shopResult = { score, itemsCount: tickedCount, timeSeconds: elapsed };

  fetch('/leaderboard')
    .then(r => r.json())
    .then(data => {
      const list = document.getElementById('leaderboard-list');
      if (data.scores.length === 0) {
        list.innerHTML = '<p style="font-size:13px;color:var(--muted);text-align:center;">No scores yet — be the first!</p>';
        return;
      }
      list.innerHTML = data.scores.map((s, i) => `
        <div style="display:flex;align-items:center;justify-content:space-between;
                    padding:10px 14px;background:${i === 0 ? '#f0f9f0' : 'var(--cream)'};
                    border-radius:10px;margin-bottom:6px;">
          <span style="font-family:'Righteous',sans-serif;font-size:15px;color:var(--text);">
            ${i + 1}. ${s.arcade_name}
          </span>
          <span style="font-family:'Righteous',sans-serif;font-size:15px;color:var(--green);">
            ${s.score}
          </span>
        </div>
      `).join('');
    });

  document.getElementById('results-overlay').style.display = 'flex';
}

function submitScore() {
  if (document.getElementById('skip-score-checkbox').checked) {
    finishShopping();
    return;
  }
  const arcadeName = document.getElementById('arcade-input').value.trim();
  if (!arcadeName || arcadeName.length < 1) {
    document.getElementById('arcade-input').style.borderColor = 'var(--red)';
    return;
  }
  const { score, itemsCount, timeSeconds } = window._shopResult;
  const form = new FormData();
  form.append('arcade_name', arcadeName);
  form.append('score', score);
  form.append('items_count', itemsCount);
  form.append('time_seconds', timeSeconds);
  fetch('/save_score', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.new_high_score) {
        const scoreEl = document.getElementById('result-score');
        scoreEl.style.transition = 'transform 0.3s';
        scoreEl.style.transform = 'scale(1.3)';
        setTimeout(() => scoreEl.style.transform = 'scale(1)', 300);
        const badge = document.createElement('p');
        badge.textContent = '🏆 New High Score!';
        badge.style.cssText = 'font-family:Righteous,sans-serif;font-size:18px;color:var(--green);text-align:center;margin:0 0 12px;';
        scoreEl.parentElement.insertBefore(badge, scoreEl);
      }
      fetch('/leaderboard')
        .then(r => r.json())
        .then(data => {
          const list = document.getElementById('leaderboard-list');
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
          document.getElementById('arcade-input').style.display = 'none';
          document.querySelector('[onclick="submitScore()"]').style.display = 'none';
          if (window._finishAfterSubmit) {
            window._finishAfterSubmit = false;
            sessionStorage.removeItem('shopStartTime');
            if (ticked.size === 0) {
              window.location.href = '/';
            } else {
              document.getElementById('ticked-input').value = JSON.stringify([...ticked]);
              document.getElementById('clear-form').submit();
            }
          }
        });
    });
}

const randomNames = [
  "supashpr", "mcspeedy", "quickrun", "starshpr", "topshpr",
  "shophero", "winner1", "thegoods", "chckndnr", "number1", "shplegnd"
];

function getRandomName() {
  return randomNames[Math.floor(Math.random() * randomNames.length)];
}

function finishShopping() {
  const arcadeInput = document.getElementById('arcade-input');
  if (arcadeInput && arcadeInput.style.display !== 'none' && !arcadeInput.value.trim() && !document.getElementById('skip-score-checkbox').checked) {
    window._finishAfterSubmit = true;
    arcadeInput.value = getRandomName();
    submitScore();
    return;
  }
  sessionStorage.removeItem('shopStartTime');
  if (ticked.size === 0) {
    window.location.href = '/';
    return;
  }
  document.getElementById('ticked-input').value = JSON.stringify([...ticked]);
  document.getElementById('clear-form').submit();
}

function updateCategory(itemId, itemName, oldCategory, newCategory) {
  const form = new FormData();
  form.append('item_id', itemId);
  form.append('item_name', itemName);
  form.append('old_category', oldCategory);
  form.append('category', newCategory);
  fetch('/update_category', { method: 'POST', body: form })
    .then(r => r.json())
    .then(data => {
      if (data.status === 'ok') {
        location.reload();
      }
    })
    .catch(err => console.error('Error:', err));
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('li[data-id]').forEach(el => {
    attachItemEvents(el);
  });
});

let longPressTimer;

function attachItemEvents(itemEl) {
  itemEl.addEventListener('contextmenu', (e) => {
    e.preventDefault();
    showCategoryMenu(e.clientX, e.clientY, itemEl);
  });
  itemEl.addEventListener('touchstart', () => {
    longPressTimer = setTimeout(() => {
      const rect = itemEl.getBoundingClientRect();
      showCategoryMenu(rect.left, rect.bottom, itemEl);
    }, 500);
  });
  itemEl.addEventListener('touchend', () => clearTimeout(longPressTimer));
  itemEl.addEventListener('touchmove', () => clearTimeout(longPressTimer));
}

function showCategoryMenu(x, y, itemEl) {
  removeCategoryMenu();
  const itemId = itemEl.dataset.id;
  const itemName = itemEl.dataset.name;
  const currentCategory = itemEl.dataset.category;
  const categoryEmojis = {
    "Fruit & Veg": "🥦", "Meat & Fish": "🥩", "Dairy & Eggs": "🧀",
    "Bakery": "🍞", "Pantry": "🥫", "Drinks": "🧃", "Snacks": "🍫",
    "Household": "🧹", "Frozen": "🧊", "Other": "👾"
  };
  const categories = ["Fruit & Veg","Meat & Fish","Dairy & Eggs","Bakery","Pantry","Drinks","Snacks","Household","Frozen","Other"];

  const menu = document.createElement('div');
  menu.id = 'category-menu';
  menu.style.cssText = `position:fixed;background:var(--card);border:2px solid var(--border);border-radius:12px;padding:8px;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,0.15);min-width:160px;`;
  menu.innerHTML = `<p style="font-size:12px;color:var(--muted);margin:0 0 6px 6px;">Move to...</p>`;

  categories.forEach(cat => {
    const btn = document.createElement('button');
    btn.textContent = `${categoryEmojis[cat] || ''} ${cat}`;
    btn.style.cssText = `display:block;width:100%;padding:8px 12px;text-align:left;
      background:${cat === currentCategory ? 'var(--green)' : 'transparent'};
      color:${cat === currentCategory ? 'white' : 'var(--text)'};
      border:none;border-radius:8px;cursor:pointer;font-size:14px;font-family:'DM Sans',sans-serif;`;
    btn.onclick = () => {
      updateCategory(itemId, itemName, currentCategory, cat);
      itemEl.dataset.category = cat;
      removeCategoryMenu();
    };
    menu.appendChild(btn);
  });

  document.body.appendChild(menu);

  const menuHeight = menu.offsetHeight;
  const menuWidth = menu.offsetWidth;
  const windowHeight = window.innerHeight;
  const windowWidth = window.innerWidth;

  let top = y;
  let left = x;
  if (y + menuHeight > windowHeight) top = y - menuHeight;
  if (x + menuWidth > windowWidth) left = x - menuWidth;
  if (top < 0) top = 8;
  if (left < 0) left = 8;

  menu.style.top = top + 'px';
  menu.style.left = left + 'px';

  setTimeout(() => document.addEventListener('click', removeCategoryMenu, { once: true }), 0);
}

function removeCategoryMenu() {
  document.getElementById('category-menu')?.remove();
}

function skipScoring() {
  document.getElementById('results-overlay').style.display = 'none';
  document.getElementById('finish-overlay').style.display = 'flex';
}

// Complete slider
(function() {
  const slider = document.getElementById('complete-slider');
  if (!slider) return;
  const track = slider.parentElement;
  let dragging = false, startX = 0, currentX = 0;
  const maxX = () => track.offsetWidth - slider.offsetWidth - 8;

  function start(x) { dragging = true; startX = x - currentX; slider.style.cursor = 'grabbing'; }

  let completed = false;
  function move(x) {
    if (!dragging || completed) return;
    currentX = Math.min(Math.max(0, x - startX), maxX());
    slider.style.left = (4 + currentX) + 'px';
    const pct = currentX / maxX();
    track.style.background = `linear-gradient(to right, #c8e6c9 ${Math.round(pct*100)}%, #e8f5e9 ${Math.round(pct*100)}%)`;
    if (pct >= 0.95) {
      completed = true; dragging = false;
      slider.style.left = (4 + maxX()) + 'px';
      slider.textContent = '🎉';
      setTimeout(async () => {
        const endTime = Date.now();
        const startTime = parseInt(shopStartTime) || endTime;
        const elapsed = Math.floor((endTime - startTime) / 1000);
        const tickedCount = ticked.size;
        if (isSuspiciousShop(tickedCount, elapsed)) {
          const allTickedOverlay = document.getElementById('all-ticked-overlay');
          if (allTickedOverlay) allTickedOverlay.remove();
          askSuspiciousConfirmation().then(ok => {
            if (!ok) document.getElementById('skip-score-checkbox').checked = true;
            showResults();
          });
        } else {
          console.log('calling showResults');
          setTimeout(() => showResults(), 400);
        }
      }, 400);
    }
  }

  function end() {
    if (!dragging || completed) return;
    dragging = false; slider.style.cursor = 'grab';
    currentX = 0; slider.style.transition = 'left 0.3s';
    slider.style.left = '4px'; track.style.background = '#e8f5e9';
    setTimeout(() => slider.style.transition = '', 300);
  }

  slider.addEventListener('mousedown', e => start(e.clientX));
  window.addEventListener('mousemove', e => move(e.clientX));
  window.addEventListener('mouseup', end);
  slider.addEventListener('touchstart', e => { e.preventDefault(); start(e.touches[0].clientX); }, {passive: false});
  window.addEventListener('touchmove', e => move(e.touches[0].clientX));
  window.addEventListener('touchend', end);
})();

// Finish slider (results overlay)
(function() {
  const slider = document.getElementById('finish-slider');
  if (!slider) return;
  const track = slider.parentElement;
  let dragging = false, startX = 0, currentX = 0;
  const maxX = () => track.offsetWidth - slider.offsetWidth - 8;

  function start(x) { dragging = true; startX = x - currentX; slider.style.cursor = 'grabbing'; }
  function move(x) {
    if (!dragging) return;
    currentX = Math.min(Math.max(0, x - startX), maxX());
    slider.style.left = (4 + currentX) + 'px';
    const pct = currentX / maxX();
    track.style.background = `linear-gradient(to right, #ffe0b2 ${Math.round(pct*100)}%, #fff3e0 ${Math.round(pct*100)}%)`;
    if (pct >= 0.95) {
      dragging = false; slider.style.left = (4 + maxX()) + 'px';
      slider.textContent = '✓'; setTimeout(() => finishShopping(), 400);
    }
  }
  function end() {
    if (!dragging) return;
    dragging = false; slider.style.cursor = 'grab';
    currentX = 0; slider.style.transition = 'left 0.3s';
    slider.style.left = '4px'; track.style.background = '#fff3e0';
    setTimeout(() => slider.style.transition = '', 300);
  }

  slider.addEventListener('mousedown', e => start(e.clientX));
  window.addEventListener('mousemove', e => move(e.clientX));
  window.addEventListener('mouseup', end);
  slider.addEventListener('touchstart', e => { e.preventDefault(); start(e.touches[0].clientX); }, {passive: false});
  window.addEventListener('touchmove', e => move(e.touches[0].clientX));
  window.addEventListener('touchend', end);
})();

// All-ticked slider
(function() {
  const slider = document.getElementById('all-ticked-slider');
  if (!slider) return;
  const track = slider.parentElement;
  let dragging = false, startX = 0, currentX = 0;
  const maxX = () => track.offsetWidth - slider.offsetWidth - 8;

  function start(x) { dragging = true; startX = x - currentX; slider.style.cursor = 'grabbing'; }
  let completed = false;
  function move(x) {
    if (!dragging || completed) return;
    currentX = Math.min(Math.max(0, x - startX), maxX());
    slider.style.left = (4 + currentX) + 'px';
    const pct = currentX / maxX();
    track.style.background = `linear-gradient(to right, #c8e6c9 ${Math.round(pct*100)}%, #e8f5e9 ${Math.round(pct*100)}%)`;
    if (pct >= 0.95) {
      completed = true; dragging = false;
      slider.style.left = (4 + maxX()) + 'px'; slider.textContent = '🎉';
      setTimeout(async () => {
        const endTime = Date.now();
        const startTime = parseInt(shopStartTime) || endTime;
        const elapsed = Math.floor((endTime - startTime) / 1000);
        const tickedCount = ticked.size;
        if (isSuspiciousShop(tickedCount, elapsed)) {
          const ok = await askSuspiciousConfirmation();
          if (!ok) { document.getElementById('skip-score-checkbox').checked = true; return; }
        }
        showResults();
      }, 400);
    }
  }
  function end() {
    if (!dragging || completed) return;
    dragging = false; slider.style.cursor = 'grab';
    currentX = 0; slider.style.transition = 'left 0.3s';
    slider.style.left = '4px'; track.style.background = '#e8f5e9';
    setTimeout(() => slider.style.transition = '', 300);
  }

  slider.addEventListener('mousedown', e => start(e.clientX));
  window.addEventListener('mousemove', e => move(e.clientX));
  window.addEventListener('mouseup', end);
  slider.addEventListener('touchstart', e => { e.preventDefault(); start(e.touches[0].clientX); }, {passive: false});
  window.addEventListener('touchmove', e => move(e.touches[0].clientX));
  window.addEventListener('touchend', end);
})();

// Skip slider (finish overlay)
(function() {
  const slider = document.getElementById('skip-slider');
  if (!slider) return;
  const track = slider.parentElement;
  let dragging = false, startX = 0, currentX = 0;
  const maxX = () => track.offsetWidth - slider.offsetWidth - 8;

  function start(x) { dragging = true; startX = x - currentX; slider.style.cursor = 'grabbing'; }
  function move(x) {
    if (!dragging) return;
    currentX = Math.min(Math.max(0, x - startX), maxX());
    slider.style.left = (4 + currentX) + 'px';
    const pct = currentX / maxX();
    track.style.background = `linear-gradient(to right, #c8e6c9 ${Math.round(pct*100)}%, #e8f5e9 ${Math.round(pct*100)}%)`;
    if (pct >= 0.95) {
      dragging = false; slider.style.left = (4 + maxX()) + 'px';
      slider.textContent = '✓'; setTimeout(() => finishShopping(), 400);
    }
  }
  function end() {
    if (!dragging) return;
    dragging = false; slider.style.cursor = 'grab';
    currentX = 0; slider.style.transition = 'left 0.3s';
    slider.style.left = '4px'; track.style.background = '#e8f5e9';
    setTimeout(() => slider.style.transition = '', 300);
  }

  slider.addEventListener('mousedown', e => start(e.clientX));
  window.addEventListener('mousemove', e => move(e.clientX));
  window.addEventListener('mouseup', end);
  slider.addEventListener('touchstart', e => { e.preventDefault(); start(e.touches[0].clientX); }, {passive: false});
  window.addEventListener('touchmove', e => move(e.touches[0].clientX));
  window.addEventListener('touchend', end);
})();
