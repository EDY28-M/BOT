using DniAutomation.Domain.Enums;

namespace DniAutomation.Domain.Entities;

public class DniRecord
{
    public int Id { get; set; }
    public int BatchId { get; set; }
    public string Dni { get; set; } = string.Empty;
    public DniStatus Status { get; set; } = DniStatus.Pending;
    public int RetryCount { get; set; }
    public string? PayloadSunedu { get; set; }
    public string? PayloadMinedu { get; set; }
    public string? ErrorMessage { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAt { get; set; } = DateTime.UtcNow;
    public Batch Batch { get; set; } = null!;
}
