using DniAutomation.Domain.Entities;
using DniAutomation.Domain.Enums;
using DniAutomation.Domain.Interfaces;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;
using StackExchange.Redis;

namespace DniAutomation.Infrastructure.Persistence;

public sealed class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<DniRecord> DniRecords => Set<DniRecord>();
    public DbSet<Batch> Batches => Set<Batch>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Batch>(b =>
        {
            b.HasKey(x => x.Id);
            b.Property(x => x.FileName).HasMaxLength(255).IsRequired();
            b.HasMany(x => x.Records).WithOne(r => r.Batch).HasForeignKey(r => r.BatchId).OnDelete(DeleteBehavior.Cascade);
        });

        modelBuilder.Entity<DniRecord>(r =>
        {
            r.HasKey(x => x.Id);
            r.Property(x => x.Dni).HasMaxLength(15).IsRequired();
            r.Property(x => x.Status).HasConversion<string>().HasMaxLength(30).IsRequired();
            r.HasIndex(x => x.Dni);
            r.HasIndex(x => x.Status);
            r.HasIndex(x => new { x.Status, x.Id });
        });
    }
}

public sealed class DniRecordRepository : IDniRecordRepository
{
    private readonly AppDbContext _db;
    private readonly ILogger<DniRecordRepository> _logger;

    public DniRecordRepository(AppDbContext db, ILogger<DniRecordRepository> logger)
    {
        _db = db;
        _logger = logger;
    }

    public async Task<Batch> CreateBatchAsync(string fileName, IReadOnlyList<string> dnis, CancellationToken ct)
    {
        var batch = new Batch { FileName = fileName, TotalDnis = dnis.Count };
        _db.Batches.Add(batch);
        await _db.SaveChangesAsync(ct);

        var records = dnis.Select(d => new DniRecord { BatchId = batch.Id, Dni = d, Status = DniStatus.Pending }).ToList();
        _db.DniRecords.AddRange(records);
        await _db.SaveChangesAsync(ct);
        return batch;
    }

    public async Task<List<Batch>> GetBatchesAsync(CancellationToken ct) =>
        await _db.Batches.OrderByDescending(b => b.Id).ToListAsync(ct);

    public async Task<DniRecord?> DequeueNextAsync(DniStatus fromStatus, DniStatus toStatus, CancellationToken ct)
    {
        var records = await _db.DniRecords
            .FromSqlRaw(@"UPDATE TOP(1) DniRecords SET Status = {0}, UpdatedAt = {1} OUTPUT INSERTED.* WHERE Status = {2} AND Id = (SELECT TOP(1) Id FROM DniRecords WHERE Status = {2} ORDER BY Id ASC)",
                toStatus.ToString(), DateTime.UtcNow, fromStatus.ToString())
            .AsNoTracking().ToListAsync(ct);
        return records.FirstOrDefault();
    }

    public async Task UpdateStatusAsync(int recordId, DniStatus newStatus, string? payloadSunedu, string? payloadMinedu, string? errorMessage, CancellationToken ct)
    {
        var record = await _db.DniRecords.FindAsync(new object[] { recordId }, ct);
        if (record is not null)
        {
            record.Status = newStatus;
            record.UpdatedAt = DateTime.UtcNow;
            if (payloadSunedu is not null) record.PayloadSunedu = payloadSunedu;
            if (payloadMinedu is not null) record.PayloadMinedu = payloadMinedu;
            if (errorMessage is not null) record.ErrorMessage = errorMessage;
            await _db.SaveChangesAsync(ct);
        }
    }

    public async Task<Dictionary<DniStatus, int>> GetCountsByStatusAsync(CancellationToken ct) =>
        await _db.DniRecords.GroupBy(r => r.Status).Select(g => new { Status = g.Key, Count = g.Count() }).ToDictionaryAsync(x => x.Status, x => x.Count, ct);

    public async Task<int> GetTotalCountAsync(CancellationToken ct) => await _db.DniRecords.CountAsync(ct);

    public async Task<List<DniRecord>> GetRecordsAsync(DniStatus? status, int? batchId, int limit, int offset, CancellationToken ct)
    {
        var q = _db.DniRecords.AsQueryable();
        if (status.HasValue) q = q.Where(r => r.Status == status.Value);
        if (batchId.HasValue) q = q.Where(r => r.BatchId == batchId.Value);
        return await q.OrderBy(r => r.Id).Skip(offset).Take(limit).AsNoTracking().ToListAsync(ct);
    }

    public async Task<bool> HasActiveWorkAsync(CancellationToken ct) =>
        await _db.DniRecords.AnyAsync(r => r.Status == DniStatus.Pending || r.Status == DniStatus.CheckingUniversity || r.Status == DniStatus.CheckingInstitute, ct);

    public async Task<int> CountRetryableAsync(CancellationToken ct) =>
        await _db.DniRecords.CountAsync(r => r.Status == DniStatus.NotFound || r.Status == DniStatus.Failed, ct);

    public async Task<int> RetryFailedAsync(CancellationToken ct)
    {
        var records = await _db.DniRecords.Where(r => r.Status == DniStatus.NotFound || r.Status == DniStatus.Failed).ToListAsync(ct);
        foreach (var r in records) { r.Status = DniStatus.Pending; r.RetryCount++; r.UpdatedAt = DateTime.UtcNow; r.ErrorMessage = null; }
        await _db.SaveChangesAsync(ct);
        return records.Count;
    }

    public async Task<(int, int)> RecoverStuckAsync(CancellationToken ct)
    {
        var uni = await _db.DniRecords.Where(r => r.Status == DniStatus.CheckingUniversity).ToListAsync(ct);
        foreach (var r in uni) r.Status = DniStatus.Pending;
        var inst = await _db.DniRecords.Where(r => r.Status == DniStatus.CheckingInstitute).ToListAsync(ct);
        foreach (var r in inst) r.Status = DniStatus.CheckingInstitute; // Re-queue for institute check, not full reset
        await _db.SaveChangesAsync(ct);
        return (uni.Count, inst.Count);
    }

    public async Task<(int, int)> CleanAllAsync(CancellationToken ct)
    {
        var r = await _db.DniRecords.ExecuteDeleteAsync(ct);
        var b = await _db.Batches.ExecuteDeleteAsync(ct);
        return (r, b);
    }
}

public sealed class RedisQueueService : IQueueService, IDisposable
{
    private readonly IConnectionMultiplexer _redis;
    private ISubscriber? _subscriber;

    public RedisQueueService(IConnectionMultiplexer redis) { _redis = redis; }

    public async Task EnqueueAsync(string queueName, string value, CancellationToken ct) =>
        await _redis.GetDatabase().ListLeftPushAsync(queueName, value);

    public async Task EnqueueBulkAsync(string queueName, IEnumerable<string> values, CancellationToken ct)
    {
        var batch = _redis.GetDatabase().CreateBatch();
        foreach (var v in values) _ = batch.ListLeftPushAsync(queueName, v);
        batch.Execute();
    }

    public async Task<string?> DequeueAsync(string queueName, TimeSpan timeout, CancellationToken ct)
    {
        var end = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < end && !ct.IsCancellationRequested)
        {
            var val = await _redis.GetDatabase().ListRightPopAsync(queueName);
            if (val.HasValue) return val.ToString();
            await Task.Delay(200, ct);
        }
        return null;
    }

    public async Task<long> GetQueueLengthAsync(string queueName, CancellationToken ct) =>
        await _redis.GetDatabase().ListLengthAsync(queueName);

    public async Task PublishSignalAsync(string channel, string message, CancellationToken ct) =>
        await _redis.GetSubscriber().PublishAsync(RedisChannel.Literal(channel), message);

    public async Task SubscribeSignalAsync(string channel, Action<string> handler, CancellationToken ct)
    {
        _subscriber = _redis.GetSubscriber();
        await _subscriber.SubscribeAsync(RedisChannel.Literal(channel), (_, msg) => { if (msg.HasValue) handler(msg.ToString()); });
    }

    public async Task UnsubscribeAsync(string channel, CancellationToken ct)
    {
        if (_subscriber is not null) await _subscriber.UnsubscribeAsync(RedisChannel.Literal(channel));
    }

    public void Dispose() { }
}

public sealed class InMemoryQueueService : IQueueService
{
    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, System.Threading.Channels.Channel<string>> _queues = new();
    private readonly System.Collections.Concurrent.ConcurrentDictionary<string, Action<string>> _handlers = new();

    private System.Threading.Channels.Channel<string> GetOrCreate(string name) =>
        _queues.GetOrAdd(name, _ => System.Threading.Channels.Channel.CreateUnbounded<string>());

    public async Task EnqueueAsync(string queueName, string value, CancellationToken ct) =>
        await GetOrCreate(queueName).Writer.WriteAsync(value, ct);

    public async Task EnqueueBulkAsync(string queueName, IEnumerable<string> values, CancellationToken ct)
    {
        var writer = GetOrCreate(queueName).Writer;
        foreach (var v in values) await writer.WriteAsync(v, ct);
    }

    public async Task<string?> DequeueAsync(string queueName, TimeSpan timeout, CancellationToken ct)
    {
        var reader = GetOrCreate(queueName).Reader;
        using var cts = CancellationTokenSource.CreateLinkedTokenSource(ct);
        cts.CancelAfter(timeout);
        try
        {
            if (await reader.WaitToReadAsync(cts.Token))
            {
                if (reader.TryRead(out var item)) return item;
            }
        }
        catch (OperationCanceledException) { }
        return null;
    }

    public Task<long> GetQueueLengthAsync(string queueName, CancellationToken ct) =>
        Task.FromResult((long)(_queues.TryGetValue(queueName, out var c) ? c.Reader.Count : 0));

    public Task PublishSignalAsync(string channel, string message, CancellationToken ct)
    {
        if (_handlers.TryGetValue(channel, out var handler)) handler(message);
        return Task.CompletedTask;
    }

    public Task SubscribeSignalAsync(string channel, Action<string> handler, CancellationToken ct)
    {
        _handlers.AddOrUpdate(channel, handler, (_, existing) => existing + handler);
        return Task.CompletedTask;
    }

    public Task UnsubscribeAsync(string channel, CancellationToken ct)
    {
        _handlers.TryRemove(channel, out _);
        return Task.CompletedTask;
    }
}
