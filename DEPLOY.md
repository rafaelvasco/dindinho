# Deployment Guide: Dindinho on Hetzner with Coolify

1. Configure DNS: Add A records for both subdomains → your Hetzner IP
2. In Coolify: Create new application from Git repository
3. Set build pack to "Dockerfile"
4. Add environment variables (especially `ANTHROPIC_API_KEY`)
5. Create volume: `/app/data`
6. Add two domains: `dindinho.yourdomain.com:8501` and `dindinho-api.yourdomain.com:8000`
7. Deploy and monitor logs

## Detailed Deployment Steps

### Step 1: Configure DNS

Add two A records in your DNS provider (Cloudflare, Namecheap, etc.):

```
A    dindinho.yourdomain.com       →    YOUR_HETZNER_IP
A    dindinho-api.yourdomain.com   →    YOUR_HETZNER_IP
```

**Verify DNS propagation:**

```bash
dig dindinho.yourdomain.com
dig dindinho-api.yourdomain.com
```

Wait 5-30 minutes for DNS to propagate globally.

---

### Step 2: Access Coolify

1. Open your browser and navigate to your Coolify instance
2. Log in with your credentials

---

### Step 3: Create New Application

1. Click **"New Resource"** → **"Application"**
2. Choose **"Public Repository"** or connect your Git provider (GitHub/GitLab)
3. Enter repository details:
   - **Repository URL**: `https://github.com/yourusername/Dindinho`
   - **Branch**: `main` (or your production branch)
4. Click **"Continue"**

---

### Step 4: Configure Build Settings

1. **Build Pack**: Select **"Dockerfile"**
2. **Dockerfile Location**: `/Dockerfile` (default)
3. **Build Context**: `/` (default)

---

### Step 5: Configure Environment Variables

In the **"Environment Variables"** section, add the following:

#### Required Variables

```bash
# CRITICAL: Mark as SECRET in Coolify
ANTHROPIC_API_KEY=sk-ant-your-actual-api-key-here

# Database
DATABASE_PATH=/app/data/finance.db

# Backend
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_URL=https://dindinho-api.yourdomain.com

# Frontend
FRONTEND_PORT=8501

# Application
LOG_LEVEL=WARNING
ENVIRONMENT=production

# CORS - Replace with your actual domain
CORS_ORIGINS=https://dindinho.yourdomain.com
```

**Important:**

- Mark `ANTHROPIC_API_KEY` as **"Secret"** to encrypt it
- Replace `yourdomain.com` with your actual domain
- The `BACKEND_URL` should point to your API subdomain

---

### Step 6: Configure Persistent Storage

1. Navigate to the **"Storage"** or **"Volumes"** tab
2. Click **"Add Volume"**
3. Configure:
   - **Volume Name**: `dindinho_data`
   - **Mount Path**: `/app/data`
   - **Type**: Persistent Volume

This ensures your SQLite database survives container restarts and redeployments.

---

### Step 7: Configure Domains

In the **"Domains"** section, add **two domains**:

#### Domain 1: Frontend

- **Domain**: `dindinho.yourdomain.com`
- **Port**: `8501`
- **SSL**: ✅ Enable (Let's Encrypt)

#### Domain 2: Backend API

- **Domain**: `dindinho-api.yourdomain.com`
- **Port**: `8000`
- **SSL**: ✅ Enable (Let's Encrypt)

Coolify will automatically:

- Configure the reverse proxy (Traefik/Nginx)
- Request SSL certificates from Let's Encrypt
- Route traffic to the correct container ports

---

### Step 8: Deploy Application

1. Review all configurations
2. Click **"Deploy"** button
3. Monitor the deployment logs:
   - Watch for Docker build stages
   - Check for dependency installation
   - Verify health checks pass
   - Confirm SSL certificate provisioning

**Expected deployment time:** 5-10 minutes (first build)

---

## Configuration Reference

### Environment Variables Explained

| Variable            | Description                  | Example                               |
| ------------------- | ---------------------------- | ------------------------------------- |
| `ANTHROPIC_API_KEY` | Claude AI API key (required) | `sk-ant-xxxxx`                        |
| `DATABASE_PATH`     | SQLite database file path    | `/app/data/finance.db`                |
| `BACKEND_HOST`      | Backend bind address         | `0.0.0.0`                             |
| `BACKEND_PORT`      | Backend port                 | `8000`                                |
| `BACKEND_URL`       | Frontend → Backend URL       | `https://dindinho-api.yourdomain.com` |
| `FRONTEND_PORT`     | Frontend port                | `8501`                                |
| `LOG_LEVEL`         | Logging verbosity            | `WARNING` (prod), `INFO` (dev)        |
| `ENVIRONMENT`       | Environment name             | `production` or `development`         |
| `CORS_ORIGINS`      | Allowed CORS origins         | `https://dindinho.yourdomain.com`     |

### Port Mappings

| Service            | Internal Port | External Access                       |
| ------------------ | ------------- | ------------------------------------- |
| FastAPI Backend    | 8000          | `https://dindinho-api.yourdomain.com` |
| Streamlit Frontend | 8501          | `https://dindinho.yourdomain.com`     |

---

## Verification & Testing

### 1. Check Deployment Status

In Coolify:

- Verify "Running" status
- Check logs for errors
- Confirm SSL certificates are active

### 2. Test Backend Health

```bash
curl https://dindinho-api.yourdomain.com/health
```

**Expected response:**

```json
{
  "status": "healthy",
  "environment": "production",
  "database": "/app/data/finance.db"
}
```

### 3. Test Frontend Access

1. Open: `https://dindinho.yourdomain.com`
2. Verify Streamlit interface loads
3. Check browser console for errors (F12 → Console)

### 4. Test Full Workflow

1. **Upload CSV file**:

   - Navigate to import section
   - Upload a sample Brazilian credit card statement or bank extract
   - Verify preview displays correctly

2. **Test AI Categorization**:

   - Process transactions
   - Confirm categories are assigned
   - Check Coolify logs for Anthropic API calls

3. **Test Data Persistence**:

   - Save some transactions
   - In Coolify, restart the container
   - Verify data still exists after restart

4. **Test Reports**:
   - Navigate to reports/analytics section
   - Verify charts render correctly
   - Test date filtering and category selection

### 5. Performance Check

Monitor in Coolify dashboard:

- **CPU usage**: Should be <50% under normal load
- **Memory usage**: Should be <2GB for single user
- **Response time**: Frontend should load in <2 seconds
- **Logs**: No repeated errors or warnings

---

## Post-Deployment Tasks

### 1. Set Up Database Backups

SSH into your Hetzner instance and create a backup script:

**Create backup script:**

```bash
sudo nano /root/backup-dindinho.sh
```

**Script contents:**

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/dindinho"
CONTAINER_NAME="dindinho"  # Adjust based on Coolify's container name

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup SQLite database from container
docker exec $CONTAINER_NAME sqlite3 /app/data/finance.db ".backup /tmp/backup.db"
docker cp $CONTAINER_NAME:/tmp/backup.db $BACKUP_DIR/finance_$DATE.db

# Compress backup
gzip $BACKUP_DIR/finance_$DATE.db

# Delete backups older than 30 days
find $BACKUP_DIR -name "finance_*.db.gz" -mtime +30 -delete

echo "Backup completed: finance_$DATE.db.gz"
```

**Make executable:**

```bash
chmod +x /root/backup-dindinho.sh
```

**Schedule with cron (daily at 2 AM):**

```bash
crontab -e
```

Add this line:

```
0 2 * * * /root/backup-dindinho.sh >> /var/log/dindinho-backup.log 2>&1
```

**Test the backup:**

```bash
/root/backup-dindinho.sh
ls -lh /var/backups/dindinho/
```

---

### 2. Configure Monitoring

#### In Coolify:

1. Go to **Settings** → **Notifications**
2. Add email/Discord/Slack webhook
3. Enable alerts for:
   - Container crashes
   - High CPU/memory usage
   - Health check failures
   - Deployment failures

#### External Monitoring (Optional):

Set up [UptimeRobot](https://uptimerobot.com/) (free tier):

1. Create account at uptimerobot.com
2. Add monitors for:
   - Frontend: `https://dindinho.yourdomain.com`
   - Backend: `https://dindinho-api.yourdomain.com/health`
3. Configure notification preferences

---

### 3. Security Hardening

**Firewall Configuration:**

```bash
# SSH into your Hetzner instance
ssh root@your-server-ip

# Configure UFW firewall
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable

# Verify status
ufw status
```

**SSL Certificate Verification:**

1. In Coolify, check SSL certificate status
2. Verify auto-renewal is enabled
3. Test HTTPS access

**Regular Updates:**

- Rebuild container monthly for security patches
- Update dependencies in `requirements.txt`
- Monitor [Python security advisories](https://www.python.org/news/security/)

---

### 4. Optional Performance Optimizations

#### Increase Uvicorn Workers (for high traffic)

Edit `run.py` to add workers:

```python
backend_process = subprocess.Popen([
    "uvicorn",
    "backend.main:app",
    "--host", backend_host,
    "--port", str(backend_port),
    "--workers", "2",  # Add this line
    "--no-access-log",
])
```

**Worker recommendations:**

- 2 vCPU: 2 workers
- 4 vCPU: 3-4 workers

Redeploy after making changes.

---

## Troubleshooting

### Deployment Fails

**Check build logs in Coolify:**

| Error                      | Solution                                 |
| -------------------------- | ---------------------------------------- |
| `ModuleNotFoundError`      | Dependency missing in `requirements.txt` |
| `Permission denied`        | Check file ownership in Dockerfile       |
| `Port already in use`      | Check port conflicts in Coolify          |
| `Python version not found` | Verify base image is `python:3.13-slim`  |

### Health Check Fails

1. Check backend logs in Coolify
2. Verify environment variables are set correctly
3. Increase health check `start-period` in Dockerfile if backend is slow to start:
   ```dockerfile
   HEALTHCHECK --start-period=60s ...
   ```

### Frontend Can't Connect to Backend

1. **Verify BACKEND_URL**: Should be `https://dindinho-api.yourdomain.com`
2. **Check CORS**: Ensure `CORS_ORIGINS` includes frontend domain
3. **Test backend directly**: `curl https://dindinho-api.yourdomain.com/health`
4. **Check browser console**: F12 → Console tab for errors

### SSL Certificate Issues

1. Verify DNS is correctly configured
2. Check that ports 80 and 443 are open on firewall
3. In Coolify, try regenerating SSL certificate
4. Wait a few minutes for Let's Encrypt propagation

### Database Not Persisting

1. **Verify volume mount**: Check Coolify storage configuration
2. **Inspect volume**:
   ```bash
   docker exec dindinho ls -la /app/data
   ```
3. **Check permissions**: Volume should be owned by `appuser` (UID 1000)

### High Memory Usage

1. **Check logs** for memory leaks
2. **Reduce workers**: Lower Uvicorn worker count
3. **Upgrade VPS**: Consider CX41 (16GB RAM)

### AI Categorization Not Working

1. **Verify API key**: Check `ANTHROPIC_API_KEY` is set correctly
2. **Check logs**: Look for Anthropic API errors
3. **Test API key**:
   ```bash
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01"
   ```
4. **Check quota**: Verify your Anthropic account has credits

---

## Restore from Backup

If you need to restore the database:

```bash
# Copy backup to container
docker cp /var/backups/dindinho/finance_YYYYMMDD_HHMMSS.db.gz dindinho:/tmp/

# Extract and restore
docker exec dindinho gunzip /tmp/finance_YYYYMMDD_HHMMSS.db.gz
docker exec dindinho mv /app/data/finance.db /app/data/finance.db.old
docker exec dindinho mv /tmp/finance_YYYYMMDD_HHMMSS.db /app/data/finance.db

# Restart container in Coolify
```

---

## Rollback Procedure

If a deployment causes issues:

1. **Quick rollback in Coolify**:

   - Go to "Deployments" tab
   - Find previous working deployment
   - Click "Redeploy"

2. **Full rollback with database restore**:
   - Rollback code (step 1)
   - Restore database from backup (see above)
   - Verify functionality

---

## Success Checklist

Deployment is complete when all these are ✅:

- [ ] Application accessible at `https://dindinho.yourdomain.com`
- [ ] Backend API responds at `https://dindinho-api.yourdomain.com/health`
- [ ] SSL certificates active (valid Let's Encrypt certificates)
- [ ] Can upload and process CSV files
- [ ] AI categorization works (transactions get categories)
- [ ] Data persists across container restarts
- [ ] Reports and analytics display correctly
- [ ] No errors in Coolify logs
- [ ] Database backups running automatically
- [ ] Monitoring/alerts configured
- [ ] Performance is acceptable (page loads <2s)

---

## Useful Commands

```bash
# SSH into Hetzner instance
ssh root@your-server-ip

# View container logs
docker logs -f dindinho

# Enter container shell
docker exec -it dindinho /bin/bash

# Check database file
docker exec dindinho ls -lh /app/data/

# Test database connectivity
docker exec dindinho sqlite3 /app/data/finance.db "SELECT COUNT(*) FROM transactions;"

# View disk usage
df -h

# Monitor resource usage
htop

# Check firewall status
ufw status

# View cron jobs
crontab -l
```

---

## Support Resources

- **Coolify Documentation**: https://coolify.io/docs
- **FastAPI Deployment**: https://fastapi.tiangolo.com/deployment/
- **Streamlit Deployment**: https://docs.streamlit.io/knowledge-base/deploy
- **Docker Best Practices**: https://docs.docker.com/develop/dev-best-practices/
- **Anthropic API Docs**: https://docs.anthropic.com/

---

## Maintenance Schedule

**Weekly:**

- [ ] Review Coolify logs for errors
- [ ] Check resource usage (CPU/memory/disk)
- [ ] Verify backups are running

**Monthly:**

- [ ] Test backup restore procedure
- [ ] Rebuild container for security updates
- [ ] Review and update dependencies

**Quarterly:**

- [ ] Review and optimize database
- [ ] Analyze performance metrics
- [ ] Update documentation if needed

---

## Notes

- This deployment uses SQLite, which is suitable for single users or small teams
- For high traffic or multiple concurrent users, consider migrating to PostgreSQL
- Keep your `.env` file secure and never commit it to Git
- Test deployments thoroughly before migrating production data
- Consider setting up a staging environment for testing updates

---

**Deployment Guide Version:** 1.0
**Last Updated:** January 2026
**Application Version:** 0.1.0
