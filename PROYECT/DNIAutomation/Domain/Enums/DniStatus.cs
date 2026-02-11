namespace DniAutomation.Domain.Enums;

public enum DniStatus
{
    Pending = 0,
    CheckingUniversity = 1,
    FoundUniversity = 2,
    CheckingInstitute = 3,
    FoundInstitute = 4,
    NotFound = 5,
    Failed = 6
}

public static class DniStatusExtensions
{
    public static bool IsTerminal(this DniStatus s) =>
        s is DniStatus.FoundUniversity or DniStatus.FoundInstitute or DniStatus.NotFound or DniStatus.Failed;

    public static bool IsActive(this DniStatus s) =>
        s is DniStatus.Pending or DniStatus.CheckingUniversity or DniStatus.CheckingInstitute;

    public static bool IsRetryable(this DniStatus s) =>
        s is DniStatus.NotFound or DniStatus.Failed;
}
