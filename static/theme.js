(() => {
    const key = 'gymdemo-theme';
    const root = document.documentElement;
    const systemTheme = window.matchMedia('(prefers-color-scheme: dark)');
    const themeColor = document.querySelector('meta[name="theme-color"]');
    const validTheme = value => value === 'light' || value === 'dark' ? value : null;
    let preference = null;

    try {
        preference = validTheme(localStorage.getItem(key));
    } catch {
        // The control still works on this page when browser storage is unavailable.
    }

    const applyTheme = () => {
        const theme = preference ?? (systemTheme.matches ? 'dark' : 'light');
        root.dataset.theme = theme;
        themeColor?.setAttribute('content', theme === 'dark' ? '#151821' : '#ffffff');
        document.querySelectorAll('[data-theme-toggle]').forEach(button => {
            button.setAttribute('aria-pressed', String(theme === 'dark'));
        });
        document.dispatchEvent(new Event('gymdemo:theme-change'));
    };

    applyTheme();

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('[data-theme-toggle]').forEach(button => {
            button.addEventListener('click', () => {
                preference = root.dataset.theme === 'dark' ? 'light' : 'dark';
                try {
                    localStorage.setItem(key, preference);
                } catch {
                    // Keep the in-page preference when saving is unavailable.
                }
                applyTheme();
            });
            button.hidden = false;
        });
        applyTheme();
    });

    systemTheme.addEventListener('change', () => {
        if (!preference) applyTheme();
    });

    window.addEventListener('storage', event => {
        if (event.key === key || event.key === null) {
            preference = validTheme(event.newValue);
            applyTheme();
        }
    });
})();
