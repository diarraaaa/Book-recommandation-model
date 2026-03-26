// User is identified server-side via session cookie — no client-side user_id needed.

document.addEventListener("DOMContentLoaded", () => {
    
    // Elements
    const submitBtn = document.getElementById('submit-upload');
    const uploadStatus = document.getElementById('upload-status');
    const uploadSection = document.getElementById('upload-section');
    const appDash = document.getElementById('app-dash');
    const exploreList = document.getElementById('explore-list');
    const ratingsList = document.getElementById('ratings-list');
    const genresContainer = document.getElementById('genres-container');

    // Tabs
    const navTabs = document.querySelectorAll('.nav-btn');
    const views = document.querySelectorAll('.view-section');

    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            navTabs.forEach(t => t.classList.remove('active'));
            views.forEach(v => v.classList.remove('active', 'hidden'));
            
            tab.classList.add('active');
            const target = tab.getAttribute('data-target');
            views.forEach(v => {
                if(v.id === target) v.classList.remove('hidden');
                else v.classList.add('hidden');
            });
            if(target === 'explore-view') loadHomeBooks();
            if(target === 'ratings-view') loadMyRatings();
            if(target === 'genres-view') loadGenres();
        });
    });

    // --- System Status Check ---
    async function initApp() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();
            if(data.ready) {
                uploadSection.classList.add('hidden');
                appDash.classList.remove('hidden');
                loadHomeBooks();
            } else {
                submitBtn.disabled = false;
                submitBtn.classList.remove('hidden');
            }
        } catch(e) { console.error("Error checking status:", e); }
    }
    initApp();

    // --- Train Logic ---
    submitBtn.addEventListener('click', async () => {
        submitBtn.disabled = true;
        uploadStatus.classList.remove('hidden');

        try {
            const response = await fetch('/api/train', { method: 'POST' });
            const result = await response.json();
            
            uploadStatus.classList.add('hidden');
            if(response.ok) {
                uploadSection.innerHTML = '<div class="init-content"><i class="fa-solid fa-check-circle init-icon" style="color:var(--success);"></i><h2>Engine Online</h2><p>Mapping complete.</p></div>';
                setTimeout(() => {
                    uploadSection.classList.add('hidden');
                    appDash.classList.remove('hidden');
                    loadHomeBooks();
                }, 1500);
            } else {
                alert("Training failed: " + result.error);
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error(error);
            alert("An error occurred during training.");
            uploadStatus.classList.add('hidden');
            submitBtn.disabled = false;
        }
    });

    // --- Modal Logic ---
    const bookModal = document.getElementById('book-modal');
    const modalBody = document.getElementById('modal-body-content');
    
    document.getElementById('close-modal').onclick = () => {
        bookModal.classList.add('hidden');
    };

    function openBookModal(book) {
        const coverLink = book.cover_link ? book.cover_link : `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='450' viewBox='0 0 300 450'%3E%3Crect width='300' height='450' fill='%231a1c23'/%3E%3Ctext x='150' y='225' text-anchor='middle' fill='%238b5cf6' font-size='48' font-family='sans-serif'%3E%F0%9F%93%96%3C/text%3E%3C/svg%3E`;
        const safeTitle = book.title.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const safeAuthor = book.author.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        
        let interactionUI = '';
        if (book.user_note !== undefined) {
             let noteStr = book.user_note > 0 ? "You Liked This <i class='fa-solid fa-heart'></i>" : "You Disliked This <i class='fa-solid fa-thumbs-down'></i>";
             interactionUI = `
                <div class="interaction-bar" style="margin-top:2rem; justify-content:center; flex-direction:column; gap:1rem; align-items:center;">
                    <span style="font-size:1.2rem; font-weight:bold; color:var(--text-main);">${noteStr}</span>
                    <button class="btn secondary-btn" style="background:rgba(239, 68, 68, 0.2); border-color:var(--danger); color:var(--danger);" onclick="handleRemoveInter(this, ${book.id})"><i class="fa-solid fa-trash"></i> Remove Rating</button>
                </div>
             `;
        } else {
             interactionUI = `
                <div class="interaction-bar" style="margin-top:2rem; justify-content:center; gap:2rem;">
                    <button class="rate-btn dislike" title="Dislike" onclick="handleInter(this, ${book.id}, -1.0, '${safeTitle}', '${safeAuthor}')">
                        <i class="fa-solid fa-thumbs-down"></i>
                    </button>
                    <button class="rate-btn like" title="Like" onclick="handleInter(this, ${book.id}, 1.0, '${safeTitle}', '${safeAuthor}')">
                        <i class="fa-solid fa-heart"></i>
                    </button>
                </div>
             `;
        }

        modalBody.innerHTML = `
            <img src="${coverLink}" class="modal-bg-blur" onerror="this.style.display='none'">
            <div class="modal-split">
                <div>
                    <img src="${coverLink}" class="modal-cover" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'300\' height=\'450\' viewBox=\'0 0 300 450\'%3E%3Crect width=\'300\' height=\'450\' fill=\'%231a1c23\'/%3E%3Ctext x=\'150\' y=\'225\' text-anchor=\'middle\' fill=\'%238b5cf6\' font-size=\'48\' font-family=\'sans-serif\'%3E%F0%9F%93%96%3C/text%3E%3C/svg%3E'">
                    ${interactionUI}
                </div>
                <div class="modal-info">
                    <h2>${book.title}</h2>
                    <h3>By ${book.author}</h3>
                    <div class="modal-meta">
                        <span class="meta-tag"><i class="fa-solid fa-tag"></i> ${book.main_genre || 'Novel'}</span>
                    </div>
                    <div class="modal-desc">${book.description}</div>
                </div>
            </div>
        `;
        bookModal.classList.remove('hidden');
    }

    // --- Data Fetching and Updating UI ---
    function createBookCard(book, renderType = 'explore') {
        const card = document.createElement('div');
        card.className = 'book-card';
        card.style.cursor = 'pointer';
        
        // Modal spawn trigger
        card.onclick = (e) => {
            // Prevent if clicking interactions
            if(e.target.closest('.interaction-bar')) return;
            openBookModal(book);
        }

        const coverLink = book.cover_link ? book.cover_link : `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='450' viewBox='0 0 300 450'%3E%3Crect width='300' height='450' fill='%231a1c23'/%3E%3Ctext x='150' y='225' text-anchor='middle' fill='%238b5cf6' font-size='48' font-family='sans-serif'%3E%F0%9F%93%96%3C/text%3E%3C/svg%3E`;
        const genre = book.main_genre ? book.main_genre : 'Novel';
        const safeTitle = book.title.replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const safeAuthor = book.author.replace(/'/g, "\\'").replace(/"/g, '&quot;');

        let interactionHTML = '';
        if(renderType === 'explore') {
            interactionHTML = `
                <div class="interaction-bar">
                    <button class="rate-btn dislike" title="Dislike" onclick="handleInter(this, ${book.id}, -1.0, '${safeTitle}', '${safeAuthor}')">
                        <i class="fa-solid fa-thumbs-down"></i>
                    </button>
                    <button class="rate-btn like" title="Like" onclick="handleInter(this, ${book.id}, 1.0, '${safeTitle}', '${safeAuthor}')">
                        <i class="fa-solid fa-heart"></i>
                    </button>
                    <button class="rate-btn bookmark" title="Add to read list" onclick="this.style.color='#3b82f6';">
                        <i class="fa-solid fa-bookmark"></i>
                    </button>
                </div>
            `;
        } else if(renderType === 'recommend') {
            interactionHTML = `
                <div class="interaction-bar" style="justify-content: center;">
                    <span style="color: var(--accent-primary); font-size:1rem; font-weight:600;"><i class="fa-solid fa-star"></i> AI Top Pick</span>
                </div>
            `;
        } else if(renderType === 'rating') {
            let noteStr = book.user_note > 0 ? `<i class="fa-solid fa-heart" style="color:var(--success);"></i> Liked` 
                        : `<i class="fa-solid fa-thumbs-down" style="color:var(--danger);"></i> Disliked`;
            interactionHTML = `
                <div class="interaction-bar" style="justify-content: center;">
                    <span style="font-size:1rem; font-weight:600;">${noteStr}</span>
                </div>
            `;
        }
        
        card.innerHTML = `
            <div class="cover-wrapper">
                <span class="genre-badge">${genre}</span>
                <img src="${coverLink}" alt="${book.title}" class="book-cover" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'300\' height=\'450\' viewBox=\'0 0 300 450\'%3E%3Crect width=\'300\' height=\'450\' fill=\'%231a1c23\'/%3E%3Ctext x=\'150\' y=\'225\' text-anchor=\'middle\' fill=\'%238b5cf6\' font-size=\'48\' font-family=\'sans-serif\'%3E%F0%9F%93%96%3C/text%3E%3C/svg%3E'">
            </div>
            <div class="book-info">
                <div class="book-title" title="${book.title}">${book.title}</div>
                <div class="book-author">${book.author}</div>
                <div class="book-desc">${book.description}</div>
                ${interactionHTML}
            </div>
        `;
        return card;
    }

    // Exported function for inline onclick
    window.handleInter = async function(btn, bookId, note, title, author) {
        const targetElement = btn.closest('.book-card') || btn.closest('.modal-content');
        if(targetElement) {
            targetElement.style.opacity = '0.5';
            targetElement.style.pointerEvents = 'none';
        }

        try {
            await fetch('/api/interact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    book_id: bookId,
                    note: note,
                    title: title,
                    author: author
                })
            });
            // Show feedback
            if(targetElement.classList.contains('book-card')){
                targetElement.innerHTML = `<div style="padding: 2rem; text-align:center; margin:auto; flex:1; display:flex; flex-direction:column; justify-content:center;">
                    <i class="fa-solid fa-check-circle" style="font-size:3rem; color:var(--success); margin-bottom:1rem;"></i>
                    <h3 style="margin-bottom:0.5rem;">Recorded</h3>
                    <p style="color:var(--text-muted); font-size:0.9rem;">The AI will use this to improve your recommendations.</p>
                </div>`;
                setTimeout(() => {
                    targetElement.remove();
                }, 2500);
            } else {
                // If in modal
                bookModal.classList.add('hidden');
                targetElement.style.opacity = '1';
                targetElement.style.pointerEvents = 'auto';
                
                // No full refresh — the feed stays stable until next tab switch or reload
            }
        } catch(e) {
            console.error(e);
            if(targetElement) {
                targetElement.style.opacity = '1';
                targetElement.style.pointerEvents = 'auto';
            }
        }
    }

    window.handleRemoveInter = async function(btn, bookId) {
        const targetElement = btn.closest('.modal-content');
        if(targetElement) {
            targetElement.style.opacity = '0.5';
            targetElement.style.pointerEvents = 'none';
        }

        try {
            await fetch('/api/remove_interact', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    book_id: bookId
                })
            });
            
            bookModal.classList.add('hidden');
            targetElement.style.opacity = '1';
            targetElement.style.pointerEvents = 'auto';
            
            // Refresh active list so UI reflects the change seamlessly
            const activeTab = document.querySelector('.nav-btn.active').getAttribute('data-target');
            if (activeTab === 'ratings-view') loadMyRatings();
            if (activeTab === 'explore-view') loadHomeBooks();
            
        } catch(e) {
            console.error(e);
            if(targetElement) {
                targetElement.style.opacity = '1';
                targetElement.style.pointerEvents = 'auto';
            }
        }
    }

    async function loadHomeBooks() {
        if (document.getElementById('search-input').value.trim() !== '') return;
        
        try {
            exploreList.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 4rem;"><div class="spinner" style="margin:auto;"></div></div>';
            const res = await fetch('/api/home');
            const books = await res.json();
            
            if (document.getElementById('search-input').value.trim() !== '') return;
            
            exploreList.innerHTML = '';
            // Display 500 books
            books.forEach(book => {
                exploreList.appendChild(createBookCard(book, 'explore'));
            });
        } catch(e) { console.error(e); }
    }

    async function loadMyRatings() {
        try {
            ratingsList.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 4rem;"><div class="spinner" style="margin:auto;"></div></div>';
            const res = await fetch('/api/my_ratings');
            const books = await res.json();
            
            ratingsList.innerHTML = '';
            if(!books || books.length === 0) {
                ratingsList.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 4rem;"><p>Your library is empty. Go Exploring and start liking books to build your history!</p></div>';
                return;
            }
            
            books.forEach(book => {
                ratingsList.appendChild(createBookCard(book, 'rating'));
            });
        } catch(e) { console.error(e); }
    }

    async function loadGenres() {
        if(genresContainer.innerHTML !== '') return; // Cached
        
        try {
            genresContainer.innerHTML = '<div style="text-align:center; padding: 4rem;"><div class="spinner" style="margin:auto;"></div></div>';
            const res = await fetch('/api/genres');
            const genresData = await res.json();
            
            genresContainer.innerHTML = '';
            
            for(const [genre, books] of Object.entries(genresData)) {
                if(books.length === 0) continue;
                
                const section = document.createElement('div');
                section.className = 'genre-section';
                
                const title = document.createElement('h3');
                title.textContent = genre;
                section.appendChild(title);
                
                const row = document.createElement('div');
                row.className = 'genre-row';
                
                books.forEach(book => {
                    row.appendChild(createBookCard(book, 'explore'));
                });
                
                section.appendChild(row);
                genresContainer.appendChild(section);
            }
        } catch(e) { console.error(e); }
    }

    // --- Search Logic ---
    const searchInput = document.getElementById('search-input');
    let searchTimeout = null;

    searchInput.addEventListener('input', (e) => {
        const homeTab = document.querySelector('[data-target="explore-view"]');
        if (!homeTab.classList.contains('active')) {
            navTabs.forEach(t => t.classList.remove('active'));
            views.forEach(v => v.classList.remove('active', 'hidden'));
            
            homeTab.classList.add('active');
            views.forEach(v => {
                if(v.id === 'explore-view') v.classList.remove('hidden');
                else v.classList.add('hidden');
            });
        }
        
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            const query = e.target.value.trim();
            if (query === '') {
                loadHomeBooks();
                return;
            }
            exploreList.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 4rem;"><div class="spinner" style="margin:auto;"></div></div>';
            
            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
                const books = await res.json();
                
                exploreList.innerHTML = '';
                if(books.length === 0) {
                    exploreList.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 4rem;"><p>No books found matching your search.</p></div>';
                    return;
                }
                books.forEach(book => exploreList.appendChild(createBookCard(book, 'explore')));
            } catch(e) { console.error(e); }
        }, 400); // 400ms debounce
    });

    // ─── Card Entrance Animation (IntersectionObserver) ───
    const cardObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry, i) => {
            if (entry.isIntersecting) {
                // Stagger: each card gets a tiny delay based on its position in the batch
                const card = entry.target;
                const siblings = [...card.parentElement.children];
                const idx = siblings.indexOf(card) % 8; // stagger up to 8
                card.style.animationDelay = `${idx * 0.06}s`;
                card.classList.add('visible');
                cardObserver.unobserve(card);
            }
        });
    }, { threshold: 0.08 });

    // Re-observe on DOM mutation (cards are injected dynamically)
    const gridObserver = new MutationObserver(() => {
        document.querySelectorAll('.book-card:not(.visible)').forEach(card => {
            cardObserver.observe(card);
        });
    });

    // Watch all grid/row containers
    [exploreList, ratingsList, genresContainer].forEach(container => {
        if (container) {
            gridObserver.observe(container, { childList: true, subtree: true });
        }
    });

    // ─── Navbar scroll shadow ───
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 10);
    }, { passive: true });
});
