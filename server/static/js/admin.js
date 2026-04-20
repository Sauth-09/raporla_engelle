/**
 * NetKalkan - Admin Panel JS
 * Handles UI interactions, AJAX requests, and responsive behavior.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Sidebar Toggle (Mobile)
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');

    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', (e) => {
            if (window.innerWidth <= 768 && 
                !sidebar.contains(e.target) && 
                !sidebarToggle.contains(e.target) && 
                sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
            }
        });
    }

    // 2. Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length > 0) {
        setTimeout(() => {
            flashMessages.forEach(msg => {
                msg.style.opacity = '0';
                msg.style.transform = 'translateY(-10px)';
                msg.style.transition = 'all 0.3s ease';
                setTimeout(() => msg.remove(), 300);
            });
        }, 5000);
    }

    // 3. Highlight current nav item based on URL
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        if (link.getAttribute('href') && currentPath.includes(link.getAttribute('href')) && link.getAttribute('href') !== '/admin/') {
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        }
    });

    // 4. AJAX Kill-Switch Toggle (if on dashboard)
    const killSwitchBtn = document.getElementById('killswitch-btn');
    if (killSwitchBtn) {
        // We already have a form submission for this, but if we wanted pure AJAX:
        // killSwitchBtn.addEventListener('click', async (e) => { ... });
    }

    // 5. Form validation enhancements
    const passwordForm = document.getElementById('password-form');
    if (passwordForm) {
        const newPassword = document.getElementById('new_password');
        const confirmPassword = document.getElementById('confirm_password');
        
        passwordForm.addEventListener('submit', (e) => {
            if (newPassword.value !== confirmPassword.value) {
                e.preventDefault();
                alert('Şifreler eşleşmiyor!');
            }
        });
    }

    // 6. Blocklist / Whitelist Type selection helper
    const typeSelects = document.querySelectorAll('select[name="block_type"], select[name="whitelist_type"]');
    const patternInputs = document.querySelectorAll('input[name="pattern"]');
    
    if (typeSelects.length > 0 && patternInputs.length > 0) {
        typeSelects.forEach((select, index) => {
            select.addEventListener('change', (e) => {
                const type = e.target.value;
                const input = patternInputs[index];
                
                switch(type) {
                    case 'url':
                        input.placeholder = 'Örn: youtube.com/watch?v=...';
                        break;
                    case 'channel_id':
                        input.placeholder = 'Örn: UCXXXXXXXXXXXXXXXXXXXX';
                        break;
                    case 'video_id':
                        input.placeholder = 'Örn: dQw4w9WgXcQ';
                        break;
                    case 'keyword':
                    case 'channel_name':
                        input.placeholder = 'Engellenecek kelime veya ad...';
                        break;
                }
            });
        });
    }
});
