# Integration Platform

A full-stack application that provides OAuth integrations with popular platforms like HubSpot, Airtable, and Notion. Built with React frontend and FastAPI backend.

## Features

- **OAuth Authentication** for multiple platforms
- **HubSpot Integration** - Connect and fetch contacts, companies, and deals
- **Airtable Integration** - Connect and fetch bases and tables
- **Notion Integration** - Connect and fetch workspaces and pages
- **Secure credential management** with Redis
- **Real-time data loading** and display

## Prerequisites

Before running this application, make sure you have:

- **Node.js** (v14 or higher)
- **Python** (v3.8 or higher)
- **Docker** and **Docker Compose**
- **HubSpot OAuth App Credentials** (Client ID and Client Secret)

## Project Setup Instructions

### Getting Started

Follow these steps to set up and run the project on your local machine.

### Clone the Project

1. Clone the project repository to your desktop:

```bash
git clone https://github.com/Baba14Yaga/VectorShift.git
cd VectorShift
```

### Backend Setup

1. Navigate to the backend directory:

```bash
cd backend
```

2. Create a virtual environment:

```bash
python -m venv venv
```

3. Activate the virtual environment:
   * On Windows:

```bash
.\venv\Scripts\activate
```

   * On macOS/Linux:

```bash
source venv/bin/activate
```

4. Install the required dependencies:

```bash
pip install -r requirements.txt
```

5. **Configure HubSpot Credentials:**
   
   Open `backend/integrations/hubspot.py` and replace the `CLIENT_ID` and `CLIENT_SECRET` with your actual HubSpot credentials:

```python
# Replace these with your actual HubSpot credentials
CLIENT_ID = 'your-hubspot-client-id-here'
CLIENT_SECRET = 'your-hubspot-client-secret-here'
```

6. Start the backend server:

```bash
uvicorn main:app --reload
```

The backend server will be accessible at `http://localhost:8000`

### Frontend Setup

1. Open a new terminal and navigate to the frontend directory:

```bash
cd frontend
```

2. Install the required dependencies:

```bash
npm i
```

3. Start the frontend server:

```bash
npm start
```

The frontend server will be running at `http://localhost:3000`

### Redis Setup (Docker)

1. In the project root directory (where your `docker-compose.yml` is located), start Redis using Docker Compose:

```bash
docker-compose up -d redis
```

2. Verify Redis is running:

```bash
docker-compose ps
```

3. Test Redis connection:

```bash
docker exec -it redis-integration redis-cli ping
```

You should see: `PONG`

## HubSpot App Setup

To get your HubSpot credentials:

1. Go to [HubSpot Developer Portal](https://developers.hubspot.com/)
2. Create a new app or use an existing one
3. Configure the app settings:
   - **Redirect URL:** `http://localhost:8000/integrations/hubspot/oauth2callback`
   - **Scopes:** `oauth`, `crm.objects.contacts.read`, `crm.objects.companies.read`, `crm.objects.deals.read`
4. Copy your **Client ID** and **Client Secret**
5. Update the credentials in `backend/integrations/hubspot.py`

## Running the Application

Once all services are running:

1. **Backend:** `http://localhost:8000` ✅
2. **Frontend:** `http://localhost:3000` ✅  
3. **Redis:** Running in Docker container ✅

### Using the Application

1. Open your browser to `http://localhost:3000`
2. Enter user details (e.g., "TestUser", "TestOrg")
3. Select "HubSpot" from the Integration Type dropdown
4. Click "Connect to HubSpot" to start OAuth flow
5. Grant permissions in the popup window
6. Click "Load Data" to fetch and display HubSpot items

## Docker Commands Reference

### Redis Management

```bash
# Start Redis
docker-compose up -d redis

# Stop Redis
docker-compose stop redis

# View Redis logs
docker logs redis-integration -f

# Access Redis CLI
docker exec -it redis-integration redis-cli

# Restart Redis
docker restart redis-integration

# Remove Redis container and data
docker-compose down -v
```

## Project Structure

```
├── backend/
│   ├── integrations/
│   │   ├── airtable.py          # Airtable OAuth integration
│   │   ├── hubspot.py           # HubSpot OAuth integration
│   │   ├── notion.py            # Notion OAuth integration
│   │   └── integration_item.py  # Data model for integration items
│   ├── main.py                  # FastAPI application and routes
│   ├── requirements.txt         # Python dependencies
│   └── redis_client.py          # Redis client utilities
├── frontend/
│   ├── src/
│   │   ├── integrations/
│   │   │   ├── airtable.js      # Airtable frontend component
│   │   │   ├── hubspot.js       # HubSpot frontend component
│   │   │   └── notion.js        # Notion frontend component
│   │   ├── App.js               # Main React component
│   │   ├── integration-form.js  # Main integration form
│   │   ├── data-form.js         # Data loading and display component
│   │   └── index.js             # React entry point
│   ├── package.json             # Node.js dependencies
│   └── public/
├── docker-compose.yml           # Docker services configuration
└── README.md
```

## API Endpoints

### HubSpot Endpoints
- `POST /integrations/hubspot/authorize` - Initialize OAuth flow
- `GET /integrations/hubspot/oauth2callback` - Handle OAuth callback
- `POST /integrations/hubspot/credentials` - Retrieve stored credentials
- `POST /integrations/hubspot/load` - Fetch HubSpot items

### Additional Endpoints
- `GET /docs` - FastAPI automatic documentation
- `GET /` - Health check endpoint

## Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```bash
   # Check if Redis container is running
   docker ps | grep redis
   
   # View Redis logs
   docker logs redis-integration
   
   # Restart Redis container
   docker restart redis-integration
   ```

2. **Backend Server Issues**
   ```bash
   # Check if virtual environment is activated
   which python  # Should point to venv/bin/python
   
   # Reinstall dependencies
   pip install -r requirements.txt
   
   # Check backend logs for errors
   uvicorn main:app --reload --log-level debug
   ```

3. **Frontend Issues**
   ```bash
   # Clear npm cache
   npm cache clean --force
   
   # Delete node_modules and reinstall
   rm -rf node_modules package-lock.json
   npm install
   ```

4. **OAuth Callback Errors**
   - Verify redirect URLs match exactly in your HubSpot app settings
   - Ensure backend server is running on port 8000
   - Check that CLIENT_ID and CLIENT_SECRET are correctly configured

5. **CORS Issues**
   - Frontend must run on port 3000
   - Backend must run on port 8000
   - Check CORS configuration in `backend/main.py`

### Debug Mode

Enable debug logging:

```bash
# Backend debug
uvicorn main:app --reload --log-level debug

# Check browser console for frontend logs
```

## Expected Results

When everything is working correctly:

1. **Connection:** HubSpot OAuth flow completes successfully
2. **Data Loading:** Application fetches contacts, companies, and deals
3. **Display:** Items appear in both raw text and formatted list views
4. **Console Logs:** Backend logs show successful API calls and data processing

Example console output:
```
HubSpot integration items: 4 items retrieved
  - Contact: John Doe (ID: 123456789)
  - Contact: Jane Smith (ID: 987654321)
  - Company: Example Corp (ID: 456789123)
  - Deal: Q1 Sales Deal (ID: 789123456)
```

## Support

- Check the troubleshooting section above
- Review FastAPI docs at `http://localhost:8000/docs`
- Ensure all prerequisites are installed
- Verify HubSpot app configuration matches requirements

## License

This project is licensed under the MIT License.