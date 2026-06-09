# Append to omnibus.rb (gitlab-secrets) when migrating Omnibus to external PostgreSQL/Redis.
# Replace DB_PASSWORD with value from gitlab-postgresql-secret before applying.

postgresql['enable'] = false
gitlab_rails['db_adapter'] = 'postgresql'
gitlab_rails['db_encoding'] = 'unicode'
gitlab_rails['db_host'] = 'gitlab-postgresql.gitlab.svc.cluster.local'
gitlab_rails['db_port'] = 5432
gitlab_rails['db_username'] = 'gitlab'
gitlab_rails['db_password'] = 'DB_PASSWORD'
gitlab_rails['db_database'] = 'gitlabhq_production'

redis['enable'] = false
gitlab_rails['redis_host'] = 'gitlab-redis.gitlab.svc.cluster.local'
gitlab_rails['redis_port'] = 6379
