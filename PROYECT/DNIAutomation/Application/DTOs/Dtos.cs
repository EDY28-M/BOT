using System.Text.Json;
using DniAutomation.Domain.Entities;
using DniAutomation.Domain.Enums;

namespace DniAutomation.Application.DTOs;

public sealed record BulkUploadRequest(string FileName, List<string> Dnis);
public sealed record BulkUploadResponse(int BatchId, string FileName, int TotalDnis, string Message);

public sealed class StatusResponse
{
    public int Total { get; init; }
    public int Completed { get; init; }
    public int InProgress { get; init; }
    public double ProgressPercent { get; init; }
    public Dictionary<string, int> Counts { get; init; } = new();
    public PipelineInfo Pipeline { get; init; } = new();
    public RetryInfo Retry { get; init; } = new();
}

public sealed class PipelineInfo
{
    public StageInfo University { get; init; } = new();
    public StageInfo Institute { get; init; } = new();
}

public sealed class StageInfo
{
    public int Pending { get; init; }
    public int Processing { get; init; }
    public int Found { get; init; }
    public int Errors { get; init; }
    public int DerivedToNext { get; init; }
    public int NotFound { get; init; }
}

public sealed class RetryInfo
{
    public int Retryable { get; init; }
    public bool PipelineIdle { get; init; }
    public bool CanRetry { get; init; }
}

public sealed record DniRecordDto
{
    public int Id { get; init; }
    public int BatchId { get; init; }
    public string Dni { get; init; } = string.Empty;
    public string Status { get; init; } = string.Empty;
    public int RetryCount { get; init; }
    public string? ErrorMessage { get; init; }
    public string? CreatedAt { get; init; }
    public string? UpdatedAt { get; init; }

    public string? SuneduNombres { get; init; }
    public string? SuneduGrado { get; init; }
    public string? SuneduInstitucion { get; init; }
    public string? SuneduFechaDiploma { get; init; }

    public string? MineduNombres { get; init; }
    public string? MineduTitulo { get; init; }
    public string? MineduInstitucion { get; init; }
    public string? MineduFecha { get; init; }

    public static DniRecordDto FromEntity(DniRecord r)
    {
        var dto = new DniRecordDto
        {
            Id = r.Id,
            BatchId = r.BatchId,
            Dni = r.Dni,
            Status = r.Status.ToString(),
            RetryCount = r.RetryCount,
            ErrorMessage = r.ErrorMessage,
            CreatedAt = r.CreatedAt.ToString("o"),
            UpdatedAt = r.UpdatedAt.ToString("o"),
        };

        if (!string.IsNullOrEmpty(r.PayloadSunedu))
        {
            try
            {
                using var doc = JsonDocument.Parse(r.PayloadSunedu);
                var root = doc.RootElement;
                return dto with
                {
                    SuneduNombres = root.TryGetProperty("nombres", out var n) ? n.GetString() : null,
                    SuneduGrado = root.TryGetProperty("grado_o_titulo", out var g) ? g.GetString() : null,
                    SuneduInstitucion = root.TryGetProperty("institucion", out var i) ? i.GetString() : null,
                    SuneduFechaDiploma = root.TryGetProperty("fecha_diploma", out var f) ? f.GetString() : null,
                    MineduNombres = TryExtractMinedu(r.PayloadMinedu, "nombre_completo"),
                    MineduTitulo = TryExtractMinedu(r.PayloadMinedu, "titulo"),
                    MineduInstitucion = TryExtractMinedu(r.PayloadMinedu, "institucion"),
                    MineduFecha = TryExtractMinedu(r.PayloadMinedu, "fecha_expedicion"),
                };
            }
            catch { }
        }

        if (!string.IsNullOrEmpty(r.PayloadMinedu))
        {
            try
            {
                return dto with
                {
                    MineduNombres = TryExtractMinedu(r.PayloadMinedu, "nombre_completo"),
                    MineduTitulo = TryExtractMinedu(r.PayloadMinedu, "titulo"),
                    MineduInstitucion = TryExtractMinedu(r.PayloadMinedu, "institucion"),
                    MineduFecha = TryExtractMinedu(r.PayloadMinedu, "fecha_expedicion"),
                };
            }
            catch { }
        }

        return dto;
    }

    private static string? TryExtractMinedu(string? json, string property)
    {
        if (string.IsNullOrEmpty(json)) return null;
        try
        {
            using var doc = JsonDocument.Parse(json);
            return doc.RootElement.TryGetProperty(property, out var v) ? v.GetString() : null;
        }
        catch { return null; }
    }
}
