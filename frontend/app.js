document.addEventListener('DOMContentLoaded', () => {
    // --- UI ELEMENTS ---
    const navLinks = document.querySelectorAll('.nav-link');
    const views = document.querySelectorAll('.view');
    const youtubeUrlInput = document.getElementById('youtubeUrl');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultsCard = document.getElementById('resultsSection');
    const summaryContent = document.getElementById('summaryContent');
    const chatBox = document.getElementById('chatMessages');
    const userQueryInput = document.getElementById('userQuery');
    const sendBtn = document.getElementById('sendBtn');
    const loader = document.getElementById('globalLoader');
    const langToggle = document.getElementById('langToggle');

    let currentLanguage = localStorage.getItem('vm_lang') || 'en';
    let currentVideoId = null;

    // --- NAVIGATION ---
    function switchView(viewName) {
        views.forEach(v => {
            v.classList.add('hidden');
            v.classList.remove('active-view');
        });
        navLinks.forEach(link => link.classList.remove('active'));

        const targetView = document.getElementById(viewName + 'View');
        const targetLink = document.getElementById(viewName + 'Link');

        if (targetView) {
            targetView.classList.remove('hidden');
            targetView.classList.add('active-view');
        }
        if (targetLink) targetLink.classList.add('active');
        
        if (viewName === 'history') renderHistory();
    }

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.getAttribute('data-view');
            switchView(view);
        });
    });

    // --- BILINGUAL ENGINE ---
    const translations = {
        en: {
            heroTitle: "Transcribe. Analyze. Master.",
            heroSub: "Unlock summaries, insights, and chat-based reasoning for any YouTube video.",
            analyzeBtn: "Analyze Video",
            dashboardTitle: "Deep Intelligence",
            chatTitle: "Chat with Video",
            historyTitle: "Analysis Vault",
            settingsTitle: "App Settings",
            chatPlaceholder: "Ask anything about the video..."
        },
        hi: {
            heroTitle: "ट्रांसक्राइब. विश्लेषण. मास्टर.",
            heroSub: "किसी भी यूट्यूब वीडियो के लिए सारांश, अंतर्दृष्टि और चैट-आधारित तर्क अनलॉक करें।",
            analyzeBtn: "वीडियो विश्लेषण करें",
            dashboardTitle: "गहन बुद्धिमत्ता",
            chatTitle: "वीडियो के साथ चैट",
            historyTitle: "विश्लेषण वॉल्ट",
            settingsTitle: "ऐप सेटिंग्स",
            chatPlaceholder: "वीडियो के बारे में कुछ भी पूछें..."
        }
    };

    function updateLanguageUI() {
        document.querySelectorAll('[data-translate]').forEach(el => {
            const key = el.getAttribute('data-translate');
            if (translations[currentLanguage][key]) {
                el.innerText = translations[currentLanguage][key];
            }
        });
        document.querySelectorAll('[data-translate-placeholder]').forEach(el => {
            const key = el.getAttribute('data-translate-placeholder');
            if (translations[currentLanguage][key]) {
                el.placeholder = translations[currentLanguage][key];
            }
        });
        langToggle.innerText = currentLanguage === 'en' ? 'EN | हिंदी' : 'हिंदी | EN';
    }

    langToggle.addEventListener('click', () => {
        currentLanguage = currentLanguage === 'en' ? 'hi' : 'en';
        localStorage.setItem('vm_lang', currentLanguage);
        updateLanguageUI();
    });

    // --- CORE ANALYSIS LOGIC ---
    async function analyzeVideo() {
        const url = youtubeUrlInput.value.trim();
        if (!url) return alert('Please enter a YouTube URL');

        summaryContent.innerHTML = '';
        if (chatBox) chatBox.innerHTML = '';
        loader.classList.remove('hidden');
        resultsCard.classList.add('hidden');
        
        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    url: url,
                    language: currentLanguage === 'en' ? 'English' : 'Hindi',
                    response_length: document.getElementById('prefLength').value || 'Medium'
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Analysis failed');
            }

            const data = await response.json();
            currentVideoId = data.video_id;
            
            summaryContent.innerHTML = marked.parse(data.analysis);
            resultsCard.classList.remove('hidden');
            saveToHistory(data.video_id, data.analysis);
            resultsCard.scrollIntoView({ behavior: 'smooth' });

        } catch (err) {
            console.error('VideoMind Error:', err);
            alert(`⚠️ Error: ${err.message}\n\nTip: The first analysis takes 1-2 mins to download AI models.`);
        } finally {
            loader.classList.add('hidden');
        }
    }

    analyzeBtn.addEventListener('click', analyzeVideo);

    // --- CHAT LOGIC ---
    async function sendMessage() {
        const query = userQueryInput.value.trim();
        if (!query || !currentVideoId) return;

        appendMessage('user', query);
        userQueryInput.value = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_id: currentVideoId,
                    question: query,
                    language: currentLanguage === 'en' ? 'English' : 'Hindi'
                })
            });

            const data = await response.json();
            if (response.ok) {
                appendMessage('ai', data.answer);
            } else {
                appendMessage('ai', "Error: " + data.detail);
            }
        } catch (err) {
            appendMessage('ai', "Could not connect to AI server.");
        }
    }

    function appendMessage(role, text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${role}-message`;
        msgDiv.innerText = text;
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    sendBtn.addEventListener('click', sendMessage);
    userQueryInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });

    // --- HISTORY MANAGEMENT ---
    function saveToHistory(id, analysis) {
        let history = JSON.parse(localStorage.getItem('vm_history') || '[]');
        const cleanPreview = analysis.replace(/[#*`]/g, '').substring(0, 100) + '...';
        
        const newItem = {
            id: id,
            preview: cleanPreview,
            full: analysis,
            date: new Date().toLocaleString()
        };
        
        history = history.filter(item => item.id !== id);
        history.unshift(newItem);
        localStorage.setItem('vm_history', JSON.stringify(history.slice(0, 20)));
    }

    function renderHistory() {
        const historyGrid = document.getElementById('historyGrid');
        const history = JSON.parse(localStorage.getItem('vm_history') || '[]');
        
        if (history.length === 0) {
            historyGrid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; opacity: 0.5;">No history found yet.</p>';
            return;
        }

        historyGrid.innerHTML = history.map(item => `
            <div class="history-card glass-card">
                <div class="history-info">
                    <span class="history-tag">ANALYSIS</span>
                    <h4>Video: ${item.id}</h4>
                    <p>${item.preview}</p>
                    <span class="history-date">${item.date}</span>
                </div>
                <div class="history-actions">
                    <button class="history-reload-btn" onclick="loadFromHistory('${item.id}')">
                        <i class="fas fa-play"></i> Open Analysis
                    </button>
                    <button class="history-del-btn" onclick="deleteHistory('${item.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }

    window.loadFromHistory = (id) => {
        const history = JSON.parse(localStorage.getItem('vm_history') || '[]');
        const item = history.find(i => i.id === id);
        if (item) {
            currentVideoId = id;
            summaryContent.innerHTML = marked.parse(item.full);
            resultsCard.classList.remove('hidden');
            switchView('dashboard');
            resultsCard.scrollIntoView({ behavior: 'smooth' });
        }
    };

    window.deleteHistory = (id) => {
        let history = JSON.parse(localStorage.getItem('vm_history') || '[]');
        history = history.filter(item => item.id !== id);
        localStorage.setItem('vm_history', JSON.stringify(history));
        renderHistory();
    };

    window.clearAllHistory = () => {
        if (confirm('Are you sure? This will delete all analysis data.')) {
            localStorage.removeItem('vm_history');
            renderHistory();
        }
    };

    // Initial Load
    updateLanguageUI();
});
