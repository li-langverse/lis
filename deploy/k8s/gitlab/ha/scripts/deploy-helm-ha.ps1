# Phase 2: GitLab Helm chart with 2 webservice replicas + shared PostgreSQL/Redis.
# Stops Omnibus StatefulSet first — run migrate-omnibus-external-db.ps1 before this.
param(
    [string]$KubeConfig = "$env:USERPROFILE\.kube\config-homelab",
    [string]$Release = "gitlab",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Ha = Join-Path $Root "ha"
$Values = Join-Path $Ha "values-ha.yaml"
$env:KUBECONFIG = $KubeConfig
$KubeDir = Split-Path $KubeConfig -Parent
$KubeFile = Split-Path $KubeConfig -Leaf

Write-Host "==> Pre-flight: shared DB + backup"
kubectl -n gitlab get svc gitlab-postgresql gitlab-redis
kubectl -n gitlab get secret gitlab-postgresql-secret

Write-Host "==> Scale down Omnibus (frees NodePort 30481 + RAM)"
if (-not $DryRun) {
    kubectl -n gitlab scale statefulset/gitlab --replicas=0
    kubectl -n gitlab wait --for=delete pod/gitlab-0 --timeout=300s 2>$null
}

$helmCache = Join-Path $env:TEMP "helm-cache-gitlab"
New-Item -ItemType Directory -Force -Path $helmCache | Out-Null

$dockerArgs = @(
    "run", "--rm",
    "-v", "${KubeDir}:/root/.kube:ro",
    "-v", "${Ha}:/values:ro",
    "-v", "${helmCache}:/root/.cache/helm",
    "-v", "${helmCache}:/root/.config/helm",
    "-e", "KUBECONFIG=/root/.kube/$KubeFile",
    "alpine/helm"
)

Write-Host "==> Helm repo + install (chart gitlab/gitlab, timeout 20m)"
& docker @dockerArgs repo add gitlab https://charts.gitlab.io/ 2>$null
& docker @dockerArgs repo update

if ($DryRun) {
    & docker @dockerArgs template $Release gitlab/gitlab -f /values/values-ha.yaml --namespace gitlab | Select-Object -First 40
    Write-Host "Dry run — template head shown."
    exit 0
}

& docker @dockerArgs upgrade --install $Release gitlab/gitlab `
    --namespace gitlab `
    --timeout 1200s `
    -f /values/values-ha.yaml

Write-Host "Waiting for webservice pods..."
kubectl -n gitlab wait --for=condition=ready pod -l app=webservice --timeout=1800s
kubectl -n gitlab get pods -l 'app in (webservice,sidekiq,gitaly)' -o wide
kubectl -n gitlab get svc -l app=webservice

Write-Host @"
Helm HA deployed. Next steps:
1. Restore repos if needed: kubectl exec -it deploy/<toolbox> -n gitlab -- backup-utility --restore -t <timestamp>
2. Verify: curl -H 'Host: gitlab.lilangverse.xyz' http://127.0.0.1:30481/api/v4/version
3. Delete Omnibus StatefulSet when satisfied: kubectl -n gitlab delete statefulset gitlab
"@
