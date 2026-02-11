using DniAutomation.Application.DTOs;
using DniAutomation.Domain.Interfaces;
using DniAutomation.Domain.Enums;
using ClosedXML.Excel;

namespace DniAutomation.Application.UseCases;

public sealed class BulkUploadUseCase
{
    private readonly IDniRecordRepository _repository;
    private readonly IQueueService _queue;

    public BulkUploadUseCase(IDniRecordRepository repository, IQueueService queue)
    {
        _repository = repository;
        _queue = queue;
    }

    public async Task<BulkUploadResponse> ExecuteAsync(BulkUploadRequest request, CancellationToken ct)
    {
        if (request.Dnis is null || request.Dnis.Count == 0)
            throw new ArgumentException("No valid DNIs provided.");

        var uniqueDnis = request.Dnis
            .Select(d => d.Trim())
            .Where(d => d.Length >= 7 && d.All(char.IsDigit))
            .Distinct()
            .ToList();

        if (uniqueDnis.Count == 0)
            throw new ArgumentException("No valid DNIs found after filtering.");

        var batch = await _repository.CreateBatchAsync(request.FileName, uniqueDnis, ct);

        await _queue.EnqueueBulkAsync(QueueNames.UniversityQueue,
            uniqueDnis.Select(d => $"{batch.Id}:{d}"), ct);

        return new BulkUploadResponse(batch.Id, request.FileName, batch.TotalDnis, $"Se cargaron {batch.TotalDnis} DNIs correctamente");
    }
}

public sealed class GetStatusUseCase
{
    private readonly IDniRecordRepository _repository;

    public GetStatusUseCase(IDniRecordRepository repository)
    {
        _repository = repository;
    }

    public async Task<StatusResponse> ExecuteAsync(CancellationToken ct)
    {
        var counts = await _repository.GetCountsByStatusAsync(ct);
        var total = await _repository.GetTotalCountAsync(ct);
        var retryableCount = await _repository.CountRetryableAsync(ct);
        var hasActive = await _repository.HasActiveWorkAsync(ct);

        int Get(DniStatus s) => counts.TryGetValue(s, out var v) ? v : 0;

        var completed = Get(DniStatus.FoundUniversity) + Get(DniStatus.FoundInstitute) + Get(DniStatus.NotFound) + Get(DniStatus.Failed);
        var inProgress = Get(DniStatus.CheckingUniversity) + Get(DniStatus.CheckingInstitute);

        return new StatusResponse
        {
            Total = total,
            Completed = completed,
            InProgress = inProgress,
            ProgressPercent = total > 0 ? Math.Round((double)completed / total * 100, 1) : 0,
            Counts = counts.ToDictionary(kv => kv.Key.ToString(), kv => kv.Value),
            Pipeline = new PipelineInfo
            {
                University = new StageInfo
                {
                    Pending = Get(DniStatus.Pending),
                    Processing = Get(DniStatus.CheckingUniversity),
                    Found = Get(DniStatus.FoundUniversity),
                    DerivedToNext = Get(DniStatus.CheckingInstitute),
                },
                Institute = new StageInfo
                {
                    Pending = Get(DniStatus.CheckingInstitute),
                    Processing = Get(DniStatus.CheckingInstitute),
                    Found = Get(DniStatus.FoundInstitute),
                    NotFound = Get(DniStatus.NotFound),
                },
            },
            Retry = new RetryInfo
            {
                Retryable = retryableCount,
                PipelineIdle = !hasActive && total > 0,
                CanRetry = !hasActive && total > 0 && retryableCount > 0,
            },
        };
    }
}

public sealed class ExportExcelUseCase
{
    private readonly IDniRecordRepository _repository;

    public ExportExcelUseCase(IDniRecordRepository repository)
    {
        _repository = repository;
    }

    public async Task<byte[]> ExecuteAsync(int? batchId, CancellationToken ct)
    {
        var records = await _repository.GetRecordsAsync(batchId: batchId, limit: 50000, ct: ct);
        if (records.Count == 0) throw new InvalidOperationException("No hay resultados para descargar.");

        var dtos = records.Select(DniRecordDto.FromEntity).ToList();
        using var workbook = new XLWorkbook();
        var ws = workbook.Worksheets.Add("Resultados");

        var headers = new[] { "DNI", "Estado", "Sunedu Nombres", "Sunedu Grado", "Sunedu Institucion", "Sunedu Fecha", "Minedu Nombres", "Minedu Titulo", "Minedu Institucion", "Minedu Fecha", "Error", "Lote", "Creado", "Reintentos" };
        for (int i = 0; i < headers.Length; i++) ws.Cell(1, i + 1).Value = headers[i];

        for (int row = 0; row < dtos.Count; row++)
        {
            var d = dtos[row];
            int r = row + 2;
            ws.Cell(r, 1).Value = d.Dni;
            ws.Cell(r, 2).Value = d.Status;
            ws.Cell(r, 3).Value = d.SuneduNombres ?? "";
            ws.Cell(r, 4).Value = d.SuneduGrado ?? "";
            ws.Cell(r, 5).Value = d.SuneduInstitucion ?? "";
            ws.Cell(r, 6).Value = d.SuneduFechaDiploma ?? "";
            ws.Cell(r, 7).Value = d.MineduNombres ?? "";
            ws.Cell(r, 8).Value = d.MineduTitulo ?? "";
            ws.Cell(r, 9).Value = d.MineduInstitucion ?? "";
            ws.Cell(r, 10).Value = d.MineduFecha ?? "";
            ws.Cell(r, 11).Value = d.ErrorMessage ?? "";
            ws.Cell(r, 12).Value = d.BatchId;
            ws.Cell(r, 13).Value = d.CreatedAt ?? "";
            ws.Cell(r, 14).Value = d.RetryCount;
        }

        ws.Columns().AdjustToContents();
        using var ms = new MemoryStream();
        workbook.SaveAs(ms);
        return ms.ToArray();
    }
}

public sealed class RetryUseCase
{
    private readonly IDniRecordRepository _repository;
    private readonly IQueueService _queue;

    public RetryUseCase(IDniRecordRepository repository, IQueueService queue)
    {
        _repository = repository;
        _queue = queue;
    }

    public async Task<RetryResponse> ExecuteAsync(CancellationToken ct)
    {
        if (await _repository.HasActiveWorkAsync(ct))
            throw new InvalidOperationException("Aún hay registros en proceso.");

        var retried = await _repository.RetryFailedAsync(ct);
        if (retried == 0) return new RetryResponse("No hay registros para reintentar", 0);

        var records = await _repository.GetRecordsAsync(status: DniStatus.Pending, limit: 50000, ct: ct);
        await _queue.EnqueueBulkAsync(QueueNames.UniversityQueue, records.Select(r => $"{r.BatchId}:{r.Dni}"), ct);

        return new RetryResponse($"Se re-encolaron {retried} registros", retried);
    }
}

public sealed record RetryResponse(string Message, int Retried);
