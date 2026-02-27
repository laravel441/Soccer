document.addEventListener('DOMContentLoaded', () => {
    const refreshBtn = document.getElementById('refresh-btn');
    const parleysGrid = document.getElementById('parleys-grid');
    const loader = document.getElementById('loader');
    const lastUpdateSpan = document.getElementById('last-update');

    const fetchParleys = async () => {
        // Show loader
        parleysGrid.innerHTML = '';
        loader.classList.remove('hidden');
        refreshBtn.disabled = true;

        try {
            const response = await fetch('/api/parleys');
            const data = await response.json();

            renderParleys(data);

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

    const renderParleys = (parleys) => {
        const parleyTemplate = document.getElementById('parley-template');
        const selectionTemplate = document.getElementById('selection-template');

        parleys.forEach(parley => {
            const parleyNode = parleyTemplate.content.cloneNode(true);
            parleyNode.querySelector('.parley-id').textContent = parley.parley_id;
            parleyNode.querySelector('.total-odds').textContent = parley.total_odds.toFixed(2);

            const selectionsList = parleyNode.querySelector('.selections-list');

            parley.selections.forEach(sel => {
                const selNode = selectionTemplate.content.cloneNode(true);
                selNode.querySelector('.league').textContent = sel.league;
                selNode.querySelector('.teams').textContent = sel.teams;
                selNode.querySelector('.market').textContent = sel.market.toUpperCase();
                selNode.querySelector('.prediction').textContent = sel.selection;
                selNode.querySelector('.selection-odds').textContent = `x${sel.odds.toFixed(2)}`;

                selectionsList.appendChild(selNode);
            });

            parleysGrid.appendChild(parleyNode);
        });
    };

    refreshBtn.addEventListener('click', fetchParleys);

    // Initial load
    fetchParleys();
});
