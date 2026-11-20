(() => {
    document.querySelectorAll('[data-popup-message]').forEach(notice => {
        if (typeof HTMLDialogElement === 'undefined') return;
        const dialog = document.createElement('dialog');
        dialog.className = 'package-alert';
        dialog.setAttribute('aria-labelledby', 'package-alert-title');
        dialog.setAttribute('aria-describedby', 'package-alert-description');
        const symbol = document.createElement('div');
        symbol.className = 'package-alert-icon';
        symbol.textContent = '!';
        symbol.setAttribute('aria-hidden', 'true');
        const title = document.createElement('h2');
        title.id = 'package-alert-title';
        title.textContent = 'Không thể đăng ký';
        const description = document.createElement('p');
        description.id = 'package-alert-description';
        description.textContent = notice.dataset.popupMessage;
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = 'Đã hiểu';
        button.autofocus = true;
        button.addEventListener('click', () => dialog.close());
        dialog.append(symbol, title, description, button);
        document.body.appendChild(dialog);
        dialog.addEventListener('close', () => {
            dialog.remove();
            document.querySelector('.package-card button:not(:disabled)')?.focus();
        });
        dialog.showModal();
        notice.remove();
    });
    const bell = document.querySelector('.notification-bell');
    document.addEventListener('click', event => {
        if (bell && !bell.contains(event.target)) bell.open = false;
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && bell?.open) {
            bell.open = false;
            bell.querySelector('summary').focus();
        }
    });

    const readAllForm = bell?.querySelector('[data-mark-notifications-read]');
    readAllForm?.addEventListener('submit', async event => {
        event.preventDefault();
        const button = readAllForm.querySelector('button');
        button.disabled = true;
        button.textContent = 'Đang đánh dấu…';
        bell.querySelector('.notification-read-error')?.remove();
        try {
            const response = await fetch(readAllForm.action, {
                method: 'POST',
                body: new FormData(readAllForm),
                credentials: 'same-origin'
            });
            if (!response.ok || new URL(response.url).pathname !== new URL(readAllForm.action).pathname) {
                throw new Error('Cannot mark notifications read');
            }
            bell.querySelector('.notification-badge')?.remove();
            bell.querySelectorAll('.notification-item.unread').forEach(item => item.classList.remove('unread'));
            bell.querySelector('.notification-heading > span').textContent = '0 chưa đọc';
            bell.querySelector('summary').setAttribute('aria-label', 'Thông báo, 0 chưa đọc');
            button.textContent = 'Đã đọc tất cả thông báo';
        } catch {
            const error = document.createElement('p');
            error.className = 'notification-read-error notification-empty';
            error.setAttribute('role', 'alert');
            error.textContent = 'Chưa đánh dấu được thông báo. Vui lòng thử lại.';
            readAllForm.before(error);
            button.textContent = 'Đọc thông báo';
        } finally {
            button.disabled = false;
        }
    });
    const menu = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    const closeMenu = () => {
        if (sidebar) sidebar.inert = window.innerWidth <= 800;
        sidebar?.classList.remove('is-open');
        menu?.setAttribute('aria-expanded', 'false');
        if (overlay) overlay.hidden = true;
        document.body.classList.remove('menu-open');
    };
    menu?.addEventListener('click', () => {
        const open = menu.getAttribute('aria-expanded') !== 'true';
        sidebar.inert = !open;
        sidebar.classList.toggle('is-open', open);
        menu.setAttribute('aria-expanded', String(open));
        overlay.hidden = !open;
        document.body.classList.toggle('menu-open', open);
        if (open) sidebar.querySelector('a')?.focus();
    });
    overlay?.addEventListener('click', () => {
        closeMenu();
        menu?.focus();
    });
    document.addEventListener('keydown', event => {
        if (event.key !== 'Tab' || !sidebar?.classList.contains('is-open')) return;
        const controls = [menu, ...sidebar.querySelectorAll('a[href], button:not(:disabled)')];
        const first = controls[0];
        const last = controls[controls.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && sidebar?.classList.contains('is-open')) {
            closeMenu();
            menu?.focus();
        }
    });
    const desktop = window.matchMedia('(min-width:801px)');
    if (sidebar) sidebar.inert = !desktop.matches;
    desktop.addEventListener('change', () => closeMenu());
    document.querySelectorAll('.notice-close').forEach(button => button.addEventListener('click', () => button.closest('.notice').remove()));
    document.querySelectorAll('input[type="password"]').forEach(input => {
        const wrapper = document.createElement('span');
        wrapper.className = 'password-field';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'password-toggle';
        button.textContent = 'Hiện';
        button.setAttribute('aria-label', 'Hiện mật khẩu');
        button.setAttribute('aria-pressed', 'false');
        button.addEventListener('click', () => {
            const visible = input.type === 'password';
            input.type = visible ? 'text' : 'password';
            button.textContent = visible ? 'Ẩn' : 'Hiện';
            button.setAttribute('aria-label', visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
            button.setAttribute('aria-pressed', String(visible));
        });
        wrapper.appendChild(button);
    });
    const workoutFilter = document.querySelector('[data-workout-filter]');
    if (workoutFilter) {
        const daySelect = workoutFilter.querySelector('select');
        const workouts = [...document.querySelectorAll('[data-workout-days]')];
        const count = workoutFilter.querySelector('[data-workout-count]');
        const empty = document.querySelector('[data-workout-empty]');
        const filterWorkouts = () => {
            const day = daySelect.value;
            let visibleCount = 0;
            for (const workout of workouts) {
                const matches = !day || workout.dataset.workoutDays.split(',').includes(day);
                workout.hidden = !matches;
                if (matches) visibleCount++;
            }
            count.textContent = day ? `${visibleCount} / ${workouts.length} bài tập` : '';
            empty.hidden = visibleCount > 0;
        };
        daySelect.addEventListener('change', filterWorkouts);
        filterWorkouts();
        workoutFilter.hidden = false;
    }

    const searchable = ['members', 'payments', 'manage_trainers', 'plans', 'dashboard', 'trainer_requests', 'manage_receptionists'];
    document.querySelectorAll('table').forEach((table, index) => {
        table.classList.add('table-cols-' + (table.rows[0]?.cells.length || 0));
        const wrapper = document.createElement('div');
        wrapper.className = 'table-scroll';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
        const rows = Array.from(table.querySelectorAll('tr')).filter(row => row.querySelector('td') && !row.querySelector('td[colspan]'));
        if (!rows.length || !searchable.includes(document.body.dataset.page) || table.closest('details') || table.closest('.auth-main')) return;
        const toolbar = document.createElement('div');
        toolbar.className = 'table-toolbar';
        const label = document.createElement('label');
        label.className = 'table-search';
        label.setAttribute('for', `table-search-${index}`);
        const input = document.createElement('input');
        input.type = 'search';
        input.id = `table-search-${index}`;
        input.placeholder = 'Tìm trong danh sách…';
        input.setAttribute('aria-label', 'Tìm trong danh sách');
        label.appendChild(input);
        const count = document.createElement('span');
        count.className = 'table-result-count';
        count.setAttribute('aria-live', 'polite');
        count.textContent = `${rows.length} mục`;
        const empty = document.createElement('tr');
        const td = document.createElement('td');
        td.colSpan = table.rows[0].cells.length;
        td.textContent = 'Không tìm thấy kết quả phù hợp.';
        empty.appendChild(td);
        empty.hidden = true;
        (table.tBodies[0] || table).appendChild(empty);
        const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/Đ/g, 'd').toLowerCase();
        input.addEventListener('input', () => {
            const query = normalize(input.value.trim());
            let total = 0;
            rows.forEach(row => {
                const match = normalize(row.textContent).includes(query);
                row.hidden = !match;
                if (match) total++;
            });
            count.textContent = `${total} / ${rows.length} mục`;
            empty.hidden = total > 0;
        });
        toolbar.append(label, count);
        wrapper.before(toolbar);
    });
})();
