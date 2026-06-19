(() => {
  // Data
  const packages = [
    {id: 'p50', stars:50, price:11500, badge: ''},
    {id: 'p100', stars:100, price:23000, badge: ''},
    {id: 'p250', stars:250, price:57500, badge: ''},
    {id: 'p500', stars:500, price:115000, badge: ''},
    {id: 'p1000', stars:1000, price:230000, badge: 'Mashhur'},
    {id: 'p2500', stars:2500, price:575000, badge: ''},
    {id: 'p5000', stars:5000, price:1150000, badge: ''},
  ];

  // Utils
  const $ = sel => document.querySelector(sel);
  const $$ = sel => Array.from(document.querySelectorAll(sel));
  const fmt = v => v.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");

  // Navigation
  function showPage(id){
    $$('.page').forEach(p=>p.classList.remove('active'));
    const el = $(`#${id}`);
    if(el) el.classList.add('active');
    $$('.nav-btn').forEach(b=>b.classList.toggle('active', b.dataset.target===id));
    window.scrollTo({top:0,behavior:'smooth'});
  }
  document.addEventListener('click', e=>{
    const t = e.target.closest('[data-target]');
    if(t){ showPage(t.dataset.target); }
  });
  $$('.nav-btn').forEach(b => b.addEventListener('click', ()=> showPage(b.dataset.target)));

  // Render packages
  const pkgsEl = $('#packages');
  const pkgSelect = $('#pkgSelect');
  function renderPackages(){
    pkgsEl.innerHTML = '';
    pkgSelect.innerHTML = '<option value="">Paketni tanlang</option>';
    packages.forEach(p => {
      const div = document.createElement('div'); div.className='pkg glass';
      div.innerHTML = `
        <div class="meta">
          <div style="font-weight:700"><i class="fa-solid fa-star" style="color:var(--gold);margin-right:8px"></i>${p.stars} Stars</div>
          <div class="price">${fmt(p.price)} UZS</div>
        </div>
        <div style="display:flex;align-items:center;gap:10px">
          ${p.badge ? `<div class="badge pop">${p.badge}</div>` : ''}
          <button class="btn primary buy-btn" data-id="${p.id}">Sotib olish</button>
        </div>`;
      pkgsEl.appendChild(div);

      const opt = document.createElement('option'); opt.value = p.id; opt.textContent = `${p.stars} yulduz — ${fmt(p.price)} UZS`;
      pkgSelect.appendChild(opt);
    });
  }
  renderPackages();

  // Buy buttons -> prefill order
  document.addEventListener('click', e=>{
    const b = e.target.closest('.buy-btn');
    if(!b) return;
    const id = b.dataset.id; pkgSelect.value = id; showPage('order');
  });

  // Order handling
  const orderForm = $('#orderForm');
  function loadOrders(){
    try{ return JSON.parse(localStorage.getItem('orders')||'[]'); }catch(e){return []}
  }
  function saveOrders(list){ localStorage.setItem('orders', JSON.stringify(list)); }
  function loadDonations(){ try{ return JSON.parse(localStorage.getItem('donations')||'[]'); }catch(e){return []} }
  function saveDonations(list){ localStorage.setItem('donations', JSON.stringify(list)); }

  // Normalize status strings in localStorage to capitalized form
  function normalizeStatuses(){
    let changed = false;
    const orders = loadOrders().map(o=>{ if(!o.status) { o.status='Pending'; changed=true; } const s = (''+o.status).toLowerCase(); if(s==='pending' && o.status!=='Pending'){ o.status='Pending'; changed=true;} if(s==='approved' && o.status!=='Approved'){ o.status='Approved'; changed=true;} if(s==='rejected' && o.status!=='Rejected'){ o.status='Rejected'; changed=true;} return o; });
    const dons = loadDonations().map(d=>{ if(!d.status) { d.status='Pending'; changed=true; } const s = (''+d.status).toLowerCase(); if(s==='pending' && d.status!=='Pending'){ d.status='Pending'; changed=true;} if(s==='approved' && d.status!=='Approved'){ d.status='Approved'; changed=true;} if(s==='rejected' && d.status!=='Rejected'){ d.status='Rejected'; changed=true;} return d; });
    if(changed){ saveOrders(orders); saveDonations(dons); }
  }

  // Convert dataURL to Blob (for sending to backend)
  function dataURLtoBlob(dataurl) {
    const arr = dataurl.split(','), mime = arr[0].match(/:(.*?);/)[1], bstr = atob(arr[1]);
    let n = bstr.length, u8arr = new Uint8Array(n);
    while(n--) u8arr[n] = bstr.charCodeAt(n);
    return new Blob([u8arr], {type:mime});
  }

  // Send order to backend as FormData; backend should forward screenshot to Telegram bot
  function sendOrderToBackend(order){
    try{
      const url = '/api/orders';
      const fd = new FormData();
      fd.append('id', order.id);
      fd.append('user', order.user);
      fd.append('pkg', order.pkg);
      fd.append('price', order.price);
      fd.append('method', order.method);
      if(order.screenshot && order.screenshot.startsWith('data:')){
        const blob = dataURLtoBlob(order.screenshot);
        fd.append('screenshot', blob, `${order.id}.png`);
      }
      return fetch(url, {method:'POST', body: fd}).then(res=>res.ok?res.json():Promise.reject(res));
    }catch(e){ return Promise.reject(e); }
  }

  orderForm.addEventListener('submit', e=>{
    e.preventDefault();
    const user = $('#tgUser').value.trim();
    const pkg = $('#pkgSelect').value;
    const method = $('#payMethod').value;
    const file = $('#payScreenshot').files[0];
    if(!user || !pkg || !method){ alert("Iltimos, barcha maydonlarni to'ldiring"); return; }
    if(!file){ alert("Iltimos, to'lov skrinshotini yuklang (majburiy)"); return; }
    const p = packages.find(x=>x.id===pkg);
    const reader = new FileReader();
    reader.onload = ()=>{
      const orders = loadOrders();
      const order = {id: 'o'+Date.now(), user, pkg:p.stars, price:p.price, method, screenshot: reader.result, status:'Pending', created: Date.now()};
      orders.unshift(order); saveOrders(orders); renderOrders(); updateStats();
      alert("Buyurtma yuborildi — admin tasdig'ini kutmoqda");
      const up = $('#uploadPreview'); if(up) up.innerHTML = '';
      orderForm.reset(); showPage('home');
      // send to backend (if available) which can forward screenshot to Telegram bot, then open t.me link
      sendOrderToBackend(order).catch(()=>{/* ignore */}).finally(()=> notifyAdminOrder(order));
      // save username to profile for convenience
      const profile = loadProfile(); profile.user = user.startsWith('@')?user:user; saveProfile(profile);
      // update profile display (current order status)
      populateProfile();
      // backend stub (ready for Flask integration)
      sendOrderToBackend(order).catch(()=>{/* ignore for now */});
    };
    if(file) reader.readAsDataURL(file); else { reader.onload(); }
  });
  $('#clearOrder').addEventListener('click', ()=> orderForm.reset());
  // clear preview when clearing
  $('#clearOrder').addEventListener('click', ()=> { const up = $('#uploadPreview'); if(up) up.innerHTML=''; });

  // Admin
  const ordersList = $('#ordersList');
  function statusBadge(status){
    if(!status) status='Pending';
    if(status==='Pending') return `<span class="status-badge status-pending"><span class="status-dot"></span>🟡 Pending</span>`;
    if(status==='Approved') return `<span class="status-badge status-approved"><span class="status-dot"></span>🟢 Approved</span>`;
    if(status==='Rejected') return `<span class="status-badge status-rejected"><span class="status-dot"></span>🔴 Rejected</span>`;
    return `<span class="status-badge status-pending"><span class="status-dot"></span>🟡 ${status}</span>`;
  }

  function renderOrders(filter=''){ 
    const list = loadOrders().filter(o => (o.user||'').includes(filter) || o.id.includes(filter));
    const pendingListEl = $('#pendingList');
    const approvedListEl = $('#approvedList');
    const rejectedListEl = $('#rejectedList');
    if(pendingListEl) pendingListEl.innerHTML = '';
    if(approvedListEl) approvedListEl.innerHTML = '';
    if(rejectedListEl) rejectedListEl.innerHTML = '';

    if(list.length===0){
      if(pendingListEl) pendingListEl.innerHTML = '<div class="glass" style="padding:18px">No orders</div>';
      return;
    }

    list.forEach(o=>{
      const el = document.createElement('div'); el.className='order-item glass';
      el.innerHTML = `
        <div style="flex:1">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px">
            <div><strong>${o.user}</strong><div style="color:var(--muted)">${o.id}</div></div>
            <div>${statusBadge(o.status)}</div>
          </div>
          <div style="display:flex;gap:12px;align-items:center;margin-top:8px">
            <div><strong>${o.pkg} yulduz</strong><div style="color:var(--muted)">${fmt(o.price)} UZS</div></div>
            <div style="color:var(--muted);margin-left:auto;text-align:right">${new Date(o.created).toLocaleString()}</div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end">
          <div style="margin-bottom:6px">${o.screenshot?`<img src="${o.screenshot}" style="width:120px;height:86px;border-radius:8px;object-fit:cover;border:1px solid rgba(255,255,255,0.06)"/>`:''}</div>
          <div class="order-actions">
            ${o.status!=='Approved'?`<button class="btn primary approve" data-id="${o.id}">Tasdiqlash</button>`:''}
            ${o.status!=='Rejected'?`<button class="btn outline reject" data-id="${o.id}">Rad etish</button>`:''}
          </div>
        </div>`;

      if(o.status==='Pending' && pendingListEl) pendingListEl.appendChild(el);
      if(o.status==='Approved' && approvedListEl) approvedListEl.appendChild(el);
      if(o.status==='Rejected' && rejectedListEl) rejectedListEl.appendChild(el);
    });
  }

  // Donations rendering
  function renderDonations(filter=''){
    const list = loadDonations().filter(d => (d.user||'').includes(filter) || d.id.includes(filter));
    const pendingEl = $('#pendingDonList');
    const approvedEl = $('#approvedDonList');
    const rejectedEl = $('#rejectedDonList');
    if(pendingEl) pendingEl.innerHTML = '';
    if(approvedEl) approvedEl.innerHTML = '';
    if(rejectedEl) rejectedEl.innerHTML = '';
    if(list.length===0){ if(pendingEl) pendingEl.innerHTML = '<div class="glass" style="padding:18px">Donatsiyalar topilmadi</div>'; return; }
    list.forEach(d=>{
      const el = document.createElement('div'); el.className='order-item glass';
      el.innerHTML = `
        <div style="flex:1">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div><strong>${d.user||'Anonim'}</strong><div style="color:var(--muted)">${d.id}</div></div>
            <div>${statusBadge(d.status)}</div>
          </div>
          <div style="display:flex;gap:12px;align-items:center;margin-top:8px">
            <div><strong>${fmt(d.amount)} UZS</strong><div style="color:var(--muted)">${d.message||''}</div></div>
            <div style="color:var(--muted);margin-left:auto;text-align:right">${new Date(d.created).toLocaleString()}</div>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end">
          <div style="margin-bottom:6px">${d.screenshot?`<img src="${d.screenshot}" style="width:120px;height:86px;border-radius:8px;object-fit:cover;border:1px solid rgba(255,255,255,0.06)"/>`:''}</div>
          <div class="order-actions">
            ${d.status!=='Approved'?`<button class="btn primary approve-don" data-id="${d.id}">Tasdiqlash</button>`:''}
            ${d.status!=='Rejected'?`<button class="btn outline reject-don" data-id="${d.id}">Rad etish</button>`:''}
          </div>
        </div>`;
      if(d.status==='Pending' && pendingEl) pendingEl.appendChild(el);
      if(d.status==='Approved' && approvedEl) approvedEl.appendChild(el);
      if(d.status==='Rejected' && rejectedEl) rejectedEl.appendChild(el);
    });
  }

  // Profile management
  function loadProfile(){ try{ return JSON.parse(localStorage.getItem('profile')||'{}'); }catch(e){return {}} }
  function saveProfile(p){ localStorage.setItem('profile', JSON.stringify(p)); }
  function populateProfile(){
    const profile = loadProfile();
    const user = profile.user || 'guest';
    $('#profileName').textContent = user.startsWith('@')?user:`@${user}`;
    $('#pfName').textContent = user.startsWith('@')?user:`@${user}`;
    $('#pfRef').textContent = profile.ref || (profile.user?('STAR-'+(profile.user.replace(/[^A-Za-z0-9]/g,'').toUpperCase().slice(0,6)||'XXXX')):'STAR-XXXX');

    // user stats
    const orders = loadOrders().filter(o => o.user && (o.user===user || o.user===('@'+user)));
    $('#pfOrdersCount').textContent = orders.length;
    const total = orders.reduce((s,x)=>s+x.price,0);
    $('#pfTotalSpent').textContent = `${fmt(total)} UZS`;
    // Total purchased stars (only Approved)
    const stars = loadOrders().filter(o=>o.user && (o.user===user||o.user===('@'+user)) && o.status==='Approved').reduce((s,x)=>s + (parseInt(x.pkg)||0),0);
    $('#pfStars').textContent = stars;

    // profile summary on home
    $('#profileBalance').textContent = stars;
    $('#profileOrders').textContent = orders.length;
    $('#profileRefs').textContent = profile.refs || 0;

    // render orders for profile
    const listEl = $('#pfOrdersList'); if(listEl){ listEl.innerHTML=''; if(orders.length===0) listEl.innerHTML='<div class="glass" style="padding:10px">No orders</div>'; }
    orders.forEach(o=>{
      const r = document.createElement('div'); r.className='order-item glass'; r.innerHTML = `<div><strong>${o.pkg} Stars</strong><div class="muted">${fmt(o.price)} UZS • ${o.status}</div></div><div>${new Date(o.created).toLocaleString()}</div>`; if(listEl) listEl.appendChild(r);
    });
    // current status = newest order status
    const recent = loadOrders().filter(o=>o.user && (o.user===user || o.user===('@'+user))).sort((a,b)=>b.created - a.created)[0];
    $('#pfCurrentStatus').innerHTML = recent? statusBadge(recent.status) : '<span class="muted">No orders</span>';
  }

  // Edit name & copy referral
  $('#editName')?.addEventListener('click', ()=>{
    const profile = loadProfile();
    const newName = prompt('Enter your Telegram username (with or without @)', profile.user||'');
    if(newName){ profile.user = newName.startsWith('@')?newName:newName; saveProfile(profile); populateProfile(); }
  });
  $('#copyRef2')?.addEventListener('click', ()=>{ navigator.clipboard?.writeText($('#pfRef').textContent); alert('Referal kodi nusxalandi'); });

  // Approve / Reject / View
  document.addEventListener('click', e=>{
    const a = e.target.closest('.approve');
    const r = e.target.closest('.reject');
    const v = e.target.closest('.view-scr');
    const ad = e.target.closest('.approve-don');
    const rd = e.target.closest('.reject-don');
    const vd = e.target.closest('.view-scr-don');
    if(a){ actionOrder(a.dataset.id,'Approved'); }
    if(r){ actionOrder(r.dataset.id,'Rejected'); }
    if(v){ viewScreenshot(v.dataset.id); }
    if(ad){ actionDonation(ad.dataset.id,'Approved'); }
    if(rd){ actionDonation(rd.dataset.id,'Rejected'); }
    if(vd){ viewDonationScreenshot(vd.dataset.id); }
  });

  // File preview for order screenshot
  $('#payScreenshot')?.addEventListener('change', e=>{
    const file = e.target.files[0];
    const preview = $('#uploadPreview');
    preview.innerHTML = '';
    if(!file) return;
    const img = document.createElement('img');
    const meta = document.createElement('div'); meta.className='preview-meta';
    meta.textContent = file.name;
    preview.appendChild(img); preview.appendChild(meta);
    const r = new FileReader(); r.onload = ()=> img.src = r.result; r.readAsDataURL(file);
  });

  // Copy card number
  $('#copyCard')?.addEventListener('click', ()=>{
    const num = document.getElementById('cardNumberDisplay').textContent.replace(/\s/g,'');
    navigator.clipboard?.writeText(num).then(()=> alert('Kart raqami nusxalandi: ' + num));
  });

  // Copy card number on purchase page
  $('#copyCardPurchase')?.addEventListener('click', ()=>{
    const num = document.getElementById('cardNumberDisplayPurchase').textContent.replace(/\s/g,'');
    navigator.clipboard?.writeText(num).then(()=> alert('Kart raqami nusxalandi: ' + num));
  });

  // Backend stub for future Flask integration
  function sendOrderToBackend(order){
    // Example POST to Flask endpoint '/api/orders' (backend must accept JSON)
    // return fetch('/api/orders', {method:'POST',headers:{'Content-Type':'application/json'},body: JSON.stringify(order)});
    return Promise.resolve();
  }

  function actionOrder(id, status){
    const list = loadOrders();
    const o = list.find(x=>x.id===id); if(!o) return; o.status = status; saveOrders(list); renderOrders($('#searchOrders').value.trim()); updateStats();
  }
  function viewScreenshot(id){
    const o = loadOrders().find(x=>x.id===id); if(!o || !o.screenshot) return; const w = window.open(''); w.document.write(`<img src="${o.screenshot}" style="max-width:100%"/>`);
  }

  function viewDonationScreenshot(id){ const d = loadDonations().find(x=>x.id===id); if(!d || !d.screenshot) return; const w=window.open(''); w.document.write(`<img src="${d.screenshot}" style="max-width:100%"/>`); }

  // Stats
  function updateStats(){
    const orders = loadOrders();
    const dons = loadDonations();
    const sales = orders.filter(x=>x.status==='Approved').reduce((s,x)=>s+x.price,0) + dons.filter(d=>d.status==='Approved').reduce((s,d)=>s+ (d.amount||0),0);
    const users = new Set([...orders.map(x=>x.user), ...dons.map(d=>d.user)]).size;
    const pending = orders.filter(x=>x.status==='Pending').length;
    $('#statSales').textContent = `${fmt(sales)} UZS`;
    $('#statUsers').textContent = users;
    $('#statPending').textContent = pending;
  }

  // Search
  // Search orders and donations
  $('#searchOrders').addEventListener('input', e=>{ const q = e.target.value.trim(); renderOrders(q); renderDonations(q); });

  // Referrals
  $('#copyRef').addEventListener('click', ()=>{ navigator.clipboard?.writeText($('#refCode').textContent); alert('Referal kodi nusxalandi'); });

  // Donation submission
  $('#donationForm')?.addEventListener('submit', e=>{
    e.preventDefault();
    const amount = parseInt($('#donAmount').value,10)||0;
    const user = $('#donUser').value.trim();
    const message = $('#donMessage').value.trim();
    const method = $('#donPayMethod').value;
    const file = $('#donScreenshot').files[0];
    if(!amount || !method){ alert('Iltimos, miqdor va to\'lov usulini tanlang'); return; }
    const reader = new FileReader();
    reader.onload = ()=>{
      const dons = loadDonations();
      const don = {id:'d'+Date.now(), user: user||'Anonim', amount, message, method, screenshot: reader.result, status:'Pending', created: Date.now()};
      dons.unshift(don); saveDonations(dons); renderDonations(); updateStats(); alert('Donatsiya yuborildi — adminga habar yuborildi'); document.getElementById('donationForm').reset(); showPage('home');
      notifyAdminDonation(don);
    };
    if(file) reader.readAsDataURL(file); else reader.onload();
  });

  function actionDonation(id, status){ const list = loadDonations(); const d = list.find(x=>x.id===id); if(!d) return; d.status = status; saveDonations(list); renderDonations($('#searchOrders').value.trim()); updateStats(); }

  // Notifications to admin via Telegram link (opens t.me with prefilled message)
  function notifyAdminOrder(order){
    const text = `Yangi buyurtma%0AFoydalanuvchi: ${order.user}%0AYulduzlar: ${order.pkg}%0ASumma: ${fmt(order.price)} UZS%0ATo'lov: ${order.method}%0AId: ${order.id}`;
    window.open(`https://t.me/Ravshanbekov888?text=${text}`,'_blank');
  }
  function notifyAdminDonation(don){
    const text = `Yangi donatsiya%0AFoydalanuvchi: ${don.user}%0AMiqdor: ${fmt(don.amount)} UZS%0AXabar: ${don.message}%0ATo'lov: ${don.method}%0AId: ${don.id}`;
    window.open(`https://t.me/Ravshanbekov888?text=${text}`,'_blank');
  }

  // Init
  document.getElementById('year').textContent = new Date().getFullYear();
  // normalize any legacy status values
  normalizeStatuses();
  populateProfile();
  renderOrders(); renderDonations(); updateStats();
})();
let tg = window.Telegram.WebApp;

tg.expand();

console.log("Mini App ishladi");