using DniAutomation.Domain.Enums;
using DniAutomation.Domain.Interfaces;
using DniAutomation.Infrastructure.Scraping;
using StackExchange.Redis;

namespace DniAutomation.Workers;

public sealed class UniversityWorker : BackgroundService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly IQueueService _queue;
    private readonly ILogger<UniversityWorker> _logger;
    private volatile bool _paused;
    private volatile bool _stopped;

    public UniversityWorker(IServiceScopeFactory f, IQueueService q, ILogger<UniversityWorker> l) { _scopeFactory = f; _queue = q; _logger = l; }

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        // Resilient loop: If Redis fails, we retry instead of crashing the app
        while (!ct.IsCancellationRequested && !_stopped)
        {
            try
            {
                // Attempt to subscribe (will fail if Redis is down)
                await _queue.SubscribeSignalAsync(QueueNames.SystemSignals, s => 
                { 
                    if (s == SystemSignals.Pause) _paused = true; 
                    else if (s == SystemSignals.Resume) _paused = false; 
                    else if (s == SystemSignals.Stop) _stopped = true; 
                }, ct);

                _logger.LogInformation("UniversityWorker connected to Redis and signals.");

                // Scraper initialization (Playwright)
                await using var scraper = new SuneduScraper();
                await scraper.InitAsync();

                // Processing loop
                while (!ct.IsCancellationRequested && !_stopped)
                {
                    if (_paused) { await Task.Delay(1000, ct); continue; }

                    try
                    {
                        var val = await _queue.DequeueAsync(QueueNames.UniversityQueue, TimeSpan.FromSeconds(5), ct);
                        if (val is null) { await Task.Delay(1000, ct); continue; }

                        var parts = val.Split(':', 2);
                        if (parts.Length != 2 || !int.TryParse(parts[0], out var batchId)) continue;
                        var dni = parts[1];

                        using var scope = _scopeFactory.CreateScope();
                        var repo = scope.ServiceProvider.GetRequiredService<IDniRecordRepository>();

                        // Improved checks: Use explicit status transition
                        var rec = await repo.DequeueNextAsync(DniStatus.Pending, DniStatus.CheckingUniversity, ct);
                        if (rec is null) continue; // Race condition or already taken

                        var (found, payload, reason) = await scraper.ProcessDniAsync(rec.Dni);
                        if (found) await repo.UpdateStatusAsync(rec.Id, DniStatus.FoundUniversity, payloadSunedu: payload, ct: ct);
                        else 
                        {
                            await repo.UpdateStatusAsync(rec.Id, DniStatus.CheckingInstitute, ct: ct);
                            await _queue.EnqueueAsync(QueueNames.InstituteQueue, $"{rec.BatchId}:{rec.Dni}", ct);
                        }
                    }
                    catch (RedisConnectionException rex)
                    {
                        _logger.LogError(rex, "Redis connection lost during processing. Reconnecting...");
                        break; // Break inner loop to reconnect/subscribe
                    }
                    catch (Exception ex) 
                    { 
                        _logger.LogError(ex, "Error processing DNI"); 
                    }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "UniversityWorker failed to initialize (likely Redis down). Retrying in 10s...");
                try { await Task.Delay(10000, ct); } catch { /* ignore cancel */ }
            }
        }
    }
}

public sealed class InstituteWorker : BackgroundService
{
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly IQueueService _queue;
    private readonly ILogger<InstituteWorker> _logger;
    private volatile bool _paused;
    private volatile bool _stopped;

    public InstituteWorker(IServiceScopeFactory f, IQueueService q, ILogger<InstituteWorker> l) { _scopeFactory = f; _queue = q; _logger = l; }

    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        while (!ct.IsCancellationRequested && !_stopped)
        {
            try
            {
                await _queue.SubscribeSignalAsync(QueueNames.SystemSignals, s => 
                { 
                    if (s == SystemSignals.Pause) _paused = true; 
                    else if (s == SystemSignals.Resume) _paused = false; 
                    else if (s == SystemSignals.Stop) _stopped = true; 
                }, ct);

                _logger.LogInformation("InstituteWorker connected to Redis.");

                await using var scraper = new MineduScraper();
                await scraper.InitAsync();

                while (!ct.IsCancellationRequested && !_stopped)
                {
                    if (_paused) { await Task.Delay(1000, ct); continue; }

                    try
                    {
                        var val = await _queue.DequeueAsync(QueueNames.InstituteQueue, TimeSpan.FromSeconds(5), ct);
                        if (val is null) { await Task.Delay(1000, ct); continue; }

                        var parts = val.Split(':', 2);
                        if (parts.Length != 2 || !int.TryParse(parts[0], out var batchId)) continue;
                        var dni = parts[1];

                        using var scope = _scopeFactory.CreateScope();
                        var repo = scope.ServiceProvider.GetRequiredService<IDniRecordRepository>();

                        var records = await repo.GetRecordsAsync(DniStatus.CheckingInstitute, batchId, 1, 0, ct);
                        var rec = records.FirstOrDefault(r => r.Dni == dni);
                        if (rec is null) continue;

                        var (found, payload, reason) = await scraper.ProcessDniAsync(rec.Dni);
                        if (found) await repo.UpdateStatusAsync(rec.Id, DniStatus.FoundInstitute, payloadMinedu: payload, ct: ct);
                        else await repo.UpdateStatusAsync(rec.Id, DniStatus.NotFound, errorMessage: reason, ct: ct);
                    }
                    catch (RedisConnectionException rex)
                    {
                         _logger.LogError(rex, "Redis connection lost. Reconnecting...");
                         break;
                    }
                    catch (Exception ex) { _logger.LogError(ex, "Error processing"); }
                }
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "InstituteWorker failed (likely Redis down). Retrying in 10s...");
                try { await Task.Delay(10000, ct); } catch { }
            }
        }
    }
}
