(() => {
  const menu = document.querySelector('.menu-toggle');
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.querySelector('.sidebar-overlay');
  const closeMenu = () => { if(sidebar) sidebar.inert=window.innerWidth<=800; sidebar?.classList.remove('is-open'); menu?.setAttribute('aria-expanded','false'); if(overlay) overlay.hidden=true; };
  menu?.addEventListener('click', () => { const open=menu.getAttribute('aria-expanded')!=='true'; sidebar.inert=!open; sidebar.classList.toggle('is-open',open); menu.setAttribute('aria-expanded',String(open)); overlay.hidden=!open; });
  overlay?.addEventListener('click',closeMenu);
  document.addEventListener('keydown',event=>{if(event.key==='Escape'&&sidebar?.classList.contains('is-open')){closeMenu();menu?.focus();}});
  const desktop=window.matchMedia('(min-width:801px)'); if(sidebar) sidebar.inert=!desktop.matches; desktop.addEventListener('change',()=>closeMenu());
  document.querySelectorAll('.notice-close').forEach(button=>button.addEventListener('click',()=>button.closest('.notice').remove()));
  document.querySelectorAll('input[type="password"]').forEach(input=>{
    const wrapper=document.createElement('span');wrapper.className='password-field';input.parentNode.insertBefore(wrapper,input);wrapper.appendChild(input);
    const button=document.createElement('button');button.type='button';button.className='password-toggle';button.textContent='Hiện';button.setAttribute('aria-label','Hiện mật khẩu');button.setAttribute('aria-pressed','false');
    button.addEventListener('click',()=>{const visible=input.type==='password';input.type=visible?'text':'password';button.textContent=visible?'Ẩn':'Hiện';button.setAttribute('aria-label',visible?'Ẩn mật khẩu':'Hiện mật khẩu');button.setAttribute('aria-pressed',String(visible));});wrapper.appendChild(button);
  });
  const searchable=['members','payments','manage_trainers','plans','dashboard','trainer_requests'];
  document.querySelectorAll('table').forEach((table,index)=>{
    table.classList.add('table-cols-'+(table.rows[0]?.cells.length||0)); const wrapper=document.createElement('div');wrapper.className='table-scroll';table.parentNode.insertBefore(wrapper,table);wrapper.appendChild(table);
    const rows=Array.from(table.querySelectorAll('tr')).filter(row=>row.querySelector('td')&&!row.querySelector('td[colspan]'));
    if(!rows.length||!searchable.includes(document.body.dataset.page)||table.closest('details')||table.closest('.auth-main'))return;
    const toolbar=document.createElement('div');toolbar.className='table-toolbar';
    const label=document.createElement('label');label.className='table-search';label.setAttribute('for',`table-search-${index}`);
    const input=document.createElement('input');input.type='search';input.id=`table-search-${index}`;input.placeholder='Tìm trong danh sách…';input.setAttribute('aria-label','Tìm trong danh sách');label.appendChild(input);
    const count=document.createElement('span');count.className='table-result-count';count.setAttribute('aria-live','polite');count.textContent=`${rows.length} mục`;
    const empty=document.createElement('tr');const td=document.createElement('td');td.colSpan=table.rows[0].cells.length;td.textContent='Không tìm thấy kết quả phù hợp.';empty.appendChild(td);empty.hidden=true;(table.tBodies[0]||table).appendChild(empty);
    const normalize=text=>text.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').replace(/Đ/g,'d').toLowerCase();
    input.addEventListener('input',()=>{const query=normalize(input.value.trim());let total=0;rows.forEach(row=>{const match=normalize(row.textContent).includes(query);row.hidden=!match;if(match)total++;});count.textContent=`${total} / ${rows.length} mục`;empty.hidden=total>0;});
    toolbar.append(label,count);wrapper.before(toolbar);
  });
})();
