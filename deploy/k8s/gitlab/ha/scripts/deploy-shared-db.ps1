# Deploy shared PostgreSQL + Redis for GitLab HA (namespace gitlab).
param(
    [string]$KubeConfig = "$env:USERPROFILE\.kube\config-homelab",
    [switch]$SkipSecret
)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Ha = Join-Path $Root "ha"
$env:KUBECONFIG = $KubeConfig

Write-Host "==> Deploy shared PostgreSQL + Redis (namespace gitlab)"

if (-not $SkipSecret) {
    $existing = $null
    try {
        $existing = kubectl -n gitlab get secret gitlab-postgresql-secret -o name 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { $existing = $null }
    } catch {
        $existing = $null
    }
    if (-not $existing) {
        $pw = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
        kubectl -n gitlab create secret generic gitlab-postgresql-secret `
            --from-literal=postgresql-password="$pw"
        Write-Host "Created gitlab-postgresql-secret (password not printed)."
    } else {
        Write-Host "gitlab-postgresql-secret already exists - skipping."
    }
}

kubectl apply -f (Join-Path $Ha "external-postgresql.yaml")
kubectl apply -f (Join-Path $Ha "external-redis.yaml")
kubectl apply -f (Join-Path (Join-Path $Root "omnibus") "pdb.yaml")

Write-Host "Waiting for PostgreSQL..."
kubectl -n gitlab wait --for=condition=ready pod -l app=gitlab-postgresql --timeout=300s
Write-Host "Waiting for Redis..."
kubectl -n gitlab wait --for=condition=available deployment/gitlab-redis --timeout=180s
kubectl -n gitlab get pods -l 'app in (gitlab-postgresql,gitlab-redis)' -o wide
