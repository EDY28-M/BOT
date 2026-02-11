using DniAutomation.Application.UseCases;
using DniAutomation.Domain.Interfaces;
using DniAutomation.Domain.Enums;
using DniAutomation.Application.DTOs;
using Microsoft.AspNetCore.Mvc;
using ClosedXML.Excel;
using System.IO;
using System.Linq;

namespace DniAutomation.Controllers;

[ApiController]
[Route("api")]
public class DniController : ControllerBase
{
    private readonly BulkUploadUseCase _bulkUpload;
    private readonly GetStatusUseCase _getStatus;
    private readonly IDniRecordRepository _repository;
    private readonly ILogger<DniController> _logger;

    public DniController(BulkUploadUseCase bulkUpload, GetStatusUseCase getStatus, IDniRecordRepository repository, ILogger<DniController> logger)
    {
        _bulkUpload = bulkUpload;
        _getStatus = getStatus;
        _repository = repository;
        _logger = logger;
    }

    [HttpPost("upload")]
    public async Task<IActionResult> BulkUpload(IFormFile? file, CancellationToken ct)
    {
        if (file is null || file.Length == 0) return BadRequest(new { detail = "Se requiere un archivo" });
        
        var dnis = new List<string>();
        var fileName = file.FileName;
        
        try 
        {
            using var stream = file.OpenReadStream();
            if (fileName.EndsWith(".xlsx", StringComparison.OrdinalIgnoreCase))
            {
                using var workbook = new XLWorkbook(stream);
                var ws = workbook.Worksheets.First();
                foreach (var row in ws.RowsUsed().Skip(1)) // Skip header
                {
                    var val = row.Cell(1).GetString(); // Assume first column
                    if (!string.IsNullOrWhiteSpace(val)) dnis.Add(val);
                }
            }
            else // Assume text file
            {
                using var reader = new StreamReader(stream);
                while (await reader.ReadLineAsync(ct) is { } line)
                {
                    if (!string.IsNullOrWhiteSpace(line)) dnis.Add(line);
                }
            }

            if (dnis.Count == 0) return BadRequest(new { detail = "No se encontraron DNIs en el archivo" });
            
            var request = new BulkUploadRequest(fileName, dnis);
            return Ok(await _bulkUpload.ExecuteAsync(request, ct));
        }
        catch (Exception ex) 
        { 
            _logger.LogError(ex, "Error parsing file");
            return BadRequest(new { detail = "Error al procesar el archivo: " + ex.Message }); 
        }
    }

    [HttpGet("status")]
    public async Task<IActionResult> GetStatus(CancellationToken ct) => Ok(await _getStatus.ExecuteAsync(ct));

    [HttpGet("registros")]
    public async Task<IActionResult> GetRecords([FromQuery] string? estado = null, [FromQuery] int? lote_id = null, [FromQuery] int limit = 200, [FromQuery] int offset = 0, CancellationToken ct = default)
    {
        DniStatus? s = null; if (!string.IsNullOrEmpty(estado) && Enum.TryParse<DniStatus>(estado, true, out var p)) s = p;
        var r = await _repository.GetRecordsAsync(s, lote_id, limit, offset, ct);
        return Ok(r.Select(DniRecordDto.FromEntity));
    }

    [HttpGet("lotes")]
    public async Task<IActionResult> GetBatches(CancellationToken ct) => Ok((await _repository.GetBatchesAsync(ct)).Select(b => new { b.Id, b.FileName, b.TotalDnis, CreatedAt = b.CreatedAt.ToString("o") }));
}

[ApiController]
[Route("api")]
public class SystemController : ControllerBase
{
    private readonly IQueueService _queue;
    private readonly IDniRecordRepository _repository;
    private readonly RetryUseCase _retryUseCase;
    private readonly ILogger<SystemController> _logger;

    public SystemController(IQueueService queue, IDniRecordRepository repository, RetryUseCase retryUseCase, ILogger<SystemController> logger)
    {
        _queue = queue;
        _repository = repository;
        _retryUseCase = retryUseCase;
        _logger = logger;
    }

    [HttpPost("workers/stop")] // Frontend 'stop' maps to Pause in our logic (stops dequeuing)
    public async Task<IActionResult> Stop(CancellationToken ct) { await _queue.PublishSignalAsync(QueueNames.SystemSignals, SystemSignals.Pause, ct); return Ok(new { message = "Workers paused" }); }

    [HttpPost("workers/start")] // Frontend 'start' maps to Resume
    public async Task<IActionResult> Start(CancellationToken ct) { await _queue.PublishSignalAsync(QueueNames.SystemSignals, SystemSignals.Resume, ct); return Ok(new { message = "Workers resumed" }); }

    [HttpPost("retry")]
    public async Task<IActionResult> Retry(CancellationToken ct) { try { return Ok(await _retryUseCase.ExecuteAsync(ct)); } catch (InvalidOperationException ex) { return BadRequest(new { detail = ex.Message }); } }

    [HttpPost("limpiar")]
    public async Task<IActionResult> Clean(CancellationToken ct)
    {
        await _queue.PublishSignalAsync(QueueNames.SystemSignals, SystemSignals.Stop, ct);
        await Task.Delay(2000, ct);
        var r = await _repository.CleanAllAsync(ct);
        return Ok(new { message = "Cleaned", deleted = r });
    }

    [HttpPost("recover")]
    public async Task<IActionResult> Recover(CancellationToken ct) { var r = await _repository.RecoverStuckAsync(ct); return Ok(new { university = r.Item1, institute = r.Item2 }); }

    [HttpGet("workers/status")]
    public async Task<IActionResult> GetQueues(CancellationToken ct)
    {
        var u = await _queue.GetQueueLengthAsync(QueueNames.UniversityQueue, ct);
        var i = await _queue.GetQueueLengthAsync(QueueNames.InstituteQueue, ct);
        return Ok(new { university = u, institute = i });
    }
}

[ApiController]
[Route("api")]
public class ExportController : ControllerBase
{
    private readonly ExportExcelUseCase _exportExcel;
    public ExportController(ExportExcelUseCase exportExcel) { _exportExcel = exportExcel; }

    [HttpGet("resultados")] // Changed to GET to match frontend
    public async Task<IActionResult> ExportExcel([FromQuery] int? lote_id = null, CancellationToken ct = default)
    {
        try { var b = await _exportExcel.ExecuteAsync(lote_id, ct); return File(b, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "resultados.xlsx"); }
        catch (InvalidOperationException ex) { return NotFound(new { detail = ex.Message }); }
    }
}
