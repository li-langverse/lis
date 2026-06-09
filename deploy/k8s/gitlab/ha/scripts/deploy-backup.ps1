# Apply GitLab backup CronJobs + PVC (homelab engine).
param(
    [string]$KubeConfig = "$env:USERPROFILE\.kube\config-homelab",
    [switch]$SkipTest
)

$ErrorActionPreference = "Stop"
$env:KUBECONFIG = $KubeConfig
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$BackupDir = Join-Path $Root "ha\backup"

Write-Host "==> Pre-flight"
kubectl -n gitlab get secret gitlab-postgresql-secret -o name 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "gitlab-postgresql-secret missing - run ha\scripts\deploy-shared-db.ps1 first."
}
kubectl -n gitlab get pod gitlab-0 -o name

Write-Host "==> Apply backup manifests"
$files = @(
    "pvc.yaml",
    "rbac.yaml",
    "configmap-scripts.yaml",
    "cronjob-db-hourly.yaml",
    "cronjob-full-daily.yaml"
)
foreach ($f in $files) {
    kubectl apply -f (Join-Path $BackupDir $f)
}

Write-Host "==> CronJobs"
kubectl -n gitlab get cronjob -l app=gitlab-backup
kubectl -n gitlab get pvc gitlab-backup-storage

if (-not $SkipTest) {
    Write-Host "==> Run manual test jobs"
    kubectl -n gitlab delete job gitlab-backup-db-test gitlab-backup-rotation-test --ignore-not-found
    kubectl apply -f (Join-Path $BackupDir "job-test-backup.yaml")
    kubectl -n gitlab wait --for=condition=complete job/gitlab-backup-rotation-test --timeout=120s
    kubectl -n gitlab wait --for=condition=complete job/gitlab-backup-db-test --timeout=600s
    Write-Host "--- rotation test ---"
    kubectl -n gitlab logs job/gitlab-backup-rotation-test
    Write-Host "--- db backup test ---"
    kubectl -n gitlab logs job/gitlab-backup-db-test
}

Write-Host 'Done. Backups on PVC gitlab-backup-storage at /backups/hourly, daily, weekly, full.'
