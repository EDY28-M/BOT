using DniAutomation.Domain.Entities;
using DniAutomation.Domain.Enums;

namespace DniAutomation.Domain.Interfaces;

public interface IDniRecordRepository
{
    Task<Batch> CreateBatchAsync(string fileName, IReadOnlyList<string> dnis, CancellationToken ct = default);
    Task<List<Batch>> GetBatchesAsync(CancellationToken ct = default);
    Task<DniRecord?> DequeueNextAsync(DniStatus fromStatus, DniStatus toStatus, CancellationToken ct = default);
    Task UpdateStatusAsync(int recordId, DniStatus newStatus, string? payloadSunedu = null, string? payloadMinedu = null, string? errorMessage = null, CancellationToken ct = default);
    Task<Dictionary<DniStatus, int>> GetCountsByStatusAsync(CancellationToken ct = default);
    Task<int> GetTotalCountAsync(CancellationToken ct = default);
    Task<List<DniRecord>> GetRecordsAsync(DniStatus? status = null, int? batchId = null, int limit = 500, int offset = 0, CancellationToken ct = default);
    Task<bool> HasActiveWorkAsync(CancellationToken ct = default);
    Task<int> CountRetryableAsync(CancellationToken ct = default);
    Task<int> RetryFailedAsync(CancellationToken ct = default);
    Task<(int uni, int inst)> RecoverStuckAsync(CancellationToken ct = default);
    Task<(int records, int batches)> CleanAllAsync(CancellationToken ct = default);
}
