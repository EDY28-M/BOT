namespace DniAutomation.Domain.Entities;

public class Batch
{
    public int Id { get; set; }
    public string FileName { get; set; } = string.Empty;
    public int TotalDnis { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public ICollection<DniRecord> Records { get; set; } = new List<DniRecord>();
}
