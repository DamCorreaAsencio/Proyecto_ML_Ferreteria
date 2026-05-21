// Dashboard Multi-Vista - Ferretería Costos

const token = localStorage.getItem('token');
if (!token) window.location.href = '/static/login.html';

document.getElementById('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem('token');
    window.location.href = '/static/login.html';
});

let optionsData = {};
let selectedProducts = [];
let chartInstance, temporalChartInstance, variationChartInstance, topChartInstance;

// Función para generar multiplicadores estacionales específicos por producto y marca
function getSeasonalMultipliers(productName, marca, categoria) {
    const basePattern = {
        1: 0.85, 2: 0.90, 3: 1.05, 4: 1.10, 5: 1.15, 6: 1.10,
        7: 1.05, 8: 1.00, 9: 1.05, 10: 1.10, 11: 1.15, 12: 1.20
    };
    const combinedKey = `${productName}_${marca}_${categoria}`;
    const hash = combinedKey.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    const seed = (hash % 100) / 100;
    const productPattern = {};
    for (let month = 1; month <= 12; month++) {
        const variation = (Math.sin(seed * month * 2) * 0.15);
        productPattern[month] = Math.max(0.7, Math.min(1.3, basePattern[month] + variation));
    }
    return productPattern;
}

// Initialize Charts immediately
function initCharts() {
    try {
        const ctx = document.getElementById('demandChart').getContext('2d');
        chartInstance = new Chart(ctx, {
            type: 'line',
            data: { labels: [], datasets: [{ label: 'Demanda Estimada (Unidades)', data: [], backgroundColor: 'rgba(59, 130, 246, 0.1)', borderColor: '#3B82F6', borderWidth: 2, fill: true, tension: 0.4, pointBackgroundColor: '#3B82F6', pointBorderColor: '#fff', pointBorderWidth: 2, pointRadius: 5, pointHoverRadius: 7 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#9CA3AF' } } }, scales: { y: { beginAtZero: true, grid: { color: '#374151' }, ticks: { color: '#9CA3AF' } }, x: { grid: { display: false }, ticks: { color: '#9CA3AF' } } } }
        });
    } catch (e) {
        console.error("Error initializing main chart", e);
    }
}

// Init Application
async function init() {
    // 1. Initialize charts first (so they are visible even if data fails)
    initCharts();

    // 2. Set default date
    try {
        const dateInput = document.getElementById('inpHistFecha');
        if (dateInput) dateInput.valueAsDate = new Date();
    } catch (e) { console.error(e); }

    // 3. Fetch Options
    try {
        const resp = await fetch('/options', { headers: { 'Authorization': `Bearer ${token}` } });
        if (resp.status === 401) window.location.href = '/static/login.html';
        if (resp.ok) {
            optionsData = await resp.json();
            populateSelect('selProducto', optionsData.producto);
            populateSelect('selProducto', optionsData.producto);
            updateDependentOptions();
            populateHistorySelects();
        } else {
            console.error("Failed to load options");
        }
    } catch (e) {
        console.error("Error loading options", e);
    }
}

// Navigation Logic
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        const target = item.dataset.target;
        if (!target) return;

        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        item.classList.add('active');

        document.getElementById('section-dashboard').style.display = 'none';
        document.getElementById('section-products').style.display = 'none';
        document.getElementById('section-settings').style.display = 'none';

        const section = document.getElementById(`section-${target}`);
        if (section) section.style.display = 'block';

        if (target === 'products') loadHistory();
        if (target === 'settings') loadSettingsMetrics();
    });
});

// Dashboard Tabs Logic
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const view = btn.dataset.view;
        if (!view) return;

        // Update active tab
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        // Hide all views
        document.querySelectorAll('.view-container').forEach(v => v.style.display = 'none');

        // Show selected view
        const viewContainer = document.getElementById(`view-${view}`);
        if (viewContainer) viewContainer.style.display = 'block';

        // Initialize charts for the view if needed
        if (view === 'temporal' && !temporalChartInstance) { initTemporalChart(); populateTemporalSelects(); }
        else if (view === 'variation' && !variationChartInstance) { initVariationChart(); populateVariationSelects(); }
        else if (view === 'top' && !topChartInstance) initTopChart();
    });
});

// Products Section Logic
async function loadHistory() {
    const tbody = document.getElementById('historyTableBody');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5" style="padding:1rem; text-align:center; color:#9CA3AF;">Cargando...</td></tr>';

    try {
        const resp = await fetch('/history?limit=50', { headers: { 'Authorization': `Bearer ${token}` } });
        const data = await resp.json();

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="padding:1rem; text-align:center; color:#9CA3AF;">No hay registros recientes.</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(row => `
            <tr style="border-bottom:1px solid #374151;">
                <td style="padding:0.75rem;">${row.fecha}</td>
                <td style="padding:0.75rem;">${row.producto}</td>
                <td style="padding:0.75rem;">${row.categoria}</td>
                <td style="padding:0.75rem;">${row.cantidad}</td>
                <td style="padding:0.75rem;">S/. ${parseFloat(row.precio_unitario).toFixed(2)}</td>
            </tr>
        `).join('');
    } catch (e) {
        console.error("Error loading history", e);
        tbody.innerHTML = '<tr><td colspan="5" style="padding:1rem; text-align:center; color:#EF4444;">Error al cargar historial.</td></tr>';
    }
}

const btnAddHistory = document.getElementById('btnAddHistory');
if (btnAddHistory) {
    btnAddHistory.addEventListener('click', async () => {
        const msg = document.getElementById('histMsg');
        msg.textContent = "Guardando...";
        msg.style.color = "#9CA3AF";

        const payload = {
            fecha: document.getElementById('inpHistFecha').value,
            producto: document.getElementById('inpHistProducto').value,
            marca: document.getElementById('inpHistMarca').value,
            categoria: document.getElementById('inpHistCategoria').value,
            cantidad: parseInt(document.getElementById('inpHistCantidad').value),
            precio_unitario: parseFloat(document.getElementById('inpHistPrecio').value)
        };

        if (!payload.fecha || !payload.producto || !payload.categoria || !payload.marca) {
            msg.textContent = "Por favor completa todos los campos (incluyendo Marca).";
            msg.style.color = "#EF4444";
            return;
        }

        try {
            const resp = await fetch('/history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(payload)
            });

            if (resp.ok) {
                msg.textContent = "Registro guardado correctamente.";
                msg.style.color = "#10B981";
                loadHistory();
                document.getElementById('inpHistProducto').value = '';
                document.getElementById('inpHistMarca').value = '';
                document.getElementById('inpHistCategoria').value = '';
                document.getElementById('inpHistCantidad').value = '1';
            } else {
                msg.textContent = "Error al guardar.";
                msg.style.color = "#EF4444";
            }
        } catch (e) {
            console.error(e);
            msg.textContent = "Error de conexión.";
            msg.style.color = "#EF4444";
        }
    });
}

const btnRetrain = document.getElementById('btnRetrain');
if (btnRetrain) {
    btnRetrain.addEventListener('click', async () => {
        console.log("Retrain button clicked");
        const originalText = btnRetrain.textContent;
        btnRetrain.textContent = "⏳ Entrenando...";
        btnRetrain.disabled = true;

        try {
            const resp = await fetch('/retrain', { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });

            if (resp.ok) {
                const data = await resp.json();
                alert("Modelo reentrenado");
            } else {
                const errText = await resp.text();
                console.error("Error retraining:", errText);
                alert(`Error al reentrenar: ${errText}`);
            }
        } catch (e) {
            console.error(e);
            alert(`Error de conexión al reentrenar: ${e.message}`);
        } finally {
            btnRetrain.textContent = originalText;
            btnRetrain.disabled = false;
        }
    });
} else {
    console.error("Retrain button not found in DOM");
}

// Profile Settings Logic
const btnUpdateUsername = document.getElementById('btnUpdateUsername');
if (btnUpdateUsername) {
    btnUpdateUsername.addEventListener('click', () => {
        const msg = document.getElementById('usernameMsg');
        const newUsername = document.getElementById('newUsername').value.trim();

        if (!newUsername) {
            msg.textContent = "Por favor ingresa un nuevo nombre de usuario.";
            msg.style.color = "#EF4444";
            return;
        }

        // Simulación - en producción esto haría una llamada al backend
        msg.textContent = "Funcionalidad en desarrollo. Contacta al administrador para cambiar tu usuario.";
        msg.style.color = "#F59E0B";
    });
}

const btnUpdatePassword = document.getElementById('btnUpdatePassword');
if (btnUpdatePassword) {
    btnUpdatePassword.addEventListener('click', () => {
        const msg = document.getElementById('passwordMsg');
        const currentPwd = document.getElementById('currentPassword').value;
        const newPwd = document.getElementById('newPassword').value;
        const confirmPwd = document.getElementById('confirmPassword').value;

        if (!currentPwd || !newPwd || !confirmPwd) {
            msg.textContent = "Por favor completa todos los campos.";
            msg.style.color = "#EF4444";
            return;
        }

        if (newPwd !== confirmPwd) {
            msg.textContent = "Las contraseñas no coinciden.";
            msg.style.color = "#EF4444";
            return;
        }

        if (newPwd.length < 6) {
            msg.textContent = "La contraseña debe tener al menos 6 caracteres.";
            msg.style.color = "#EF4444";
            return;
        }

        // Simulación - en producción esto haría una llamada al backend
        msg.textContent = "Funcionalidad en desarrollo. Contacta al administrador para cambiar tu contraseña.";
        msg.style.color = "#F59E0B";

        // Limpiar campos
        document.getElementById('currentPassword').value = '';
        document.getElementById('newPassword').value = '';
        document.getElementById('confirmPassword').value = '';
    });
}

function initTemporalChart() {
    try {
        const ctx = document.getElementById('temporalChart').getContext('2d');
        temporalChartInstance = new Chart(ctx, {
            type: 'line', data: { labels: [], datasets: [{ label: 'Demanda Mensual', data: [], backgroundColor: 'rgba(59,130,246,0.1)', borderColor: '#3B82F6', borderWidth: 2, fill: true, tension: 0.4, pointBackgroundColor: '#3B82F6', pointBorderColor: '#fff', pointBorderWidth: 2, pointRadius: 5, pointHoverRadius: 7 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#9CA3AF' } } }, scales: { y: { beginAtZero: true, grid: { color: '#374151' }, ticks: { color: '#9CA3AF' } }, x: { grid: { display: false }, ticks: { color: '#9CA3AF' } } } }
        });
    } catch (e) { console.error("Error init temporal chart", e); }
}

function initTopChart() {
    try {
        const ctx = document.getElementById('topChart').getContext('2d');
        topChartInstance = new Chart(ctx, {
            type: 'bar', data: { labels: [], datasets: [{ label: 'Demanda Estimada', data: [], backgroundColor: '#3B82F6', borderRadius: 6 }] },
            options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#9CA3AF' } } }, scales: { x: { beginAtZero: true, grid: { color: '#374151' }, ticks: { color: '#9CA3AF' } }, y: { grid: { display: false }, ticks: { color: '#9CA3AF' } } } }
        });
    } catch (e) { console.error("Error init top chart", e); }
}

function initVariationChart() {
    try {
        const ctx = document.getElementById('variationChart').getContext('2d');
        variationChartInstance = new Chart(ctx, {
            type: 'bar',
            data: { labels: [], datasets: [{ label: 'Variación %', data: [], backgroundColor: [], borderRadius: 6 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#9CA3AF' } } }, scales: { y: { beginAtZero: true, grid: { color: '#374151' }, ticks: { color: '#9CA3AF', callback: function (value) { return value + '%'; } } }, x: { grid: { display: false }, ticks: { color: '#9CA3AF' } } } }
        });
    } catch (e) { console.error("Error init variation chart", e); }
}

function populateTemporalSelects() {
    populateSelect('selProductoTemporal', optionsData.producto);
    const firstProd = optionsData.producto ? optionsData.producto[0] : null;
    if (firstProd && optionsData.mappings?.[firstProd]) {
        populateSelect('selMarcaTemporal', optionsData.mappings[firstProd].marcas);
        populateSelect('selCategoriaTemporal', optionsData.mappings[firstProd].categorias);
    }

    document.getElementById('selProductoTemporal').addEventListener('change', () => {
        const prod = document.getElementById('selProductoTemporal').value;
        if (optionsData.mappings?.[prod]) {
            populateSelect('selMarcaTemporal', optionsData.mappings[prod].marcas);
            populateSelect('selCategoriaTemporal', optionsData.mappings[prod].categorias);
        }
        if (temporalChartInstance && temporalChartInstance.data.labels.length > 0) {
            document.getElementById('btnGenerateTemporal').click();
        }
    });

    // Add other listeners...
    ['selMarcaTemporal', 'selCategoriaTemporal', 'inpPrecioTemporal'].forEach(id => {
        document.getElementById(id).addEventListener('change', () => {
            if (temporalChartInstance && temporalChartInstance.data.labels.length > 0) {
                document.getElementById('btnGenerateTemporal').click();
            }
        });
    });
}

function populateVariationSelects() {
    populateSelect('selProductoVariation', optionsData.producto);
    const firstProd = optionsData.producto ? optionsData.producto[0] : null;
    if (firstProd && optionsData.mappings?.[firstProd]) {
        populateSelect('selMarcaVariation', optionsData.mappings[firstProd].marcas);
        populateSelect('selCategoriaVariation', optionsData.mappings[firstProd].categorias);
    }

    document.getElementById('selProductoVariation').addEventListener('change', () => {
        const prod = document.getElementById('selProductoVariation').value;
        if (optionsData.mappings?.[prod]) {
            populateSelect('selMarcaVariation', optionsData.mappings[prod].marcas);
            populateSelect('selCategoriaVariation', optionsData.mappings[prod].categorias);
        }
    });
}

function populateHistorySelects() {
    populateSelect('inpHistProducto', optionsData.producto);
    const firstProd = optionsData.producto ? optionsData.producto[0] : null;
    if (firstProd && optionsData.mappings?.[firstProd]) {
        populateSelect('inpHistMarca', optionsData.mappings[firstProd].marcas);
        populateSelect('inpHistCategoria', optionsData.mappings[firstProd].categorias);
    }

    document.getElementById('inpHistProducto').addEventListener('change', () => {
        const prod = document.getElementById('inpHistProducto').value;
        if (optionsData.mappings?.[prod]) {
            populateSelect('inpHistMarca', optionsData.mappings[prod].marcas);
            populateSelect('inpHistCategoria', optionsData.mappings[prod].categorias);
        }
    });
}

document.getElementById('btnGenerateTemporal').addEventListener('click', async () => {
    const meses = parseInt(document.getElementById('inpMesesTemporal').value);
    const basePayload = { producto: document.getElementById('selProductoTemporal').value, marca: document.getElementById('selMarcaTemporal').value, categoria: document.getElementById('selCategoriaTemporal').value, precio_unitario: parseFloat(document.getElementById('inpPrecioTemporal').value), tipo_producto: optionsData.tipo_producto?.[0] || "No especificado", metodo_pago: "efectivo", comprobante: "boleta" };
    const labels = [], predictions = [], mesesNombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    const hoy = new Date();

    let baseDemand = 0;
    try {
        const resp = await fetch('/predict', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify(basePayload) });
        const data = await resp.json();
        baseDemand = data.demanda_estimada;
    } catch (e) { console.error(e); baseDemand = 0; }

    const seasonalMultipliers = getSeasonalMultipliers(basePayload.producto, basePayload.marca, basePayload.categoria);

    for (let i = 0; i < meses; i++) {
        const fecha = new Date(hoy.getFullYear(), hoy.getMonth() + i + 1, 1);
        const mes = fecha.getMonth() + 1;
        const multiplier = seasonalMultipliers[mes] || 1.0;
        const adjustedDemand = baseDemand * multiplier;

        labels.push(`${mesesNombres[fecha.getMonth()]} ${fecha.getFullYear()}`);
        predictions.push(adjustedDemand);
    }

    temporalChartInstance.data.labels = labels;
    temporalChartInstance.data.datasets[0].data = predictions;
    temporalChartInstance.update();
    const avg = predictions.reduce((a, b) => a + b, 0) / predictions.length;
    document.getElementById('metricAvg').textContent = avg.toFixed(1) + ' u';
    document.getElementById('metricPeak').textContent = Math.max(...predictions).toFixed(1) + ' u';
    document.getElementById('metricLow').textContent = Math.min(...predictions).toFixed(1) + ' u';
});

document.getElementById('btnGenerateVariation').addEventListener('click', async () => {
    const meses = parseInt(document.getElementById('inpMesesVariation').value);
    const basePayload = {
        producto: document.getElementById('selProductoVariation').value,
        marca: document.getElementById('selMarcaVariation').value,
        categoria: document.getElementById('selCategoriaVariation').value,
        precio_unitario: parseFloat(document.getElementById('inpPrecioVariation').value),
        tipo_producto: optionsData.tipo_producto?.[0] || "No especificado",
        metodo_pago: "efectivo",
        comprobante: "boleta"
    };

    const labels = [], variations = [], colors = [];
    const mesesNombres = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    const hoy = new Date();

    let baseDemand = 0;
    try {
        const resp = await fetch('/predict', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify(basePayload) });
        const data = await resp.json();
        baseDemand = data.demanda_estimada;
    } catch (e) { console.error(e); baseDemand = 0; }

    const seasonalMultipliers = getSeasonalMultipliers(basePayload.producto, basePayload.marca, basePayload.categoria);
    const demands = [];
    for (let i = 0; i < meses; i++) {
        const fecha = new Date(hoy.getFullYear(), hoy.getMonth() + i + 1, 1);
        const mes = fecha.getMonth() + 1;
        const multiplier = seasonalMultipliers[mes] || 1.0;
        demands.push(baseDemand * multiplier);
    }

    for (let i = 1; i < demands.length; i++) {
        const fecha = new Date(hoy.getFullYear(), hoy.getMonth() + i + 1, 1);
        const variation = ((demands[i] - demands[i - 1]) / demands[i - 1]) * 100;
        labels.push(`${mesesNombres[fecha.getMonth()]} ${fecha.getFullYear()}`);
        variations.push(variation.toFixed(2));
        colors.push(variation >= 0 ? '#10B981' : '#EF4444');
    }

    variationChartInstance.data.labels = labels;
    variationChartInstance.data.datasets[0].data = variations;
    variationChartInstance.data.datasets[0].backgroundColor = colors;
    variationChartInstance.update();
});

document.getElementById('btnGenerateTop').addEventListener('click', async () => {
    const topCount = parseInt(document.getElementById('inpTopCount').value), productos = optionsData.producto || [];
    const loadingStatus = document.getElementById('topLoadingStatus');
    loadingStatus.style.display = 'block';
    const results = [];
    for (const prod of productos.slice(0, Math.min(50, productos.length))) {
        const mapping = optionsData.mappings?.[prod];
        if (!mapping) continue;
        const precio = mapping.avg_price || 10;
        const payload = { producto: prod, marca: mapping.marcas[0], categoria: mapping.categorias[0], precio_unitario: precio, tipo_producto: optionsData.tipo_producto?.[0] || "No especificado", metodo_pago: "efectivo", comprobante: "boleta" };
        try {
            const resp = await fetch('/predict', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify(payload) });
            const data = await resp.json();
            results.push({ producto: prod, demanda: data.demanda_estimada });
        } catch (e) { console.error(e); }
    }
    results.sort((a, b) => b.demanda - a.demanda);
    const top = results.slice(0, topCount);
    topChartInstance.data.labels = top.map(r => r.producto);
    topChartInstance.data.datasets[0].data = top.map(r => r.demanda);
    topChartInstance.update();
    loadingStatus.style.display = 'none';
});

function populateSelect(id, items) {
    const sel = document.getElementById(id);
    if (!items) return;
    const filteredItems = items.filter(i => i && i.toLowerCase() !== 'desconocida');
    sel.innerHTML = filteredItems.map(i => `<option value="${i}">${i}</option>`).join('');
}

function updateDependentOptions() {
    const selectedProd = document.getElementById('selProducto').value, mappings = optionsData.mappings;
    if (mappings?.[selectedProd]) {
        populateSelect('selMarca', mappings[selectedProd].marcas);
        populateSelect('selCategoria', mappings[selectedProd].categorias);
    } else {
        populateSelect('selMarca', optionsData.marca);
        populateSelect('selCategoria', optionsData.categoria);
    }
}

document.getElementById('selProducto').addEventListener('change', updateDependentOptions);

document.getElementById('btnAdd').addEventListener('click', () => {
    const prod = { producto: document.getElementById('selProducto').value, marca: document.getElementById('selMarca').value, categoria: document.getElementById('selCategoria').value, precio_unitario: parseFloat(document.getElementById('inpPrecio').value), tipo_producto: optionsData.tipo_producto?.[0] || "No especificado", metodo_pago: "efectivo", comprobante: "boleta" };
    selectedProducts.push(prod);
    renderProductList();
    updateChart();
});

function renderProductList() {
    const list = document.getElementById('productList');
    list.innerHTML = selectedProducts.map((p, i) => `<div class="product-item"><div><div style="font-weight:600">${p.producto}</div><div style="font-size:0.8rem;color:#9CA3AF">${p.marca} - S/.${p.precio_unitario}</div></div><div class="remove-prod" onclick="removeProduct(${i})">✕</div></div>`).join('');
    document.getElementById('prodCount').textContent = selectedProducts.length;
}

window.removeProduct = (index) => {
    selectedProducts.splice(index, 1);
    renderProductList();
    updateChart();
};


async function updateChart() {
    const btn = document.getElementById('btnCompare');
    if (btn) {
        btn.textContent = "Actualizando...";
        btn.disabled = true;
    }

    if (selectedProducts.length === 0) {
        if (chartInstance) {
            chartInstance.data.labels = [];
            chartInstance.data.datasets[0].data = [];
            chartInstance.update();
        }
        document.getElementById('totalDemand').textContent = "0";
        document.getElementById('topProduct').textContent = "-";
        document.getElementById('topProductVal').textContent = "Mayor demanda";
        document.getElementById('alertsList').innerHTML = '<div style="padding:0.5rem; color:#9CA3AF;">Agrega productos...</div>';

        if (btn) {
            btn.textContent = "Actualizar Gráfico";
            btn.disabled = false;
        }
        return;
    }

    const predictions = [];
    let total = 0;
    let maxDemand = -1;
    let maxProduct = "";

    for (const p of selectedProducts) {
        try {

            const resp = await fetch('/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify(p)
            });
            if (resp.ok) {
                const data = await resp.json();
                const val = parseFloat(data.demanda_estimada) || 0;
                predictions.push(val);
                total += val;
                if (val > maxDemand) {
                    maxDemand = val;
                    maxProduct = p.producto;
                }
            } else {
                const errText = await resp.text();
                console.error("Error fetching prediction:", errText);
                alert(`Error del servidor: ${errText}`);
                predictions.push(0);
            }
        } catch (e) {
            console.error(e);
            alert(`Error de conexión: ${e.message}`);
            predictions.push(0);
        }
    }

    if (chartInstance) {
        chartInstance.data.labels = selectedProducts.map(p => p.producto);
        chartInstance.data.datasets[0].data = predictions;
        chartInstance.update();
    } else {
        // Try to re-init if missing
        initCharts();
        if (chartInstance) {
            chartInstance.data.labels = selectedProducts.map(p => p.producto);
            chartInstance.data.datasets[0].data = predictions;
            chartInstance.update();
        }
    }

    document.getElementById('totalDemand').textContent = total.toFixed(1);
    document.getElementById('topProduct').textContent = maxProduct || "-";
    document.getElementById('topProductVal').textContent = maxDemand > 0 ? `${maxDemand.toFixed(1)} Unidades` : "-";

    const alertsDiv = document.getElementById('alertsList');
    let alertsHtml = "";
    selectedProducts.forEach((p, i) => {
        const demand = predictions[i];
        if (demand > 50) {
            alertsHtml += `<div style="padding:0.5rem; background:rgba(16,185,129,0.1); border-left:3px solid #10B981; margin-bottom:0.5rem;"><strong>Tendencia al Alza</strong><br>${p.producto}: Demanda alta prevista (${demand.toFixed(0)} u).</div>`;
        } else if (demand < 10) {
            alertsHtml += `<div style="padding:0.5rem; background:rgba(239,68,68,0.1); border-left:3px solid #EF4444; margin-bottom:0.5rem;"><strong>Baja Demanda</strong><br>${p.producto}: Considerar promoción.</div>`;
        }
    });
    if (!alertsHtml) alertsHtml = '<div style="padding:0.5rem; color:#9CA3AF;">Sin alertas críticas.</div>';
    alertsDiv.innerHTML = alertsHtml;

    if (btn) {
        btn.textContent = "Actualizar Gráfico";
        btn.disabled = false;
    }
}

document.getElementById('btnCompare').addEventListener('click', updateChart);
init();


