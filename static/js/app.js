const API = {
  async request(url, options = {}) {
    const headers = new Headers(options.headers || {});
    if (!headers.has('X-CSRF-Token')) headers.set('X-CSRF-Token', document.querySelector('meta[name="csrf-token"]')?.content || '');
    const opts = {...options, headers, credentials:'same-origin'};
    if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type','application/json');
    const res = await fetch(url, opts);
    let body = null;
    try { body = await res.json(); } catch (_) { body = {success:false,message:'Invalid server response',error:'Non-JSON response'}; }
    if (!res.ok || body.success === false) throw new Error(body.error || body.message || `Request failed (${res.status})`);
    return body;
  }
};
window.api = API.request.bind(API);
window.showAlert = function(message,type='success'){
  const el=document.getElementById('global-alert'); if(!el)return;
  el.className=`alert alert-${type}`; el.textContent=message; el.classList.remove('d-none');
  window.clearTimeout(window.__alertTimer); window.__alertTimer=window.setTimeout(()=>el.classList.add('d-none'),4500);
};
window.esc = function(v){return String(v??'').replace(/[&<>'"]/g,s=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[s]));};
window.priorityBadge=function(v){const c=(v||'LOW').toLowerCase();return `<span class="badge priority-${c}">${esc(v||'LOW')}</span>`};
window.statusBadge=function(v){return `<span class="status-badge status-${esc(v||'')}" >${esc((v||'').replaceAll('_',' '))}</span>`};
window.renderPagination=function(containerId,page,pages,load){const el=document.getElementById(containerId);if(!el)return;if(pages<=1){el.innerHTML='';return;}const prev=Math.max(1,page-1),next=Math.min(pages,page+1);el.innerHTML=`<div class="d-flex justify-content-between align-items-center"><button class="btn btn-sm btn-outline-secondary" ${page===1?'disabled':''} data-page="${prev}">Previous</button><span class="small-muted">Page ${page} of ${pages}</span><button class="btn btn-sm btn-outline-secondary" ${page===pages?'disabled':''} data-page="${next}">Next</button></div>`;el.querySelectorAll('button[data-page]').forEach(b=>b.addEventListener('click',()=>load(Number(b.dataset.page))));};
async function initNav(){
  const box=document.getElementById('nav-user'); if(!box)return;
  const t = window.t || ((k, d) => d);
  try{
    const r=await fetch('/api/auth/me',{credentials:'same-origin'});
    const j=await r.json();
    if(j.success){
      const u=j.data;
      const isAdmin=u.role==='ADMIN';
      box.innerHTML=`
        <div class="d-flex align-items-center gap-2 flex-wrap">
          ${!isAdmin && !u.demo ? `
            <a class="btn btn-sm btn-primary d-flex align-items-center gap-1 shadow-sm" href="/citizen/report">
              <i class="bi bi-plus-circle me-1"></i><span>${t('nav_report_issue', 'Report Issue')}</span>
            </a>
          ` : ''}
          <div class="user-status-pill d-flex align-items-center gap-2">
            <span class="status-dot"></span>
            <span class="small fw-semibold">${esc(u.name)}</span>
            <span class="badge ${isAdmin ? 'bg-primary text-white' : 'bg-light text-dark border'} ms-1" style="font-size:0.65rem;">${u.demo ? 'READ-ONLY DEMO' : esc(u.role)}</span>
          </div>
          <a class="btn btn-sm btn-outline-primary" href="${isAdmin ? '/admin/dashboard' : '/citizen/dashboard'}">
            <i class="bi bi-speedometer2 me-1"></i><span>${t('nav_dashboard', 'Dashboard')}</span>
          </a>
          <button id="logout" class="btn btn-sm btn-light text-danger border" aria-label="Log out">
            <i class="bi bi-box-arrow-right me-1"></i><span>${t('nav_logout', 'Logout')}</span>
          </button>
        </div>`;
      document.getElementById('logout').onclick=async()=>{
        try{await api('/api/auth/logout',{method:'POST'});location.href='/';}catch(e){showAlert(e.message,'danger')}
      };
    } else {
      box.innerHTML=`
        <div class="d-flex align-items-center gap-2">
          <a class="btn btn-sm btn-light border" href="/citizen/login"><i class="bi bi-box-arrow-in-right me-1"></i><span>${t('nav_sign_in', 'Sign In')}</span></a>
          <a class="btn btn-sm btn-primary shadow-sm" href="/register"><i class="bi bi-person-plus me-1"></i><span>${t('nav_register', 'Register')}</span></a>
        </div>`;
    }
  }catch(_){
    box.innerHTML=`
      <div class="d-flex align-items-center gap-2">
        <a class="btn btn-sm btn-light border" href="/citizen/login"><i class="bi bi-box-arrow-in-right me-1"></i><span>${t('nav_sign_in', 'Sign In')}</span></a>
        <a class="btn btn-sm btn-primary shadow-sm" href="/register"><i class="bi bi-person-plus me-1"></i><span>${t('nav_register', 'Register')}</span></a>
      </div>`;
  }
}
document.addEventListener('DOMContentLoaded',initNav);
window.addEventListener('languageChanged',initNav);

