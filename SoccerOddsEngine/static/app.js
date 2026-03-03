document.addEventListener('DOMContentLoaded', () => {
    const refreshBtn = document.getElementById('refresh-btn');
    const parleysGrid = document.getElementById('parleys-grid');
    const loader = document.getElementById('loader');
    const lastUpdateSpan = document.getElementById('last-update');
    const dateInput = document.getElementById('scan-date');
    const betAmountInput = document.getElementById('bet-amount');
    const summarySection = document.getElementById('summary-section');
    const tabAll = document.getElementById('tab-all');
    const tabPremium = document.getElementById('tab-premium');
    let isPremium = false;

    // Set default date to today
    const today = new Date().toISOString().split('T')[0];
    dateInput.value = today;

    const fetchParleys = async () => {
        const selectedDate = dateInput.value;
        const betAmount = parseInt(betAmountInput.value) || 10000;

        // Show loader
        parleysGrid.innerHTML = '';
        summarySection.classList.add('hidden');
        loader.classList.remove('hidden');
        refreshBtn.disabled = true;

        try {
            const response = await fetch(`/api/parleys?date=${selectedDate}&bet_amount=${betAmount}&premium_only=${isPremium}`);
            const data = await response.json();

            if (!data.parleys || data.parleys.length === 0) {
                parleysGrid.innerHTML = '<p class="error">NO SE ENCONTRARON PARTIDOS PARA ESTE FILTRO</p>';
            } else {
                renderParleys(data.parleys);
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
            refreshBtn.disabled = false;
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
    };

    const renderParleys = (parleys) => {
        const parleyTemplate = document.getElementById('parley-template');
        const selectionTemplate = document.getElementById('selection-template');

        parleys.forEach(parley => {
            const parleyNode = parleyTemplate.content.cloneNode(true);
            parleyNode.querySelector('.parley-id').textContent = parley.parley_id;
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

            const selectionsList = parleyNode.querySelector('.selections-list');

            parley.selections.forEach(sel => {
                const selNode = selectionTemplate.content.cloneNode(true);
                selNode.querySelector('.league').textContent = sel.league;
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

    refreshBtn.addEventListener('click', fetchParleys);

    tabAll.addEventListener('click', () => {
        if (!isPremium) return;
        isPremium = false;
        tabAll.classList.add('active');
        tabPremium.classList.remove('active');
        fetchParleys();
    });

    tabPremium.addEventListener('click', () => {
        if (isPremium) return;
        isPremium = true;
        tabPremium.classList.add('active');
        tabAll.classList.remove('active');
        fetchParleys();
    });

    // Initial load
    fetchParleys();
});
