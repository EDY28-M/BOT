const { chromium } = require('playwright');

// ── Arguments ──────────────────────────────────────────────────────
const DNI = process.argv[2];
const MAX_RETRIES = parseInt(process.argv[3] || '5', 10);

if (!DNI) {
    console.log(JSON.stringify({ success: false, error: "No DNI provided", logs: [] }));
    process.exit(1);
}

const URL = 'https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos';

// ── Main ───────────────────────────────────────────────────────────
(async () => {
    let browser = null;
    const result = {
        success: false,
        data: null,
        motivo: "",
        logs: []
    };

    function pushLog(type, msg) {
        result.logs.push({ type, message: String(msg).substring(0, 500), timestamp: new Date().toISOString() });
    }

    try {
        // ── Launch Browser ─────────────────────────────────────────
        browser = await chromium.launch({
            headless: false,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        const context = await browser.newContext({
            viewport: { width: 1366, height: 768 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        });
        const page = await context.newPage();

        // ── PROFESSIONAL MONITORING ────────────────────────────────
        page.on('console', msg => {
            pushLog('CONSOLE_' + msg.type().toUpperCase(), msg.text());
        });

        page.on('pageerror', error => {
            pushLog('JS_ERROR', error.message);
        });

        page.on('requestfailed', request => {
            const failure = request.failure();
            pushLog('NET_FAIL', `${request.method()} ${request.url()} - ${failure ? failure.errorText : 'unknown'}`);
        });

        page.on('response', response => {
            if (response.status() >= 400) {
                pushLog('HTTP_ERROR', `${response.status()} ${response.url()}`);
            }
        });
        // ── END MONITORING ─────────────────────────────────────────

        // ── Navigate ───────────────────────────────────────────────
        pushLog('INFO', `Navigating to SUNEDU for DNI ${DNI}`);
        await page.goto(URL, {
            waitUntil: 'domcontentloaded',
            timeout: 30000
        });

        // Wait for Angular app to bootstrap
        await page.waitForTimeout(6000);

        // ── Retry Loop ─────────────────────────────────────────────
        let lastMotivo = 'MAX_REINTENTOS';

        for (let intento = 1; intento <= MAX_RETRIES; intento++) {
            pushLog('INFO', `Attempt ${intento}/${MAX_RETRIES}`);

            try {
                // ── Detect State ───────────────────────────────────
                const estado = await detectarEstado(page);
                pushLog('INFO', `Estado detectado: ${estado}`);

                // ── Handle Verification/Turnstile ──────────────────
                if (estado === 'verificacion' || estado === 'verificacion_fallida') {
                    pushLog('WARN', 'Verification/Turnstile detected, attempting checkbox...');
                    await clickCheckbox(page);
                    await page.waitForTimeout(4000);

                    const nuevoEstado = await detectarEstado(page);
                    if (nuevoEstado === 'verificacion_fallida' || nuevoEstado === 'verificacion') {
                        lastMotivo = 'CAPTCHA_FALLO';
                        pushLog('WARN', 'Verification failed, reloading...');
                        await page.waitForTimeout(7000);
                        await page.reload({ waitUntil: 'domcontentloaded' });
                        await page.waitForTimeout(4000);
                        continue;
                    }
                }

                // ── Fill DNI ───────────────────────────────────────
                const inputFilled = await page.evaluate((dni) => {
                    const input = document.querySelector('input[formcontrolname="dni"]') ||
                        document.querySelector('input[type="text"]');
                    if (!input) return false;
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(input, dni);
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }, DNI);

                if (!inputFilled) {
                    lastMotivo = 'INPUT_NO_ENCONTRADO';
                    pushLog('ERROR', 'DNI input field not found');
                    await page.reload({ waitUntil: 'domcontentloaded' });
                    await page.waitForTimeout(4000);
                    continue;
                }

                await page.waitForTimeout(500);

                // ── Click Search ───────────────────────────────────
                const clicked = await page.evaluate(() => {
                    const spans = document.querySelectorAll('span.p-button-label');
                    for (let i = 0; i < spans.length; i++) {
                        if (spans[i].textContent.trim() === 'Buscar') {
                            const btn = spans[i].closest('button');
                            if (btn) { btn.click(); return true; }
                        }
                    }
                    return false;
                });

                if (!clicked) {
                    lastMotivo = 'BOTON_NO_ENCONTRADO';
                    pushLog('ERROR', 'Search button not found');
                    continue;
                }

                pushLog('INFO', 'Search button clicked, waiting for results...');

                // ── Wait for Result ────────────────────────────────
                const res = await esperarResultado(page, 15000);
                pushLog('INFO', `Result state: ${res}`);

                if (res === 'tabla') {
                    const data = await extraerDatos(page);
                    if (data && data.length > 0) {
                        result.success = true;
                        result.data = data;
                        result.motivo = 'Encontrado';
                        pushLog('INFO', `Found ${data.length} record(s)`);
                        await page.waitForTimeout(2000);
                        break; // Success!
                    }
                    lastMotivo = 'TABLA_VACIA';
                } else if (res === 'no_encontrado') {
                    result.success = false;
                    result.motivo = 'NO_ENCONTRADO';
                    pushLog('INFO', 'DNI not found in SUNEDU');

                    // Close swal
                    await page.evaluate(() => {
                        const btn = document.querySelector('button.swal2-close') ||
                            document.querySelector('button[aria-label="Close this dialog"]');
                        if (btn) btn.click();
                    });
                    await page.waitForTimeout(800);
                    break; // Not found is a valid result
                } else if (res === 'verificacion_fallida' || res === 'verificacion') {
                    lastMotivo = 'CAPTCHA_FALLO';
                    pushLog('WARN', 'Verification challenge appeared after search');
                    await page.waitForTimeout(5000);
                    await page.reload({ waitUntil: 'domcontentloaded' });
                    await page.waitForTimeout(4000);
                    continue;
                } else {
                    lastMotivo = `RESULTADO_INESPERADO: ${res}`;
                    pushLog('WARN', `Unexpected result: ${res}`);
                }

            } catch (e) {
                lastMotivo = `EXCEPCION: ${e.message}`;
                pushLog('ERROR', `Attempt ${intento} exception: ${e.message}`);
                try {
                    await page.reload({ waitUntil: 'domcontentloaded' });
                    await page.waitForTimeout(4000);
                } catch (reloadErr) {
                    pushLog('ERROR', `Reload failed: ${reloadErr.message}`);
                }
            }
        }

        // If we exit the loop without success and no specific motivo set
        if (!result.success && !result.motivo) {
            result.motivo = lastMotivo;
        }

    } catch (e) {
        result.success = false;
        result.motivo = 'CRASH: ' + e.message;
        pushLog('CRASH', e.message);
    } finally {
        if (browser) {
            try { await browser.close(); } catch (e) { /* ignore */ }
        }
        // Output ONLY the JSON result to stdout
        console.log(JSON.stringify(result));
    }
})();

// ── Helper Functions ───────────────────────────────────────────────

async function detectarEstado(page) {
    try {
        return await page.evaluate(() => {
            const tabla = document.querySelector('table.custom-table');
            if (tabla && tabla.querySelectorAll('tbody tr.ng-star-inserted').length > 0)
                return 'tabla';

            const swal = document.querySelector('.swal2-html-container');
            if (swal) {
                const txt = (swal.innerText || '').toLowerCase();
                if (txt.includes('no se encontraron')) return 'no_encontrado';
                if (txt.includes('verificaci') && txt.includes('fallid')) return 'verificacion_fallida';
                if (txt.includes('verificaci') || txt.includes('seguridad')) return 'verificacion';
            }

            const cbs = document.querySelectorAll('input[type="checkbox"]');
            for (let i = 0; i < cbs.length; i++) {
                if (!cbs[i].checked) return 'verificacion';
            }

            // Check iframes for Turnstile
            const iframes = document.querySelectorAll('iframe');
            for (let i = 0; i < iframes.length; i++) {
                const src = iframes[i].src || '';
                if (src.includes('turnstile') || src.includes('challenges')) {
                    const r = iframes[i].getBoundingClientRect();
                    if (r.width > 0 && r.height > 0) return 'verificacion';
                }
            }
            return 'cargando';
        });
    } catch (e) {
        return 'cargando';
    }
}

async function clickCheckbox(page) {
    try {
        await page.evaluate(() => {
            const cbs = document.querySelectorAll('input[type="checkbox"]');
            for (let i = 0; i < cbs.length; i++) {
                if (!cbs[i].checked) { cbs[i].click(); return; }
            }
        });
    } catch (e) {
        // Try Playwright click
        try {
            const cb = page.locator('input[type="checkbox"]').first();
            if (await cb.count() > 0) await cb.click();
        } catch (e2) { /* ignore */ }
    }
}

async function esperarResultado(page, timeout) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
        const estado = await detectarEstado(page);
        if (estado !== 'cargando') return estado;
        await page.waitForTimeout(500);
    }
    return 'timeout';
}

async function extraerDatos(page) {
    return await page.evaluate(() => {
        const rows = document.querySelectorAll('table.custom-table tbody tr.ng-star-inserted');
        const results = [];
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            if (cells.length < 3) return;

            let nombre = '', dniT = '', grado = '', fDip = '', inst = '';

            // Cell 0: Nombres + DNI
            cells[0].querySelectorAll('p').forEach(p => {
                const t = p.innerText.trim();
                if (t.includes('DNI')) dniT = t;
                else if (t.length > 3 && t.includes(',')) nombre = t;
            });

            // Cell 1: Grado + Fecha
            cells[1].querySelectorAll('p').forEach(p => {
                const t = p.innerText.trim(), tl = t.toLowerCase();
                if (tl.includes('fecha de diploma:')) fDip = t.split(':').slice(1).join(':').trim();
                else if (t.length > 5 && !tl.startsWith('grado') && !tl.startsWith('fecha')) grado = t;
            });

            // Cell 2: Institucion
            cells[2].querySelectorAll('p').forEach(p => {
                const tu = p.innerText.trim().toUpperCase();
                if (tu.includes('UNIVERSIDAD') || tu.includes('INSTITUTO')) inst = p.innerText.trim();
            });

            results.push({
                nombres: nombre,
                dni_encontrado: dniT,
                grado_o_titulo: grado,
                institucion: inst,
                fecha_diploma: fDip
            });
        });
        return results;
    });
}
