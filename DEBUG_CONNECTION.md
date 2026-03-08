# Debug Connection Issues

## Check Streamlit Cloud Logs

1. Go to: https://share.streamlit.io
2. Your app → **Manage app** → **Logs**
3. Look for lines that say:
   - `Testing connection: ...`
   - `Connection failed on port ...`
   - `Authentication failed` or `Connection refused`

## Verify Secrets Are Correct

The logs will show what values are being used. Compare with your Supabase Session Pooler connection string:

**From Supabase:**
```
postgresql://postgres.peawexmwwmkqszcdqwjv:[PASSWORD]@aws-1-us-east-1.pooler.supabase.com:5432/postgres
```

**In Streamlit Secrets should be:**
```toml
POSTGRES_HOST=aws-1-us-east-1.pooler.supabase.com
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres.peawexmwwmkqszcdqwjv
POSTGRES_PASSWORD=JxhkAQBPSQD8hfCG
```

## Common Issues

1. **Wrong hostname**: Must be `aws-1-us-east-1.pooler.supabase.com` (not `db.xxx.supabase.co`)
2. **Wrong user**: Must be `postgres.peawexmwwmkqszcdqwjv` (includes project ID)
3. **Wrong port**: Must be `5432` for Session Pooler
4. **Quotes in secrets**: Streamlit might add quotes - the code strips them, but check logs
5. **Password encoding**: Special characters in password might cause issues

## Test Connection Locally

If you want to test the connection locally first:

```bash
# Set environment variables
export POSTGRES_HOST="aws-1-us-east-1.pooler.supabase.com"
export POSTGRES_PORT="5432"
export POSTGRES_DB="postgres"
export POSTGRES_USER="postgres.peawexmwwmkqszcdqwjv"
export POSTGRES_PASSWORD="JxhkAQBPSQD8hfCG"

# Test connection
PYTHONPATH=$(pwd) python3 -c "from scripts.database import test_connection; print(test_connection())"
```

This will show you the exact error message.
