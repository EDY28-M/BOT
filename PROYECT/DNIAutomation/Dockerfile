# Dockerfile for single-project DniAutomation

FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY ["DNIAutomation.csproj", "."]
RUN dotnet restore "./DNIAutomation.csproj"
COPY . .
WORKDIR "/src/."
RUN dotnet build "DNIAutomation.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "DNIAutomation.csproj" -c Release -o /app/publish

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
WORKDIR /app
COPY --from=publish /app/publish .

# Install Playwright dependencies and Tesseract OCR
RUN apt-get update && apt-get install -y wget && \
    apt-get install -y libglib2.0-0 libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 libx11-xcb1 fonts-liberation fonts-noto-color-emoji && \
    apt-get install -y tesseract-ocr tesseract-ocr-spa libtesseract-dev && \
    rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["dotnet", "DNIAutomation.dll"]
