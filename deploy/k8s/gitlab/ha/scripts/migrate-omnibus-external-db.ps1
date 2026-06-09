# Migrate live Omnibus GitLab from embedded PostgreSQL/Redis to shared services.
# Non-destructive: creates backup + pg_dump before switching. Expect ~5–15 min downtime.
param(
    [string]$KubeConfig = "$env:USERPROFILE\.kube\config-homelab",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$env:KUBECONFIG = $KubeConfig
$Ns = "gitlab"
$Pod = "gitlab-0"

function Exec-Gitlab([string]$Cmd) {
    kubectl -n $Ns exec $Pod -c gitlab -- bash -lc $Cmd
}

Write-Host "==> Pre-flight"
kubectl -n $Ns get pod $Pod
kubectl -n $Ns wait --for=condition=ready pod -l app=gitlab-postgresql --timeout=120s
kubectl -n $Ns wait --for=condition=available deployment/gitlab-redis --timeout=120s

$dbHost = "gitlab-postgresql.gitlab.svc.cluster.local"
$redisHost = "gitlab-redis.gitlab.svc.cluster.local"

if ($DryRun) {
    Write-Host "Dry run — would migrate $Pod to $dbHost / $redisHost"
    exit 0
}

Write-Host "==> GitLab application backup (includes DB metadata)"
Exec-Gitlab "gitlab-backup create SKIP=registry,artifacts,builds,pages,lfs,terraform_state,packages,ci_secure_files 2>&1 | tail -5"

Write-Host "==> Stop Puma/Sidekiq"
Exec-Gitlab "gitlab-ctl stop puma sidekiq"

Write-Host "==> Dump embedded PostgreSQL"
Exec-Gitlab "pg_dump -h /var/opt/gitlab/postgresql -U gitlab -d gitlabhq_production -Fc -f /var/opt/gitlab/backups/embedded_pre_ha.dump"

Write-Host "==> Restore to external PostgreSQL"
$pgPw = kubectl -n $Ns get secret gitlab-postgresql-secret -o jsonpath='{.data.postgresql-password}' | ForEach-Object {
    [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_))
}
$restoreCmd = @"
export PGPASSWORD='$pgPw'
pg_restore -h $dbHost -U gitlab -d gitlabhq_production --clean --if-exists --no-owner --role=gitlab /var/opt/gitlab/backups/embedded_pre_ha.dump 2>&1 | tail -20
"@
Exec-Gitlab $restoreCmd

Write-Host "==> Patch omnibus.rb in secret (external DB + Redis)"
$omnibus = kubectl -n $Ns get secret gitlab-secrets -o jsonpath='{.data.omnibus\.rb}' | ForEach-Object {
    [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_))
}
if ($omnibus -notmatch "postgresql\['enable'\] = false") {
    $snippet = @"

postgresql['enable'] = false
gitlab_rails['db_adapter'] = 'postgresql'
gitlab_rails['db_encoding'] = 'unicode'
gitlab_rails['db_host'] = '$dbHost'
gitlab_rails['db_port'] = 5432
gitlab_rails['db_username'] = 'gitlab'
gitlab_rails['db_password'] = '$pgPw'
gitlab_rails['db_database'] = 'gitlabhq_production'
redis['enable'] = false
gitlab_rails['redis_host'] = '$redisHost'
gitlab_rails['redis_port'] = 6379
"@
    $omnibusNew = $omnibus + $snippet
    $b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($omnibusNew))
    kubectl -n $Ns patch secret gitlab-secrets --type merge -p "{`"data`":{`"omnibus.rb`":`"$b64`"}}"
} else {
    Write-Host "omnibus.rb already references external DB — skipping secret patch."
}

Write-Host "==> Rolling restart Omnibus to pick up config"
kubectl -n $Ns delete pod $Pod --wait=true
kubectl -n $Ns wait --for=condition=ready pod/$Pod --timeout=1200s

Write-Host "==> Verify database host"
Exec-Gitlab "grep -E \"host:|adapter:\" /var/opt/gitlab/gitlab-rails/etc/database.yml | head -4"
Write-Host "Migration complete. Verify: curl -H 'Host: gitlab.lilangverse.xyz' http://<nodeport>/api/v4/version"
