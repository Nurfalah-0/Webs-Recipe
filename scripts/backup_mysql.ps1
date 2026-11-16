[CmdletBinding()]
param(
    [string]$BackupDirectory = (Join-Path $PSScriptRoot "..\backups")
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "Load-EnvFile.ps1")
Import-LocalEnvironment (Join-Path $PSScriptRoot "..\.env")

foreach ($name in @("DB_NAME", "DB_USER")) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) {
        throw "Set $name in the current environment before running this script."
    }
}

$dump = Get-Command mysqldump.exe -ErrorAction Stop
$hostName = if ($env:DB_HOST) { $env:DB_HOST } else { "127.0.0.1" }
$port = if ($env:DB_PORT) { $env:DB_PORT } else { "3306" }
$backupPath = Join-Path ([System.IO.Path]::GetFullPath($BackupDirectory)) (
    "{0}_{1:yyyyMMdd_HHmmss}.sql" -f $env:DB_NAME, (Get-Date)
)
$backupParent = Split-Path -Parent $backupPath
New-Item -ItemType Directory -Path $backupParent -Force | Out-Null

$previousMysqlPassword = $env:MYSQL_PWD
try {
    if ($null -eq $env:DB_PASSWORD) {
        Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
    }
    else {
        $env:MYSQL_PWD = $env:DB_PASSWORD
    }
    & $dump.Source `
        "--host=$hostName" `
        "--port=$port" `
        "--user=$($env:DB_USER)" `
        "--single-transaction" `
        "--routines" `
        "--triggers" `
        "--result-file=$backupPath" `
        "--databases" `
        $env:DB_NAME

    if ($LASTEXITCODE -ne 0) {
        throw "mysqldump failed with exit code $LASTEXITCODE."
    }
    $hash = (Get-FileHash -LiteralPath $backupPath -Algorithm SHA256).Hash
    Set-Content -LiteralPath "$backupPath.sha256" -Value "$hash  $(Split-Path -Leaf $backupPath)" -Encoding ascii
}
finally {
    if ($null -eq $previousMysqlPassword) {
        Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
    }
    else {
        $env:MYSQL_PWD = $previousMysqlPassword
    }
}

Write-Output "Database backup created: $backupPath"
