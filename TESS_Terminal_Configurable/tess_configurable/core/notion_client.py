"""
Notion Integration - Knowledge management and note-taking.
"""

import json
from datetime import datetime
from typing import Optional, Dict, List, Any
from pathlib import Path


class NotionClient:
    """
    Integration with Notion for knowledge management.
    
    Features:
    - Create pages and notes
    - Query databases
    - Update existing content
    - Search across workspace
    """
    
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token
        self.base_url = "https://api.notion.com/v1"
        self.headers = {}
        
        if api_token:
            self._setup_headers()
        else:
            # Try to load from config
            self._load_token_from_config()
    
    def _setup_headers(self):
        """Setup API headers."""
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def _load_token_from_config(self):
        """Load token from TESS config."""
        try:
            from ..config_manager import get_config_manager
            config = get_config_manager()
            
            # Check if Notion token exists in config
            # You can add this to config_manager later
            self.api_token = getattr(config.config, 'notion_token', None)
            
            if self.api_token:
                self._setup_headers()
                
        except Exception:
            pass
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Dict = None) -> Dict:
        """Make API request to Notion."""
        if not self.api_token:
            return {"error": "Notion API token not configured"}
        
        try:
            import requests
            
            url = f"{self.base_url}/{endpoint}"
            
            if method == "GET":
                response = requests.get(url, headers=self.headers)
            elif method == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method == "PATCH":
                response = requests.patch(url, headers=self.headers, json=data)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                return {"error": f"API Error {response.status_code}: {response.text}"}
                
        except ImportError:
            return {"error": "requests not installed. Run: pip install requests"}
        except Exception as e:
            return {"error": str(e)}
    
    def search(self, query: str = "", filter_type: str = None) -> str:
        """
        Search across Notion workspace.
        
        Args:
            query: Search query
            filter_type: Optional filter (page, database)
            
        Returns:
            Formatted search results
        """
        data = {"query": query}
        
        if filter_type:
            data["filter"] = {"value": filter_type, "property": "object"}
        
        result = self._make_request("search", "POST", data)
        
        if "error" in result:
            return f"Notion error: {result['error']}"
        
        results = result.get("results", [])
        
        if not results:
            return "No results found"
        
        output = [f"Notion Search Results ({len(results)} found):", "-" * 40]
        
        for item in results[:10]:  # Limit to 10
            obj_type = item.get("object", "unknown")
            
            if obj_type == "page":
                title = self._extract_title(item)
                url = item.get("url", "")
                output.append(f"📄 {title}")
                output.append(f"   {url}")
                
            elif obj_type == "database":
                title = self._extract_title(item)
                output.append(f"🗃️  {title} (Database)")
        
        return "\n".join(output)
    
    def _extract_title(self, item: Dict) -> str:
        """Extract title from Notion item."""
        properties = item.get("properties", {})
        
        # Try to get title
        title_obj = properties.get("title", {})
        if title_obj:
            titles = title_obj.get("title", [])
            if titles:
                return "".join([t.get("plain_text", "") for t in titles])
        
        # For pages without title property
        if "title" in item:
            titles = item.get("title", [])
            if titles:
                return titles[0].get("plain_text", "Untitled")
        
        return "Untitled"
    
    def create_page(self, parent_id: str, title: str, content: str = "", 
                   database_id: str = None) -> str:
        """
        Create a new page in Notion.
        
        Args:
            parent_id: Parent page/database ID
            title: Page title
            content: Page content
            database_id: Optional database ID for database entries
            
        Returns:
            Created page URL or error
        """
        # Build page data
        data = {
            "parent": {"page_id": parent_id} if not database_id else {"database_id": database_id},
            "properties": {
                "title": {
                    "title": [{"text": {"content": title}}]
                }
            }
        }
        
        # Add content if provided
        if content:
            data["children"] = [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    }
                }
            ]
        
        result = self._make_request("pages", "POST", data)
        
        if "error" in result:
            return f"Error creating page: {result['error']}"
        
        url = result.get("url", "")
        return f"Created page: {title}\nURL: {url}"
    
    def create_note(self, title: str, content: str, tags: List[str] = None) -> str:
        """
        Quick note creation with metadata.
        
        Args:
            title: Note title
            content: Note content
            tags: Optional tags
            
        Returns:
            Result message
        """
        # For quick notes, we need a default parent
        # User should configure their "Notes" database/page ID
        
        from ..config_manager import get_config_manager
        config = get_config_manager()
        default_parent = getattr(config.config, 'notion_default_parent', None)
        
        if not default_parent:
            return "No default Notion parent configured. Please set a default page/database ID."
        
        # Add timestamp and tags to content
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        full_content = f"Created: {timestamp}\n\n{content}"
        
        if tags:
            full_content += f"\n\nTags: {', '.join(tags)}"
        
        return self.create_page(default_parent, title, full_content)
    
    def query_database(self, database_id: str, filter_obj: Dict = None) -> str:
        """
        Query a Notion database.
        
        Args:
            database_id: Database ID
            filter_obj: Optional filter criteria
            
        Returns:
            Formatted results
        """
        data = {"filter": filter_obj} if filter_obj else {}
        
        result = self._make_request(f"databases/{database_id}/query", "POST", data)
        
        if "error" in result:
            return f"Database query error: {result['error']}"
        
        results = result.get("results", [])
        
        if not results:
            return "No entries found"
        
        output = [f"Database Entries ({len(results)} found):", "-" * 40]
        
        for item in results[:10]:
            properties = item.get("properties", {})
            
            # Try to get name/title
            name = "Untitled"
            for prop_name, prop_value in properties.items():
                if prop_value.get("type") == "title":
                    titles = prop_value.get("title", [])
                    if titles:
                        name = titles[0].get("plain_text", "Untitled")
                        break
            
            output.append(f"• {name}")
        
        return "\n".join(output)
    
    def append_to_page(self, page_id: str, content: str) -> str:
        """
        Append content to existing page.
        
        Args:
            page_id: Page ID to append to
            content: Content to append
            
        Returns:
            Result message
        """
        data = {
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": content}}]
                    }
                }
            ]
        }
        
        result = self._make_request(f"blocks/{page_id}/children", "PATCH", data)
        
        if "error" in result:
            return f"Error appending content: {result['error']}"
        
        return "Content added successfully"
    
    def get_setup_instructions(self) -> str:
        """Get instructions for setting up Notion integration."""
        return """
Notion Integration Setup
========================

1. Go to https://www.notion.so/my-integrations
2. Click "New integration"
3. Name it "TESS Terminal"
4. Select your workspace
5. Copy the "Internal Integration Token"
6. Share pages/databases with your integration:
   - Open page in Notion
   - Click "..." (menu) → "Add connections"
   - Select "TESS Terminal"

To configure in TESS:
- Run: tess --settings
- Or manually add to config.json:
  "notion_token": "your-token-here"
  "notion_default_parent": "page-or-database-id"

Finding page/database IDs:
- Open page in Notion
- URL looks like: notion.so/workspace/PAGE-ID?v=...
- Copy the PAGE-ID part (32 characters)
"""
    
    def save_to_config(self, token: str, default_parent: str = None):
        """Save Notion credentials to TESS config."""
        from ..config_manager import get_config_manager
        config = get_config_manager()
        
        # Add to config
        config.config.notion_token = token
        if default_parent:
            config.config.notion_default_parent = default_parent
        
        config.save()
        
        # Reload
        self.api_token = token
        self._setup_headers()
