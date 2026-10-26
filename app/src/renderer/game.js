/* ===== Игровая логика (renderer) =====
 * Поле 8x8 из зон, выбор зоны с подсветкой, соседние зоны — возможные ходы.
 * Модель данных готова к юнитам: zone = { id, row, col, unit, owner, terrain }
 */

const BOARD_SIZE = 8;
const COLS_LABEL = 'ABCDEFGH';

// --- Состояние игры ---
const state = {
    zones: [],            // массив объектов зон
    selectedZoneId: null, // выбранная зона
    currentPlayer: 1,     // 1 или 2
    turn: 1
};

// --- Генерация поля ---
function createZones() {
    state.zones = [];
    for (let row = 0; row < BOARD_SIZE; row++) {
        for (let col = 0; col < BOARD_SIZE; col++) {
            state.zones.push({
                id: `${COLS_LABEL[col]}${row + 1}`,
                row,
                col,
                unit: null,           // сюда позже встанут юниты
                owner: null,          // 1 / 2 / null — контроль территории
                terrain: 'plain'      // plain | forest | mountain и т.д.
            });
        }
    }
}

function getZone(id) {
    return state.zones.find(z => z.id === id);
}

// Соседние зоны (8 направлений — как ход шахматного кон… то есть короля)
function getNeighbors(zone) {
    const dirs = [-1, 0, 1];
    const result = [];
    for (const dr of dirs) {
        for (const dc of dirs) {
            if (dr === 0 && dc === 0) continue;
            const r = zone.row + dr, c = zone.col + dc;
            if (r >= 0 && r < BOARD_SIZE && c >= 0 && c < BOARD_SIZE) {
                result.push(state.zones[r * BOARD_SIZE + c]);
            }
        }
    }
    return result;
}

// --- Отрисовка DOM ---
const boardEl = document.getElementById('game-board');
const infoEl = document.getElementById('selected-info');

function renderBoard() {
    boardEl.innerHTML = '';
    state.zones.forEach(zone => {
        const el = document.createElement('div');
        el.className = 'zone ' + ((zone.row + zone.col) % 2 === 0 ? 'light' : 'dark');
        el.dataset.id = zone.id;

        const coord = document.createElement('span');
        coord.className = 'coord';
        coord.textContent = zone.id;
        el.appendChild(coord);

        if (zone.owner) el.classList.add('owner-' + zone.owner);

        el.addEventListener('click', () => onZoneClick(zone.id));
        boardEl.appendChild(el);
    });
}

function updateHighlights() {
    document.querySelectorAll('.zone').forEach(el => {
        el.classList.remove('selected', 'move-target');
    });

    if (!state.selectedZoneId) {
        infoEl.textContent = 'Выберите зону на поле';
        return;
    }

    const zone = getZone(state.selectedZoneId);
    const selEl = boardEl.querySelector(`[data-id="${zone.id}"]`);
    if (selEl) selEl.classList.add('selected');

    // Подсветка возможных ходов
    getNeighbors(zone).forEach(n => {
        const el = boardEl.querySelector(`[data-id="${n.id}"]`);
        if (el) el.classList.add('move-target');
    });

    const ownerText = zone.owner ? `Игрок ${zone.owner}` : 'нейтральная';
    infoEl.innerHTML =
        `<span class="badge">Зона ${zone.id}</span>` +
        `<span class="badge">${zone.terrain}</span>` +
        `юнит: ${zone.unit ? zone.unit : 'нет'} · владелец: ${ownerText}`;
}

// --- Выбор зоны ---
function onZoneClick(id) {
    state.selectedZoneId = (state.selectedZoneId === id) ? null : id;
    updateHighlights();
}

function clearSelection() {
    state.selectedZoneId = null;
    updateHighlights();
}

// --- Ходы игроков (задел под будущие механики) ---
function endTurn() {
    state.currentPlayer = state.currentPlayer === 1 ? 2 : 1;
    if (state.currentPlayer === 1) state.turn++;
    clearSelection();
    updatePlayersHud();
}

function updatePlayersHud() {
    const p1 = document.getElementById('card-p1');
    const p2 = document.getElementById('card-p2');
    const t1 = p1.querySelector('.player-tag');
    const t2 = p2.querySelector('.player-tag');

    p1.classList.toggle('active', state.currentPlayer === 1);
    p2.classList.toggle('active', state.currentPlayer === 2);
    t1.textContent = state.currentPlayer === 1 ? 'Ходит…' : 'Ожидание';
    t2.textContent = state.currentPlayer === 2 ? 'Ходит…' : 'Ожидание';
    document.getElementById('turn-number').textContent = state.turn;
}

// --- Управление ---
document.getElementById('btn-end-turn').addEventListener('click', endTurn);
document.getElementById('btn-fullscreen').addEventListener('click', () => {
    if (window.gameAPI) window.gameAPI.toggleFullscreen();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') clearSelection();
    if (e.code === 'Space') { e.preventDefault(); endTurn(); }
    if (e.key === 'F11') {
        e.preventDefault();
        if (window.gameAPI) window.gameAPI.toggleFullscreen();
    }
});

// Версия приложения из preload (если запущено в Electron)
if (window.gameAPI && window.gameAPI.version) {
    document.getElementById('app-version').textContent = 'v' + window.gameAPI.version;
}

// --- Старт ---
createZones();
renderBoard();
updatePlayersHud();
