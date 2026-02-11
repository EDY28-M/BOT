namespace DniAutomation.Domain.Interfaces;

public interface IQueueService
{
    Task EnqueueAsync(string queueName, string value, CancellationToken ct = default);
    Task EnqueueBulkAsync(string queueName, IEnumerable<string> values, CancellationToken ct = default);
    Task<string?> DequeueAsync(string queueName, TimeSpan timeout, CancellationToken ct = default);
    Task<long> GetQueueLengthAsync(string queueName, CancellationToken ct = default);
    Task PublishSignalAsync(string channel, string message, CancellationToken ct = default);
    Task SubscribeSignalAsync(string channel, Action<string> handler, CancellationToken ct = default);
    Task UnsubscribeAsync(string channel, CancellationToken ct = default);
}

public static class QueueNames
{
    public const string UniversityQueue = "queue:university";
    public const string InstituteQueue = "queue:institute";
    public const string SystemSignals = "signal:system";
}

public static class SystemSignals
{
    public const string Pause = "PAUSE";
    public const string Resume = "RESUME";
    public const string Stop = "STOP";
}
