document.addEventListener('DOMContentLoaded', () => {
    const refreshBtn = document.getElementById('refresh-btn');
    const updateResultsBtn = document.getElementById('update-results-btn');
    const parleysGrid = document.getElementById('parleys-grid');
    const loader = document.getElementById('loader');
    const lastUpdateSpan = document.getElementById('last-update');
    const dateInput = document.getElementById('scan-date');
    const betAmountInput = document.getElementById('bet-amount');
    const summarySection = document.getElementById('summary-section');
    const tabAll = document.getElementById('tab-all');
    const tabPremium = document.getElementById('tab-premium');
    const tabSafe = document.getElementById('tab-safe');
    const tabDaily = document.getElementById('tab-daily');
    const tabSaved = document.getElementById('tab-saved');

    // Modal elements
    const saveModal = document.getElementById('save-modal');
    const modalBetAmount = document.getElementById('modal-bet-amount');
    const modalConfirm = document.getElementById('modal-confirm');
    const modalCancel = document.getElementById('modal-cancel');
    let parleyToSave = null;

    let currentMode = 'all';
    let currentFedFilter = null;
    let allData = null; // Store full response for local filtering

    // Set default date to today in Bogota timezone
    const now = new Date();
    const formatter = new Intl.DateTimeFormat('en-CA', {
        timeZone: 'America/Bogota',
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
    const today = formatter.format(now);
    dateInput.value = today;

    const fetchParleys = async (forceRefresh = false) => {
        const selectedDate = dateInput.value;
        const betAmount = parseInt(betAmountInput.value) || 10000;

        // Show loader and dim existing grid
        parleysGrid.classList.add('grid-loading');
        summarySection.classList.add('hidden');
        loader.classList.remove('hidden');
        refreshBtn.disabled = true;
        updateResultsBtn.disabled = true;

        try {
            let url = `/api/parleys?date=${selectedDate}&bet_amount=${betAmount}&mode=${currentMode}`;
            if (currentFedFilter) {
                url += `&federation_filter=${currentFedFilter}`;
            }
            if (forceRefresh) {
                url += `&force_refresh=true`;
            }
            if (currentMode === 'daily') {
                url += `&show_all=true`;
            }
            const response = await fetch(url);
            const data = await response.json();
            allData = data; // Store for filtering

            if (!data.parleys || data.parleys.length === 0) {
                parleysGrid.innerHTML = '<p class="error">NO SE ENCONTRARON PARTIDOS PARA ESTE FILTRO</p>';
                summarySection.classList.add('hidden');
            } else {
                parleysGrid.innerHTML = ''; // Clear old grid now that we have data
                renderParleys(data.parleys);
                renderSidebar(data.all_predictions);
                renderSummary(data.parleys, betAmount, data.global_stats);
            }

            const now = new Date();
            lastUpdateSpan.innerText = `ESCANEO COMPLETADO A LAS ${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}`;
            lastUpdateSpan.classList.replace('green', 'cyan');
        } catch (error) {
            console.error('Error fetching parleys:', error);
            parleysGrid.innerHTML = '<p class="error">ERROR AL CONECTAR CON LA INFRAESTRUCTURA DEL AGENTE</p>';
        } finally {
            loader.classList.add('hidden');
            parleysGrid.classList.remove('grid-loading');
            refreshBtn.disabled = false;
            updateResultsBtn.disabled = false;
        }
    };

    const fetchSavedParleys = async () => {
        parleysGrid.classList.add('grid-loading');
        summarySection.classList.add('hidden');
        loader.classList.remove('hidden');

        try {
            const response = await fetch('/api/parleys/saved');
            const data = await response.json();

            parleysGrid.innerHTML = '';
            if (!data.saved_parleys || data.saved_parleys.length === 0) {
                parleysGrid.innerHTML = '<p class="error">AÚN NO HAS GUARDADO NINGÚN PARLEY</p>';
            } else {
                renderParleys(data.saved_parleys, true);
            }
        } catch (error) {
            console.error('Error fetching saved parleys:', error);
            parleysGrid.innerHTML = '<p class="error">ERROR AL CARGAR TUS PARLEYS GUARDADOS</p>';
        } finally {
            loader.classList.add('hidden');
            parleysGrid.classList.remove('grid-loading');
        }
    };

    const renderSummary = (parleys, betAmount, stats) => {
        const totalInvested = parleys.length * betAmount;
        const won = parleys.filter(p => p.status === 'WON');
        const lost = parleys.filter(p => p.status === 'LOST');
        const pending = parleys.filter(p => p.status === 'PENDING');
        const totalReturn = parleys.reduce((sum, p) => sum + (p.status === 'WON' ? p.estimated_return : 0), 0);

        document.getElementById('total-invested').textContent = `$${totalInvested.toLocaleString('es-CO')} COP`;
        document.getElementById('total-return').textContent = `$${totalReturn.toLocaleString('es-CO')} COP`;
        document.getElementById('global-accuracy').textContent = stats ? `${stats.accuracy_percentage}%` : '0%';
        document.getElementById('total-won').textContent = won.length;
        document.getElementById('total-lost').textContent = lost.length;
        document.getElementById('total-pending').textContent = pending.length;

        summarySection.classList.remove('hidden');

        // Render Federation Stats if available
        const fedWrapper = document.getElementById('fed-stats-wrapper');
        const fedList = document.getElementById('fed-stats-list');
        fedList.innerHTML = '';

        if (stats && stats.federations && stats.federations.length > 0) {
            stats.federations.forEach(fed => {
                const badge = document.createElement('div');
                badge.className = 'fed-badge';
                if (currentFedFilter === fed.name) {
                    badge.style.border = '1px solid var(--primary-cyan)';
                    badge.style.boxShadow = '0 0 10px rgba(0, 242, 255, 0.2)';
                } else {
                    badge.style.cursor = 'pointer';
                }

                badge.innerHTML = `
                    <span class="fed-badge-name">${fed.name}</span>
                    <span class="fed-badge-acc">${fed.accuracy}%</span>
                    <span class="fed-badge-sub">${fed.won}W - ${fed.lost}L - ${fed.pending}P</span>
                `;

                badge.addEventListener('click', () => {
                    currentFedFilter = fed.name;
                    fetchParleys();
                });

                fedList.appendChild(badge);
            });
            fedWrapper.classList.remove('hidden');
        } else {
            fedWrapper.classList.add('hidden');
        }
    };

    const renderSidebar = (predictions) => {
        const sidebar = document.getElementById('predictions-sidebar');
        const listContainer = document.getElementById('predictions-list');
        const template = document.getElementById('prediction-item-template');
        const filterBadge = document.getElementById('active-filter-badge');
        const filterText = filterBadge.querySelector('.filter-text');

        listContainer.innerHTML = '';
        sidebar.classList.remove('hidden');

        if (currentFedFilter) {
            filterBadge.classList.remove('hidden');
            filterText.textContent = currentFedFilter;
        } else {
            filterBadge.classList.add('hidden');
        }

        // Local filtering if needed (though API already filters parleys, it's good to keep sidebar and parleys in sync)
        const filtered = currentFedFilter
            ? predictions.filter(p => p.federation === currentFedFilter)
            : predictions;

        filtered.forEach(pred => {
            const node = template.content.cloneNode(true);
            node.querySelector('.row-league').textContent = pred.competition_name;
            node.querySelector('.row-time').textContent = pred.start_date.split('T')[1].substring(0, 5);
            node.querySelector('.row-teams').textContent = `${pred.home_team} vs ${pred.away_team}`;
            node.querySelector('.row-market').textContent = pred.api_market.toUpperCase();
            node.querySelector('.row-prediction').textContent = pred.prediction;
            node.querySelector('.row-odds').textContent = `x${(pred.prediction_odds || 0).toFixed(2)}`;

            const statusEl = node.querySelector('.row-status');
            if (pred.status) {
                statusEl.textContent = pred.status;
                statusEl.classList.add(`result-${pred.status.toLowerCase()}`);
            }

            listContainer.appendChild(node);
        });
    };

    document.getElementById('clear-filter').addEventListener('click', () => {
        currentFedFilter = null;
        fetchParleys();
    });

    const renderParleys = (parleys, isSavedView = false) => {
        const parleyTemplate = document.getElementById('parley-template');
        const selectionTemplate = document.getElementById('selection-template');

        parleys.forEach(parley => {
            const parleyNode = parleyTemplate.content.cloneNode(true);
            const parleyIdText = isSavedView ? `GUARDADO (${parley.timestamp || ''})` : parley.parley_id;
            parleyNode.querySelector('.parley-id').textContent = parleyIdText;
            parleyNode.querySelector('.total-odds').textContent = parley.total_odds.toFixed(2);

            // Status badge
            const statusBadge = parleyNode.querySelector('.parley-status-badge');
            statusBadge.textContent = parley.status;
            statusBadge.classList.add(`status-${parley.status.toLowerCase()}`);

            // Financials
            parleyNode.querySelector('.parley-bet').textContent = parley.bet_amount.toLocaleString('es-CO');
            parleyNode.querySelector('.parley-return').textContent = parley.estimated_return.toLocaleString('es-CO');

            // Card border color based on status
            const card = parleyNode.querySelector('.parley-card');
            if (parley.status === 'WON') card.classList.add('parley-won');
            if (parley.status === 'LOST') card.classList.add('parley-lost');

            // Save button logic
            const saveBtn = parleyNode.querySelector('.parley-save-btn');
            if (isSavedView) {
                saveBtn.parentElement.classList.add('hidden'); // Hide footer in saved view
            } else {
                saveBtn.addEventListener('click', () => {
                    parleyToSave = parley;
                    modalBetAmount.value = parley.bet_amount;
                    saveModal.classList.remove('hidden');
                });
            }

            const selectionsList = parleyNode.querySelector('.selections-list');

            parley.selections.forEach(sel => {
                const selNode = selectionTemplate.content.cloneNode(true);
                selNode.querySelector('.league').textContent = sel.league;
                selNode.querySelector('.match-time').textContent = sel.start_time;
                selNode.querySelector('.teams').textContent = sel.teams;
                selNode.querySelector('.market').textContent = sel.market.toUpperCase();
                selNode.querySelector('.prediction').textContent = sel.selection;
                selNode.querySelector('.selection-odds').textContent = `x${sel.odds.toFixed(2)}`;

                // Score
                const scoreEl = selNode.querySelector('.score');
                if (sel.score) scoreEl.textContent = `[${sel.score}]`;

                // Result badge
                const resultEl = selNode.querySelector('.selection-result');
                resultEl.textContent = sel.result;
                resultEl.classList.add(`result-${sel.result.toLowerCase()}`);

                selectionsList.appendChild(selNode);
            });

            parleysGrid.appendChild(parleyNode);
        });
    };

    // Modal Events
    modalCancel.addEventListener('click', () => {
        saveModal.classList.add('hidden');
        parleyToSave = null;
    });

    modalConfirm.addEventListener('click', async () => {
        if (!parleyToSave) return;
        const amount = parseInt(modalBetAmount.value) || 10000;

        // Update local object
        parleyToSave.bet_amount = amount;
        parleyToSave.estimated_return = amount * parleyToSave.total_odds;

        try {
            const response = await fetch('/api/parleys/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(parleyToSave)
            });
            const result = await response.json();
            if (result.success) {
                saveModal.classList.add('hidden');
                parleyToSave = null;
                // Optional: Show success toast/glow
            }
        } catch (error) {
            console.error('Error saving parley:', error);
        }
    });

    refreshBtn.addEventListener('click', () => {
        currentFedFilter = null;
        fetchParleys();
    });

    function switchTab(mode, activeTab) {
        if (currentMode === mode) return;
        currentMode = mode;

        [tabAll, tabPremium, tabSafe, tabDaily, tabSaved].forEach(t => t.classList.remove('active'));
        activeTab.classList.add('active');

        if (mode === 'saved') {
            fetchSavedParleys();
        } else {
            fetchParleys();
        }
    }

    tabAll.addEventListener('click', () => switchTab('all', tabAll));
    tabPremium.addEventListener('click', () => switchTab('premium', tabPremium));
    tabSafe.addEventListener('click', () => switchTab('safe', tabSafe));
    tabDaily.addEventListener('click', () => switchTab('daily', tabDaily));
    tabSaved.addEventListener('click', () => switchTab('saved', tabSaved));

    // Initial load
    fetchParleys();

    updateResultsBtn.addEventListener('click', () => {
        if (currentMode === 'saved') {
            fetchSavedParleys();
        } else {
            fetchParleys(true);
        }
    });
});
