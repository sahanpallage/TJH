# Deployment Guide

This guide covers deploying the Job Search API to production.

## Pre-Deployment Checklist

### 1. Environment Variables

Ensure all required environment variables are set in your production environment:

**Required:**

- `RAPID_API_KEY` - RapidAPI key for JSearch
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase service role key
- `API_KEY` - Secure API key for authenticating requests (generate a strong random key)
- `CORS_ORIGINS` - Comma-separated list of allowed frontend origins

**Optional but Recommended:**

- `APIFY_API_KEY` - For Indeed job searches
- `ENVIRONMENT=production` - Set to production mode
- `LOG_LEVEL=INFO` - Set appropriate log level
- `LOG_FORMAT=json` - Use JSON logging for production

### 2. Generate API Key

Generate a secure API key for authentication:

```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Or using OpenSSL
openssl rand -hex 32
```

Add this to your `.env` file as `API_KEY`.

### 3. Update Frontend

Update your frontend to include the API key in requests:

```typescript
// In your API route files
const response = await fetch(`${BACKEND_URL}/api/jobs/...`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": process.env.API_KEY || "", // Add this header
  },
  body: JSON.stringify(data),
});
```

### 4. CORS Configuration

Update `CORS_ORIGINS` to include your production frontend URL:

```bash
CORS_ORIGINS=https://your-frontend-domain.vercel.app,https://www.yourdomain.com
```

### 5. Database Setup

Ensure the Supabase cache table is created:

```sql
CREATE TABLE job_cache (
  service    text    NOT NULL,
  cache_key  text    NOT NULL,
  response   jsonb   NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (service, cache_key)
);

CREATE INDEX idx_job_cache_created_at ON job_cache(created_at);
```

## Deployment Steps

### Railway / Render / Fly.io

1. **Set Environment Variables:**

   - Add all required environment variables in your platform's dashboard
   - Set `ENVIRONMENT=production`
   - Set `VALIDATE_ENV=true` to validate env vars at startup

2. **Build Command:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Start Command:**

   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers
   ```

4. **Health Check:**
   - Configure health check endpoint: `/health`
   - Expected response: `{"status": "healthy"}`

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
```

Build and run:

```bash
docker build -t job-search-api .
docker run -p 8000:8000 --env-file .env job-search-api
```

## Post-Deployment

### 1. Test Health Endpoint

```bash
curl https://your-api-domain.com/health
```

### 2. Test Authentication

```bash
# Should fail without API key
curl -X POST https://your-api-domain.com/api/jobs/jsearch \
  -H "Content-Type: application/json" \
  -d '{"jobTitle": "developer"}'

# Should succeed with API key
curl -X POST https://your-api-domain.com/api/jobs/jsearch \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"jobTitle": "developer"}'
```

### 3. Monitor Logs

Check application logs for:

- Successful startup messages
- Any error messages
- Rate limiting activity
- Cache hit/miss rates

### 4. Monitor Costs

- **Apify**: Monitor usage at https://console.apify.com
- **RapidAPI**: Monitor usage in RapidAPI dashboard
- Set up alerts for unexpected cost spikes

## Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Rotate API keys regularly** - Especially if compromised
3. **Use HTTPS only** - Never expose API over HTTP in production
4. **Monitor rate limits** - Check logs for abuse patterns
5. **Review CORS origins** - Only allow trusted domains
6. **Keep dependencies updated** - Regularly update `requirements.txt`

## Troubleshooting

### API returns 401 Unauthorized

- Check that `API_KEY` is set in environment
- Verify frontend is sending `X-API-Key` header
- Check API key matches between frontend and backend

### Rate limit errors (429)

- Check `RATE_LIMIT_PER_MINUTE` and `RATE_LIMIT_PER_HOUR` settings
- Consider increasing limits if legitimate users are hitting them
- For multiple instances, consider using Redis for distributed rate limiting

### Health check fails

- Check that required environment variables are set
- Verify Supabase connection
- Check application logs for specific errors

### High API costs

- Review cache hit rates - low cache hits mean more external API calls
- Consider reducing `max_results` limits
- Monitor Apify and RapidAPI usage dashboards
