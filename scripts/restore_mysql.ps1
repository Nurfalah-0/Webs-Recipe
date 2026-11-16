[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "Load-EnvFile.ps1")
Import-LocalEnvironment (Join-Path $PSScriptRoot "..\.env")

foreach ($name in @("DB_NAME", "DB_USER")) {
    if ([string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable($name))) {
        throw "Set $name in the current environment before running this script."
    }
}

$backupPath = (Resolve-Path -LiteralPath $BackupFile -ErrorAction Stop).Path
$hashPath = "$backupPath.sha256"
if (-not (Test-Path -LiteralPath $hashPath)) {
    throw "Required backup checksum file not found: $hashPath"
}
$expectedHash = ((Get-Content -LiteralPath $hashPath -Raw).Trim() -split "\s+")[0]
$actualHash = (Get-FileHash -LiteralPath $backupPath -Algorithm SHA256).Hash
if ($actualHash -ne $expectedHash) {
    throw "Backup checksum verification failed."
}
$confirmation = Read-Host "This restores into '$($env:DB_NAME)'. Type RESTORE to continue"
if ($confirmation -cne "RESTORE") {
    throw "Restore cancelled."
}

$mysql = Get-Command mysql.exe -ErrorAction Stop
$hostName = if ($env:DB_HOST) { $env:DB_HOST } else { "127.0.0.1" }
$port = if ($env:DB_PORT) { $env:DB_PORT } else { "3306" }
$previousMysqlPassword = $env:MYSQL_PWD
try {
    if ($null -eq $env:DB_PASSWORD) {
        Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
    }
    else {
        $env:MYSQL_PWD = $env:DB_PASSWORD
    }
    $mysqlArguments = @(
        "--host=$hostName",
        "--port=$port",
        "--user=$($env:DB_USER)",
        "--database=$($env:DB_NAME)"
    ) -join " "
    $command = "`"$($mysql.Source)`" $mysqlArguments < `"$backupPath`""
    & $env:ComSpec /d /c $command
    if ($LASTEXITCODE -ne 0) {
        throw "mysql restore failed with exit code $LASTEXITCODE."
    }
}
finally {
    if ($null -eq $previousMysqlPassword) {
        Remove-Item Env:\MYSQL_PWD -ErrorAction SilentlyContinue
    }
    else {
        $env:MYSQL_PWD = $previousMysqlPassword
    }
}

Write-Output "Database restore completed from: $backupPath"
