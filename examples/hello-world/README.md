# Example: Simple Node.js App

This is a minimal Node.js app to test Dead Simple Infrastructure.

## Files

**app.js**
```javascript
const express = require('express');
const app = express();
const PORT = process.env.PORT || 8080;

let requestCount = 0;

app.get('/', (req, res) => {
  requestCount++;
  res.json({
    message: 'Hello from Dead Simple Infrastructure!',
    timestamp: new Date().toISOString(),
    requests: requestCount
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy' });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`✓ Server running on port ${PORT}`);
  console.log(`✓ Environment: ${process.env.NODE_ENV || 'development'}`);
});
```

**package.json**
```json
{
  "name": "dsi-example-app",
  "version": "1.0.0",
  "description": "Example app for Dead Simple Infrastructure",
  "main": "app.js",
  "scripts": {
    "start": "node app.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  }
}
```

**Dockerfile**
```dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install --production

# Copy application code
COPY . .

# Expose port 8080 (required by DSI)
EXPOSE 8080

# Start the application
CMD ["npm", "start"]
```

**README.md**
```markdown
# DSI Example App

A simple Node.js Express server for testing Dead Simple Infrastructure.

## Endpoints

- `GET /` - Returns a JSON response with timestamp and request count
- `GET /health` - Health check endpoint

## Deploy to DSI

1. Push this code to a GitHub repository
2. In DSI Console, click "New App"
3. Enter the repository URL
4. Click "Deploy"
5. Access your app at the provided URL
```

## Deploy This Example

1. Create a new repository on GitHub
2. Copy these files to the repository
3. Push to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```
4. In DSI Console:
   - Click "New App"
   - Name: `dsi-example-app`
   - Repo URL: `<your-repo-url>`
   - Click "Create App"
   - Click "Deploy"

5. Once deployed, visit the URL shown in the console!
