using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Playwright;
using Tesseract;

namespace DniAutomation.Infrastructure.Scraping;

public sealed class SuneduScraper : IAsyncDisposable
{
    private const string Url = "https://constanciasweb.sunedu.gob.pe/#/modulos/grados-y-titulos";
    private const int MaxRetries = 5;
    private IPlaywright? _playwright;
    private IBrowser? _browser;
    private IPage? _page;
    private bool _firstLoad = true;
    private readonly ILogger<SuneduScraper>? _logger;

    public SuneduScraper(ILogger<SuneduScraper>? logger = null)
    {
        _logger = logger;
    }

    public async Task InitAsync(bool headless = true)
    {
        _playwright = await Playwright.CreateAsync();
        _browser = await _playwright.Chromium.LaunchAsync(new BrowserTypeLaunchOptions 
        { 
            Headless = headless, 
            Args = new[] { "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu" } 
        });
        _page = await _browser.NewPageAsync();
        await _page.SetViewportSizeAsync(1366, 768);
    }

    public async Task<(bool Found, string? PayloadJson, string Reason)> ProcessDniAsync(string dni)
    {
        if (_page is null) throw new InvalidOperationException("Scraper not initialized");
        string lastReason = "Unknown";

        for (int attempt = 1; attempt <= MaxRetries; attempt++)
        {
            try
            {
                // 1. Prepare Page
                if (_firstLoad) 
                {
                    await _page.GotoAsync(Url);
                    await Task.Delay(5000); // Initial load wait
                    _firstLoad = false;
                }
                else 
                {
                    await CloseSwalAsync();
                    await Task.Delay(500);
                }

                // 2. Check & Pass Verification (Turnstile)
                if (!await PassVerificationAsync())
                {
                    lastReason = "Verification Failed";
                    await ReloadPageAsync();
                    continue;
                }

                // 3. Search DNI
                if (!await SearchDniAsync(dni))
                {
                    lastReason = "Search Button Not Found";
                    await ReloadPageAsync();
                    continue;
                }

                // 4. Wait Result
                string result = await WaitForResultAsync();

                if (result == "table")
                {
                    var data = await ExtractDataAsync(dni);
                    if (data.Count > 0)
                    {
                        var payload = JsonSerializer.Serialize(new { registros = data });
                        return (true, payload, "Found");
                    }
                    else
                    {
                        lastReason = "Extraction Error"; // Table found but empty extraction?
                    }
                }
                else if (result == "not_found")
                {
                    await CloseSwalAsync();
                    await Task.Delay(1000); // Anti-ban wait
                    return (false, null, "Not Found");
                }
                else if (result == "verificacion_fallida" || result == "verificacion")
                {
                    lastReason = "Verification Re-appeared";
                    await CloseSwalAsync();
                    await ReloadPageAsync();
                    continue;
                }
                else // timeout or nada
                {
                    lastReason = "Timeout / No Result";
                    await ReloadPageAsync();
                    continue;
                }
            }
            catch (Exception ex)
            {
                lastReason = $"Exception: {ex.Message}";
                _logger?.LogError(ex, "Sunedu scrape error attempt {Attempt}", attempt);
                await ReloadPageAsync();
            }
        }

        return (false, null, $"Max Retries ({MaxRetries}) - Last: {lastReason}");
    }

    private async Task ReloadPageAsync() 
    { 
        try 
        { 
            if (_page != null) 
            {
                await _page.ReloadAsync(); 
                await Task.Delay(4000); 
            }
        } 
        catch {} 
    }

    private async Task CloseSwalAsync()
    {
        if (_page == null) return;
        try 
        { 
            await _page.EvaluateAsync(@"() => { 
                var btn = document.querySelector('button.swal2-close') || 
                          document.querySelector('button[aria-label=""Close this dialog""]');
                if (btn) btn.click();
            }"); 
        } 
        catch {}
    }

    private async Task<bool> SearchDniAsync(string dni)
    {
        if (_page == null) return false;
        try 
        {
            // Input DNI
            await _page.EvalOnSelectorAsync("input[formcontrolname='dni'], input[type='text']", 
                "(el, d) => { el.value = d; el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); }", dni);
            
            await Task.Delay(500);

            // Click Search
            // We'll mimic the JS search logic from python
            var found = await _page.EvaluateAsync<bool>(@"() => {
                var spans = document.querySelectorAll('span.p-button-label');
                for (var i = 0; i < spans.length; i++) {
                    if (spans[i].textContent.trim() === 'Buscar') {
                        var btn = spans[i].closest('button');
                        if (btn) { btn.click(); return true; }
                    }
                }
                var btns = document.querySelectorAll('button');
                for (var i = 0; i < btns.length; i++) {
                    if (btns[i].textContent.trim().includes('Buscar')) {
                        btns[i].click(); return true;
                    }
                }
                return false;
            }");
            return found;
        } 
        catch { return false; }
    }

    private async Task<bool> PassVerificationAsync()
    {
        if (_page == null) return false;
        // Check if verification exists
        var state = await DetectStateAsync();
        if (state != "verificacion") return true; // No verification needed

        // Try to click checkbox
        for (int i = 0; i < 3; i++)
        {
            await CloseSwalAsync();
            await Task.Delay(500);
            await ClickCheckboxAsync();
            await Task.Delay(3000);
            
            var postState = await DetectStateAsync();
            if (postState != "verificacion" && postState != "verificacion_fallida") return true;
        }
        return false;
    }

    private async Task ClickCheckboxAsync() 
    { 
        if (_page == null) return;
        try 
        { 
            // Try explicit selector first
            var frame = _page.Frames.FirstOrDefault(f => f.Url.Contains("turnstile") || f.Url.Contains("challenges"));
            if (frame != null) 
            {
                await frame.ClickAsync("input[type='checkbox']", new() { Timeout = 1000 });
                return;
            }

            // Fallback JS click
            await _page.EvaluateAsync(@"() => {
                var cbs = document.querySelectorAll('input[type=""checkbox""]');
                for (var i = 0; i < cbs.length; i++) {
                    if (!cbs[i].checked) cbs[i].click();
                }
            }");
        } 
        catch {} 
    }

    private async Task<string> WaitForResultAsync()
    {
        for(int i=0; i<30; i++) {
            var state = await DetectStateAsync();
            if(state != "loading" && state != "cargando" && state != "nada") return state;
            
            // If stuck in 'nada' for too long, return nada
            if (state == "nada" && i > 16) return "nada"; 
            
            await Task.Delay(500);
        }
        return "timeout";
    }

    private async Task<string> DetectStateAsync()
    {
        if (_page == null) return "cargando";
        try {
            return await _page.EvaluateAsync<string>(@"() => {
                var tabla = document.querySelector('table.custom-table');
                if (tabla && tabla.querySelectorAll('tbody tr.ng-star-inserted').length > 0) return 'table';
                
                var swal = document.querySelector('.swal2-html-container');
                if (swal) {
                    var txt = (swal.innerText || '').toLowerCase();
                    if (txt.includes('no se encontraron')) return 'not_found';
                    if (txt.includes('verificaci') && txt.includes('fallid')) return 'verificacion_fallida';
                    if (txt.includes('verificaci') || txt.includes('seguridad')) return 'verificacion';
                }
                
                var cbs = document.querySelectorAll('input[type=""checkbox""]');
                for (var i = 0; i < cbs.length; i++) {
                    if (!cbs[i].checked) { // simplistic check
                        var r = cbs[i].getBoundingClientRect();
                        if (r.width > 0) return 'verificacion';
                    }
                }

                // If input present but no spinner, it's 'nada' (idle)
                var input = document.querySelector('input[formcontrolname=""dni""]');
                if (input) {
                    var spinner = document.querySelector('.p-progress-spinner, .loading, .spinner');
                    if (!spinner) return 'nada';
                }
                return 'cargando';
            }");
        } catch { return "cargando"; }
    }

    private async Task<List<Dictionary<string, string>>> ExtractDataAsync(string dni)
    {
        if (_page == null) return new();
        // JS extraction logic ported from python
        var json = await _page.EvaluateAsync<string>(@"() => {
            var res = [];
            var tabla = document.querySelector('table.custom-table');
            if (!tabla) return JSON.stringify(res);
            var filas = tabla.querySelectorAll('tbody tr.ng-star-inserted');
            filas.forEach(function(fila) {
                var celdas = fila.querySelectorAll('td');
                if (celdas.length < 3) return;
                
                var ps1 = celdas[0].querySelectorAll('p');
                var nombre = '', dniT = '';
                for (var i = 0; i < ps1.length; i++) {
                    var t = ps1[i].textContent.trim();
                    if (t.includes('DNI')) dniT = t;
                    else if (t.length > 3 && t.includes(',')) nombre = t;
                }
                
                var ps2 = celdas[1].querySelectorAll('p');
                var grado = '', fDip = '';
                for (var i = 0; i < ps2.length; i++) {
                    var t = ps2[i].textContent.trim(), tl = t.toLowerCase();
                    if (tl.includes('fecha de diploma:')) fDip = t.split(':').slice(1).join(':').trim();
                    else if (t.length > 5 && !tl.startsWith('grado') && !tl.startsWith('fecha') && !grado) grado = t;
                }
                
                var ps3 = celdas[2].querySelectorAll('p');
                var inst = '';
                for (var i = 0; i < ps3.length; i++) {
                    var tu = ps3[i].textContent.trim().toUpperCase();
                    if (tu.includes('UNIVERSIDAD') || tu.includes('INSTITUTO') || tu.includes('ESCUELA'))
                        inst = ps3[i].textContent.trim();
                }
                res.push({n: nombre, d: dniT, g: grado, i: inst, fd: fDip});
            });
            return JSON.stringify(res);
        }");
        
        var rawList = JsonSerializer.Deserialize<List<RawRecord>>(json);
        if (rawList == null) return new();

        return rawList.Select(r => new Dictionary<string, string> {
            { "nombres", r.n }, { "grado_o_titulo", r.g }, { "institucion", r.i }, { "fecha_diploma", r.fd }
        }).ToList();
    }

    private class RawRecord { public string n { get; set; } = ""; public string d { get; set; } = ""; public string g { get; set; } = ""; public string i { get; set; } = ""; public string fd { get; set; } = ""; }


    public async ValueTask DisposeAsync() { if (_browser is not null) await _browser.CloseAsync(); _playwright?.Dispose(); }
}

public sealed class MineduScraper : IAsyncDisposable
{
    private const string Url = "https://titulosinstitutos.minedu.gob.pe/";
    private const int MaxRetries = 5;
    private IPlaywright? _playwright;
    private IBrowser? _browser;
    private IPage? _page;
    private readonly ILogger<MineduScraper>? _logger;

    public MineduScraper(ILogger<MineduScraper>? logger = null)
    {
        _logger = logger;
    }

    public async Task InitAsync(bool headless = true)
    {
        _playwright = await Playwright.CreateAsync();
        _browser = await _playwright.Chromium.LaunchAsync(new BrowserTypeLaunchOptions 
        { 
            Headless = headless, 
            Args = new[] { 
                "--no-sandbox", 
                "--disable-dev-shm-usage", 
                "--disable-gpu", 
                "--ignore-certificate-errors",
                "--disable-extensions",
                "--disable-blink-features=AutomationControlled"
            } 
        });
        
        var context = await _browser.NewContextAsync(new BrowserNewContextOptions
        {
            IgnoreHTTPSErrors = true,
            UserAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            ViewportSize = new ViewportSize { Width = 1366, Height = 768 }
        });
        
        _page = await context.NewPageAsync();
        // Add extra headers to avoid blocking
        await _page.SetExtraHTTPHeadersAsync(new Dictionary<string, string>
        {
            { "Accept-Language", "es-ES,es;q=0.9" },
            { "Upgrade-Insecure-Requests", "1" },
            { "Sec-Ch-Ua", "\"Not A(Brand\";v=\"99\", \"Google Chrome\";v=\"121\", \"Chromium\";v=\"121\"" },
            { "Sec-Ch-Ua-Mobile", "?0" },
            { "Sec-Ch-Ua-Platform", "\"Windows\"" }
        });
    }

    public async Task<(bool Found, string? PayloadJson, string Reason)> ProcessDniAsync(string dni)
    {
        if (_page is null) throw new InvalidOperationException("Scraper not initialized");
        bool needReload = true;
        string lastReason = "Unknown";

        for (int attempt = 1; attempt <= MaxRetries; attempt++)
        {
            try
            {
                if (needReload) 
                {
                    try 
                    {
                        // Commit = equivalent to no wait? No, Commit waits for network response.
                        // Playwright default is Load. We want faster if possible but consistent.
                        // 'DontWait' error suggests we should use 'Commit' or just standard Load.
                        // Let's use LoadState.DOMContentLoaded for consistency.
                        await _page.GotoAsync(Url, new() { Timeout = 60000, WaitUntil = WaitUntilState.Commit }); 
                        await _page.WaitForLoadStateAsync(LoadState.DOMContentLoaded);
                    }
                    catch (Exception ex)
                    {
                        if (!ex.Message.Contains("ERR_CONNECTION_RESET")) throw; // Retry if reset
                        _logger?.LogWarning("Connection Reset, retrying load...");
                        await Task.Delay(2000);
                        await _page.GotoAsync(Url, new() { Timeout = 60000, WaitUntil = WaitUntilState.DOMContentLoaded });
                    }
                    
                    await Task.Delay(2000);
                    needReload = false;
                }

                // Input DNI
                await _page.EvalOnSelectorAsync("#DOCU_NUM", "(el, d) => { el.value = d; el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); }", dni);
                await Task.Delay(300);

                // Clear Captcha
                await _page.EvaluateAsync(@"() => { var cap = document.querySelector('#CaptchaCodeText'); if (cap) { cap.disabled = false; cap.value = ''; } }");
                
                // Solve Captcha (OCR)
                string captcha = await ResolveCaptchaAsync();
                if (string.IsNullOrEmpty(captcha))
                {
                    lastReason = "OCR Failed";
                    // Try refreshing captcha
                    if (!await RefreshCaptchaAsync()) needReload = true; 
                    continue;
                }

                // Fill Captcha
                await _page.EvalOnSelectorAsync("#CaptchaCodeText", "(el, c) => { el.value = c; el.dispatchEvent(new Event('input', {bubbles:true})); el.dispatchEvent(new Event('change', {bubbles:true})); }", captcha);
                await Task.Delay(300);

                // Click Search
                bool clicked = await _page.EvaluateAsync<bool>(@"() => {
                    var btn = document.querySelector('#btnConsultar');
                    if (btn) { btn.disabled = false; btn.click(); return true; }
                    return false;
                }");

                if (!clicked) { lastReason = "Button Not Found"; needReload = true; continue; }

                await Task.Delay(2000); // Wait for response

                // Check Error Toast/Alert
                var errorMsg = await CheckErrorAsync();
                if (!string.IsNullOrEmpty(errorMsg))
                {
                    lastReason = $"Captcha/Site Error: {errorMsg}";
                    if (errorMsg.ToLower().Contains("captcha") || errorMsg.ToLower().Contains("incorrecto"))
                    {
                         // specific retry for captcha
                         if (!await RefreshCaptchaAsync()) needReload = true;
                    }
                    continue;
                }

                // Check Result
                string resultHtml = await _page.EvaluateAsync<string>(@"() => { var div = document.querySelector('#divResultado'); return div ? div.innerHTML : ''; }");
                
                if (!string.IsNullOrEmpty(resultHtml) && resultHtml.Length > 50)
                {
                    var data = await ExtractDataAsync();
                    if (data != null)
                    {
                        var payload = JsonSerializer.Serialize(data);
                        return (true, payload, "Found");
                    }
                    lastReason = "Found but extraction failed"; // Should not happen if HTML exists
                }
                else
                {
                     // Assume Not Found if no error and no result? 
                     // Or maybe timeout? 
                     // Usually Minedu shows "No se encontraron resultados" inside divResultado or alert
                     // We'll treat as Not Found if no result appears but also no error.
                     // But let's check for specific "Not Found" message if possible.
                     // For now, retry logic from python implies empty result = timeout/not-found?
                     // Python code returns False if no HTML.
                     lastReason = "No Result HTML (Timeout)";
                }
            }
            catch (Exception ex)
            {
                lastReason = $"Exception: {ex.Message}";
                _logger?.LogError(ex, "Minedu scrape error attempt {Attempt}", attempt);
                needReload = true;
            }
        }
        
        // If we finished retries and reason is "No Result HTML", it might just be Not Found?
        // But safer to say Failed/Not Found.
        return (false, null, $"Max Retries ({MaxRetries}) - Last: {lastReason}");
    }

    private async Task<string> ResolveCaptchaAsync()
    {
        if (_page == null) return "";
        try {
            var b64 = await _page.EvaluateAsync<string>(@"() => { var img = document.querySelector('#imgCaptcha'); return img ? img.src : null; }");
            if (string.IsNullOrEmpty(b64) || !b64.Contains("base64,")) return "";
            
            var base64Data = b64.Split("base64,")[1];
            var bytes = Convert.FromBase64String(base64Data);

            // OCR using Tesseract
            // Note: TESSDATA_PREFIX env var or file placement required.
            // Using "eng" as default language for captcha (usually alphanumeric)
            using var engine = new TesseractEngine(null, "eng", EngineMode.Default);
            using var img = Pix.LoadFromMemory(bytes);
            using var page = engine.Process(img);
            var text = page.GetText().Trim().Replace(" ", "").Replace("\n", "");
            return text;
        } catch (Exception ex) {
            _logger?.LogWarning("OCR Error: {Message}", ex.Message);
            return "";
        }
    }

    private async Task<bool> RefreshCaptchaAsync()
    {
         if (_page == null) return false;
         try {
             await _page.EvaluateAsync(@"() => {
                var btn = document.querySelector('#CapImageRefresh');
                if (btn) btn.click();
             }");
             await Task.Delay(1000);
             return true;
         } catch { return false; }
    }

    private async Task<string?> CheckErrorAsync()
    {
        if (_page == null) return null;
        try {
            return await _page.EvaluateAsync<string>(@"() => {
                var toast = document.querySelector('.toast-message');
                if (toast && toast.innerText) return toast.innerText.trim();
                var val = document.querySelector('span[data-valmsg-for=""CaptchaCodeText""]');
                if (val && val.innerText) return val.innerText.trim();
                return '';
            }");
        } catch { return null; }
    }

    private async Task<Dictionary<string, string>?> ExtractDataAsync()
    {
        if (_page == null) return null;
        var json = await _page.EvaluateAsync<string>(@"() => {
            var result = {nombres: '', titulo: '', institucion: '', fecha: '', nivel: '', codigo: ''};
            var div = document.querySelector('#divResultado');
            if (!div) return null;
            var tables = div.querySelectorAll('table.gobpe-res-tabla-cuerpo');
            for (var t = 0; t < tables.length; t++) {
                var rows = tables[t].querySelectorAll('tbody tr');
                for (var i = 0; i < rows.length; i++) {
                    var cells = rows[i].querySelectorAll('td');
                    if (cells.length < 3) continue;
                    
                    var cell1 = cells[0].innerText.trim();
                    var lines1 = cell1.split('\n');
                    if (lines1.length > 0) result.nombres = lines1[0].trim();

                    var cell2 = cells[1].innerText.trim();
                    var lines2 = cell2.split('\n');
                    for (var j = 0; j < lines2.length; j++) {
                        var line = lines2[j].trim();
                        if (!line.includes(':') && line.length > 5 && !result.titulo) result.titulo = line;
                        if (line.includes('Nivel:')) result.nivel = line.replace('Nivel:', '').trim();
                        if (line.includes('Fecha de emisión:') || line.includes('Fecha emisión:'))
                            result.fecha = line.split(':')[1].trim();
                        if (line.includes('Código DRE:')) result.codigo = line.split(':')[1].trim();
                    }

                    var cell3 = cells[2].innerText.trim();
                    var lines3 = cell3.split('\n');
                    if (lines3.length > 0) result.institucion = lines3[0].trim();

                    if (result.titulo) break;
                }
                if (result.titulo) break;
            }
            return JSON.stringify(result);
        }");
        
        if (json == "null" || string.IsNullOrEmpty(json)) return null;
        var r = JsonSerializer.Deserialize<RawMinedu>(json);
        if (r == null || string.IsNullOrEmpty(r.titulo)) return null;

        return new Dictionary<string, string> {
            { "nombre_completo", r.nombres }, { "titulo", r.titulo }, { "institucion", r.institucion }, 
            { "nivel", r.nivel }, { "fecha_expedicion", r.fecha }, { "codigo_dre", r.codigo }
        };
    }
    
    private class RawMinedu { public string nombres { get; set; } = ""; public string titulo { get; set; } = ""; public string institucion { get; set; } = ""; public string fecha { get; set; } = ""; public string nivel { get; set; } = ""; public string codigo { get; set; } = ""; }

    public async ValueTask DisposeAsync() { if (_browser is not null) await _browser.CloseAsync(); _playwright?.Dispose(); }
}
