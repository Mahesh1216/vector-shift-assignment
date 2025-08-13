# hubspot.py

import json
import secrets
import urllib.parse
from fastapi import Request, HTTPException
from fastapi.responses import HTMLResponse
import httpx
import asyncio
from datetime import datetime
from integrations.integration_item import IntegrationItem

from redis_client import add_key_value_redis, get_value_redis, delete_key_redis

# HubSpot OAuth credentials - Replace with your actual credentials
CLIENT_ID ='XYZ'
CLIENT_SECRET = 'XYZ'

# Redirect URL - must match exactly what's configured in your HubSpot app
REDIRECT_URI = 'http://localhost:8000/integrations/hubspot/oauth2callback'

# Fixed scopes - must match exactly what's configured in your HubSpot app
SCOPE = 'oauth crm.objects.contacts.read crm.objects.companies.read crm.objects.deals.read'

def get_authorization_url():
    """Generate the HubSpot authorization URL with proper encoding"""
    return f'https://app.hubspot.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&scope={urllib.parse.quote(SCOPE)}'

def is_mock_mode():
    """Check if we're running in mock mode (using default test credentials)"""
    return False  # Disable mock mode since you have real credentials

async def authorize_hubspot(user_id, org_id):
    """Initialize HubSpot OAuth authorization flow"""
    
    # Generate state for CSRF protection
    state_data = {
        'state': secrets.token_urlsafe(32),
        'user_id': user_id,
        'org_id': org_id,
        'mock': is_mock_mode()
    }
    encoded_state = urllib.parse.quote(json.dumps(state_data))
    
    # Store state in Redis for validation
    await add_key_value_redis(f'hubspot_state:{org_id}:{user_id}', json.dumps(state_data), expire=600)
    
    if is_mock_mode():
        # Mock mode - return a fake authorization URL that will trigger mock data
        return f'http://localhost:8000/integrations/hubspot/oauth2callback?code=mock_code&state={encoded_state}'
    
    # Real OAuth flow
    auth_url = f'{get_authorization_url()}&state={encoded_state}'
    return auth_url

async def oauth2callback_hubspot(request: Request):
    """Handle HubSpot OAuth callback"""
    
    # Check for OAuth errors
    if request.query_params.get('error'):
        error_description = request.query_params.get('error_description', 'Unknown error')
        raise HTTPException(status_code=400, detail=f"OAuth error: {error_description}")
    
    code = request.query_params.get('code')
    encoded_state = request.query_params.get('state')
    
    if not code or not encoded_state:
        raise HTTPException(status_code=400, detail='Missing code or state parameter')
    
    # Decode and validate state
    try:
        state_data = json.loads(urllib.parse.unquote(encoded_state))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Invalid state parameter: {str(e)}')
    
    original_state = state_data.get('state')
    user_id = state_data.get('user_id')
    org_id = state_data.get('org_id')
    is_mock = state_data.get('mock', False)
    
    if not all([original_state, user_id, org_id]):
        raise HTTPException(status_code=400, detail='Invalid state data')
    
    # Verify state matches what we stored
    saved_state = await get_value_redis(f'hubspot_state:{org_id}:{user_id}')
    if not saved_state:
        raise HTTPException(status_code=400, detail='State expired or not found')
    
    try:
        saved_state_data = json.loads(saved_state)
        if original_state != saved_state_data.get('state'):
            raise HTTPException(status_code=400, detail='State does not match')
    except:
        raise HTTPException(status_code=400, detail='Invalid saved state')
    
    # Clean up state
    await delete_key_redis(f'hubspot_state:{org_id}:{user_id}')
    
    # Handle mock mode
    if is_mock or code == 'mock_code':
        mock_token_data = {
            'access_token': 'mock_access_token',
            'refresh_token': 'mock_refresh_token',
            'expires_in': 3600,
            'token_type': 'bearer'
        }
        await add_key_value_redis(f'hubspot_credentials:{org_id}:{user_id}', json.dumps(mock_token_data), expire=600)
        
        return HTMLResponse(content="""
        <html>
            <script>
                window.close();
            </script>
        </html>
        """)
    
    # Exchange authorization code for access token
    token_url = 'https://api.hubapi.com/oauth/v1/token'
    token_data = {
        'grant_type': 'authorization_code',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': 'http://localhost:8000/integrations/hubspot/oauth2callback',
        'code': code
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                token_url,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                error_detail = f"Token exchange failed: {response.status_code} - {response.text}"
                raise HTTPException(status_code=400, detail=error_detail)
            
            token_response = response.json()
            
            # Store credentials in Redis
            await add_key_value_redis(
                f'hubspot_credentials:{org_id}:{user_id}', 
                json.dumps(token_response), 
                expire=600
            )
            
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Network error during token exchange: {str(e)}")
    
    return HTMLResponse(content="""
    <html>
        <script>
            window.close();
        </script>
    </html>
    """)

async def get_hubspot_credentials(user_id, org_id):
    """Retrieve stored HubSpot credentials"""
    credentials = await get_value_redis(f'hubspot_credentials:{org_id}:{user_id}')
    
    if not credentials:
        raise HTTPException(status_code=400, detail='No HubSpot credentials found. Please re-authenticate.')
    
    try:
        credentials_data = json.loads(credentials)
    except:
        raise HTTPException(status_code=400, detail='Invalid credentials data')
    
    # Clean up credentials after retrieval
    await delete_key_redis(f'hubspot_credentials:{org_id}:{user_id}')
    
    return credentials_data

async def create_integration_item_metadata_object(response_json, item_type="Contact"):
    """Create IntegrationItem from HubSpot response"""
    properties = response_json.get('properties', {})
    item_id = str(response_json.get('id', ''))
    
    # Handle different object types with better naming
    if item_type == "Contact":
        firstname = properties.get('firstname', '')
        lastname = properties.get('lastname', '')
        name = f"{firstname} {lastname}".strip()
        if not name:
            name = properties.get('email', f'Contact {item_id}')
        url = f"https://app.hubspot.com/contacts/{item_id}"
        
    elif item_type == "Company":
        name = properties.get('name', f'Company {item_id}')
        url = f"https://app.hubspot.com/contacts/{item_id}/company"
        
    elif item_type == "Deal":
        name = properties.get('dealname', f'Deal {item_id}')
        url = f"https://app.hubspot.com/contacts/{item_id}/deal"
        
    else:
        name = f"{item_type} {item_id}"
        url = f"https://app.hubspot.com/contacts/{item_id}"
    
    # Handle HubSpot timestamps (milliseconds since epoch)
    creation_time = None
    last_modified_time = None
    
    try:
        if response_json.get('createdAt'):
            creation_time = datetime.fromtimestamp(int(response_json['createdAt']) / 1000)
    except (ValueError, TypeError, KeyError):
        pass
    
    try:
        if response_json.get('updatedAt'):
            last_modified_time = datetime.fromtimestamp(int(response_json['updatedAt']) / 1000)
    except (ValueError, TypeError, KeyError):
        pass
    
    return IntegrationItem(
        id=item_id,
        type=item_type,
        name=name,
        creation_time=creation_time,
        last_modified_time=last_modified_time,
        url=url,
        visibility=True
    )

async def get_items_hubspot(credentials):
    """Fetch HubSpot items (contacts, companies, deals) and return as IntegrationItem objects"""
    
    # Parse credentials if they're a string
    if isinstance(credentials, str):
        try:
            credentials_data = json.loads(credentials)
        except:
            raise HTTPException(status_code=400, detail='Invalid credentials format')
    else:
        credentials_data = credentials
    
    access_token = credentials_data.get('access_token')
    if not access_token:
        raise HTTPException(status_code=400, detail='No access token found in credentials')
    
    # Handle mock data
    if access_token == 'mock_access_token':
        mock_items = [
            IntegrationItem(
                id="1001",
                type="Contact",
                name="John Doe",
                creation_time=datetime.now(),
                last_modified_time=datetime.now(),
                url="https://app.hubspot.com/contacts/1001",
                visibility=True
            ),
            IntegrationItem(
                id="1002",
                type="Contact", 
                name="Jane Smith",
                creation_time=datetime.now(),
                last_modified_time=datetime.now(),
                url="https://app.hubspot.com/contacts/1002",
                visibility=True
            ),
            IntegrationItem(
                id="2001",
                type="Company",
                name="Acme Corporation",
                creation_time=datetime.now(),
                last_modified_time=datetime.now(),
                url="https://app.hubspot.com/contacts/2001/company",
                visibility=True
            ),
            IntegrationItem(
                id="3001",
                type="Deal",
                name="Enterprise Deal Q1",
                creation_time=datetime.now(),
                last_modified_time=datetime.now(),
                url="https://app.hubspot.com/contacts/3001/deal",
                visibility=True
            )
        ]
        print(f'HubSpot mock integration items: {len(mock_items)} items')
        return mock_items
    
    # Real API calls
    list_of_integration_items = []
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    async with httpx.AsyncClient() as client:
        # Fetch contacts
        try:
            contacts_response = await client.get(
                'https://api.hubapi.com/crm/v3/objects/contacts',
                headers=headers,
                params={'limit': 100}
            )
            
            if contacts_response.status_code == 200:
                contacts_data = contacts_response.json()
                for contact in contacts_data.get('results', []):
                    integration_item = await create_integration_item_metadata_object(contact, 'Contact')
                    list_of_integration_items.append(integration_item)
            elif contacts_response.status_code == 401:
                raise HTTPException(status_code=401, detail='HubSpot access token expired or invalid')
            else:
                print(f"Warning: Failed to fetch contacts: {contacts_response.status_code}")
                
        except httpx.RequestError as e:
            print(f"Network error fetching contacts: {str(e)}")
        
        # Fetch companies
        try:
            companies_response = await client.get(
                'https://api.hubapi.com/crm/v3/objects/companies',
                headers=headers,
                params={'limit': 100}
            )
            
            if companies_response.status_code == 200:
                companies_data = companies_response.json()
                for company in companies_data.get('results', []):
                    integration_item = await create_integration_item_metadata_object(company, 'Company')
                    list_of_integration_items.append(integration_item)
            else:
                print(f"Warning: Failed to fetch companies: {companies_response.status_code}")
                
        except httpx.RequestError as e:
            print(f"Network error fetching companies: {str(e)}")
        
        # Fetch deals
        try:
            deals_response = await client.get(
                'https://api.hubapi.com/crm/v3/objects/deals',
                headers=headers,
                params={'limit': 100}
            )
            
            if deals_response.status_code == 200:
                deals_data = deals_response.json()
                for deal in deals_data.get('results', []):
                    integration_item = await create_integration_item_metadata_object(deal, 'Deal')
                    list_of_integration_items.append(integration_item)
            else:
                print(f"Warning: Failed to fetch deals: {deals_response.status_code}")
                
        except httpx.RequestError as e:
            print(f"Network error fetching deals: {str(e)}")
    
    print(f'HubSpot integration items: {len(list_of_integration_items)} items retrieved')
    for item in list_of_integration_items:
        print(f'  - {item.type}: {item.name} (ID: {item.id})')
    
    return list_of_integration_items