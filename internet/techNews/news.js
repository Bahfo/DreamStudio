const UI = {
    root: document.getElementById('root'),
    // We expect Python to provide this global variable
    newsData: window.INJECTED_NEWS || [], 

    renderNav() {
        const nav = document.createElement('nav');
        nav.id = 'nav-container';
        nav.innerHTML = `
            <div class="nav-content">
                <div class="logo" id="logo-home">DreamStudio Articles</div>
                <div class="nav-links">
                    <a href="#" id="link-home">EXcellent TechStacks</a>
                </div>
            </div>
        `;
        this.root.appendChild(nav);
    },

    renderFeed() {
        const oldView = document.getElementById('article-view');
        if (oldView) oldView.remove();

        let feed = document.getElementById('feed-container');
        if (!feed) {
            feed = document.createElement('main');
            feed.id = 'feed-container';
            this.root.appendChild(feed);
        }
        
        feed.classList.remove('hidden');
        feed.innerHTML = ''; 

        this.newsData.forEach((item, index) => {
            const card = document.createElement('div');
            card.className = 'card';
            card.dataset.index = index;
            card.innerHTML = `
                <div class="card-content">
                    <div class="card-tag">${item.tag}</div>
                    <h2 class="card-title">${item.title}</h2>
                    <p class="card-excerpt">${item.excerpt}</p>
                </div>
            `;
            feed.appendChild(card);
        });
    },

    showArticle(index) {
        const item = this.newsData[index];
        const feed = document.getElementById('feed-container');
        if (feed) feed.classList.add('hidden');

        const articleView = document.createElement('div');
        articleView.id = 'article-view';
        articleView.innerHTML = `
            <div class="back-btn" id="go-back">← Back to Feed</div>
            <header class="article-header">
                <div class="card-tag">${item.tag}</div>
                <h1>${item.title}</h1>
                <div class="article-meta">Published in Technical Opinions • 2026</div>
            </header>
            <div class="article-body">
                <p>${item.excerpt}</p>
                <p style="margin-top:20px;">This content was provided directly by the DreamStudio Python Backend.</p>
            </div>
        `;
        this.root.appendChild(articleView);
    },

    handleClicks(e) {
        const card = e.target.closest('.card');
        if (card) {
            this.showArticle(card.dataset.index);
            return;
        }
        if (e.target.id === 'go-back') {
            this.renderFeed();
            return;
        }
        if (e.target.id === 'logo-home' || e.target.id === 'link-home') {
            this.renderFeed();
        }
    },

    init() {
        this.renderNav();
        this.renderFeed(); // No 'await fetch' needed!
        this.root.addEventListener('click', (e) => this.handleClicks(e));
    }
};

UI.init();