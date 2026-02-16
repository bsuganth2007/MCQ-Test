# Security Setup Guide - Gemini API Key Configuration

## ⚠️ IMPORTANT: Secure API Key Management

This application requires a Google Gemini API key to generate MCQ questions using AI. To ensure security, your API key must be properly configured and protected.

## 🔑 Getting Your Gemini API Key

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated API key (it will look like: `AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`)

## 🛡️ Secure Configuration Steps

### Step 1: Create Your .env File

```bash
# From the project root directory
cd backend
cp .env.example .env
```

### Step 2: Add Your API Key

Open the newly created `backend/.env` file and replace `YOUR_GEMINI_API_KEY_HERE` with your actual API key:

```bash
GEMINI_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

### Step 3: Verify .gitignore

The `.gitignore` file is already configured to prevent `.env` files from being committed to version control. Verify it contains:

```
.env
*.env
backend/.env
mcq_backup/backend/.env
```

## ✅ Security Best Practices

### DO:
- ✅ Store API keys in environment variables or `.env` files
- ✅ Use `.gitignore` to prevent `.env` files from being committed
- ✅ Keep your API key private and secure
- ✅ Rotate your API key if it's accidentally exposed
- ✅ Use API key restrictions in Google Cloud Console (optional)
- ✅ Use separate API keys for development and production

### DON'T:
- ❌ Commit API keys to version control
- ❌ Share API keys in public repositories, forums, or chat
- ❌ Hardcode API keys directly in source code
- ❌ Include API keys in screenshots or documentation
- ❌ Use the same API key across multiple projects

## 🔄 If Your API Key Was Exposed

If you accidentally exposed your API key:

1. **Immediately revoke the exposed key:**
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Delete the compromised API key

2. **Generate a new API key:**
   - Create a new API key following the steps above
   - Update your `.env` file with the new key

3. **Remove the key from git history (if committed):**
   ```bash
   # Use git filter-branch or BFG Repo-Cleaner to remove sensitive data
   # See: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository
   ```

4. **Update any deployed environments:**
   - Update environment variables in all deployment environments
   - Restart services to pick up the new key

## 🚀 Deployment Configuration

### Local Development
Use the `.env` file as described above.

### Production Deployment

**For cloud platforms, use their secrets management:**

- **Heroku:**
  ```bash
  heroku config:set GEMINI_API_KEY=your_api_key_here
  ```

- **AWS (Lambda/EC2):**
  Use AWS Secrets Manager or Parameter Store

- **Google Cloud:**
  Use Secret Manager

- **Docker:**
  Pass as environment variable:
  ```bash
  docker run -e GEMINI_API_KEY=your_api_key_here ...
  ```

- **Docker Compose:**
  ```yaml
  environment:
    - GEMINI_API_KEY=${GEMINI_API_KEY}
  ```

## 🧪 Testing Your Setup

Run the test script to verify your API key is configured correctly:

```bash
cd backend
python check_gemini.py
```

Expected output:
```
Testing Gemini API...
API Key: AIzaSyXXXXXXXXXXXXXX...

📋 Available models:
  ✅ models/gemini-1.5-flash-latest
  ✅ models/gemini-1.5-pro-latest

🧪 Testing content generation...
🎯 Using model: models/gemini-1.5-flash-latest

✅ SUCCESS!
Response: ...
```

## 📚 Additional Resources

- [Google AI Studio - API Keys](https://aistudio.google.com/app/apikey)
- [Gemini API Documentation](https://ai.google.dev/docs)
- [GitHub: Removing Sensitive Data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [OWASP: Secrets Management](https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password)

## 🆘 Troubleshooting

### Error: "GEMINI_API_KEY environment variable not set"
- Ensure you created the `.env` file in the `backend/` directory
- Verify the file contains `GEMINI_API_KEY=your_key_here`
- Check for typos in the variable name

### Error: "API key not valid"
- Verify your API key is correct (no extra spaces or quotes)
- Ensure the API key hasn't been revoked
- Generate a new API key if needed

### Error: "Rate limit exceeded" or "quota exceeded"
- Wait a few minutes before trying again
- Consider upgrading your Gemini API quota
- Check your API usage in Google AI Studio

---

**Remember: Security is not a one-time setup. Regularly review and update your security practices!**
