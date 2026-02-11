using DniAutomation.Application.UseCases;
using DniAutomation.Infrastructure.Persistence;
using DniAutomation.Infrastructure.Scraping;
using DniAutomation.Workers;
using DniAutomation.Domain.Interfaces;
using Microsoft.EntityFrameworkCore;
using StackExchange.Redis;
using Serilog;

var builder = WebApplication.CreateBuilder(args);

// Logging
Log.Logger = new LoggerConfiguration()
    .WriteTo.Console()
    .WriteTo.File("logs/log-.txt", rollingInterval: RollingInterval.Day)
    .CreateLogger();

builder.Host.UseSerilog();

// Services
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddOpenApi(); // Built-in OpenAPI
builder.Services.AddCors(options =>
{
    options.AddPolicy("AllowFrontend",
        b => b.WithOrigins("http://localhost:3000") // Vite dev server
              .AllowAnyMethod()
              .AllowAnyHeader());
});

// Infrastructure
var connStr = builder.Configuration.GetConnectionString("DefaultConnection") 
    ?? "Server=localhost;Database=DniAutomation;Trusted_Connection=True;TrustServerCertificate=True;";
builder.Services.AddDbContext<AppDbContext>(o => o.UseSqlServer(connStr));

builder.Services.AddScoped<IDniRecordRepository, DniRecordRepository>();

var redisStr = builder.Configuration.GetConnectionString("Redis") ?? "local";

if (redisStr == "local")
{
    builder.Services.AddSingleton<IQueueService, InMemoryQueueService>();
}
else
{
    builder.Services.AddSingleton<IConnectionMultiplexer>(sp => ConnectionMultiplexer.Connect(redisStr));
    builder.Services.AddSingleton<IQueueService, RedisQueueService>();
}

// Scrapers
builder.Services.AddTransient<SuneduScraper>();
builder.Services.AddTransient<MineduScraper>();

// Application Use Cases
builder.Services.AddScoped<BulkUploadUseCase>();
builder.Services.AddScoped<GetStatusUseCase>();
builder.Services.AddScoped<ExportExcelUseCase>();
builder.Services.AddScoped<RetryUseCase>();

// Workers
builder.Services.AddHostedService<UniversityWorker>();
builder.Services.AddHostedService<InstituteWorker>();

var app = builder.Build();

// Auto-migrate on startup for convenience (but proper way is via tools)
// We'll keep EnsureCreatedAsync to satisfy "migra a mi bd" without manual steps if user runs app.
// But for EF tools to work, we need to handle DesignTime factory if Program.cs is complex.
// Since we are using standard Program.cs, ef tools should work if we don't have runtime errors on build.
using (var scope = app.Services.CreateScope())
{
    var services = scope.ServiceProvider;
    try
    {
        var context = services.GetRequiredService<AppDbContext>();
        // context.Database.Migrate(); // Use Migrate() instead of EnsureCreated() if using migrations
        await context.Database.MigrateAsync(); // Use Migrate for proper schema updates
    }
    catch (Exception ex)
    {
        Log.Error(ex, "An error occurred creating the DB.");
    }
}

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi(); // Built-in swagger.json endpoint
}

app.UseCors("AllowFrontend");
app.UseAuthorization();
app.MapControllers();

app.Run();
