#!/usr/bin/env python3
"""
Automated App Fetcher for GitHub Profile
Fetches apps from App Store and Google Play Store automatically
"""

import json
import requests
import re
from datetime import datetime
from typing import Dict, List, Optional
import os

class AppStoreFetcher:
    """Fetches apps from Apple App Store using iTunes API"""
    
    def __init__(self, developer_id: str):
        self.developer_id = developer_id
        self.base_url = "https://itunes.apple.com"
    
    def get_developer_apps(self) -> List[Dict]:
        """Fetch all apps from a developer using iTunes API"""
        try:
            # First, get developer info
            lookup_url = f"{self.base_url}/lookup?id={self.developer_id}"
            response = requests.get(lookup_url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data['resultCount'] == 0:
                print(f"❌ No developer found with ID: {self.developer_id}")
                return []
            
            developer_info = data['results'][0]
            artist_name = developer_info.get('artistName', 'Unknown')
            
            # Search for all apps by this developer
            search_url = f"{self.base_url}/search"
            params = {
                'term': artist_name,
                'entity': 'software',
                'limit': 200
            }
            
            response = requests.get(search_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Filter apps by exact artist name match
            apps = []
            for app in data['results']:
                if app.get('artistName', '').lower() == artist_name.lower():
                    apps.append({
                        'name': app.get('trackName', ''),
                        'id': app.get('trackId', ''),
                        'bundle_id': app.get('bundleId', ''),
                        'icon_url': app.get('artworkUrl512', app.get('artworkUrl100', '')),
                        'store_url': app.get('trackViewUrl', ''),
                        'category': app.get('primaryGenreName', ''),
                        'rating': app.get('averageUserRating', 0),
                        'rating_count': app.get('userRatingCount', 0),
                        'price': app.get('price', 0),
                        'description': app.get('description', ''),
                        'release_date': app.get('releaseDate', ''),
                        'version': app.get('version', ''),
                        'screenshots': app.get('screenshotUrls', [])
                    })
            
            print(f"✅ Found {len(apps)} apps for {artist_name} on App Store")
            return sorted(apps, key=lambda x: x['name'])
            
        except requests.RequestException as e:
            print(f"❌ Error fetching from App Store: {e}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return []


class GooglePlayFetcher:
    """Fetches apps from Google Play Store (using web scraping)"""
    
    def __init__(self, developer_id: str):
        self.developer_id = developer_id
        self.base_url = "https://play.google.com/store/apps"
    
    def get_developer_apps(self) -> List[Dict]:
        """Fetch apps from Google Play Store developer page"""
        try:
            # Use the developer page URL
            dev_url = f"{self.base_url}/dev?id={self.developer_id}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(dev_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML to extract app information
            html_content = response.text
            
            # Extract app URLs using regex (basic approach)
            app_pattern = r'/store/apps/details\?id=([^"&]+)'
            app_ids = list(set(re.findall(app_pattern, html_content)))
            
            apps = []
            for app_id in app_ids:
                app_info = self._get_app_details(app_id, headers)
                if app_info:
                    apps.append(app_info)
            
            print(f"✅ Found {len(apps)} apps on Google Play Store")
            return sorted(apps, key=lambda x: x['name'])
            
        except requests.RequestException as e:
            print(f"❌ Error fetching from Google Play Store: {e}")
            return []
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return []
    
    def _get_app_details(self, package_id: str, headers: Dict) -> Optional[Dict]:
        """Get detailed information about a specific app"""
        try:
            app_url = f"{self.base_url}/details?id={package_id}"
            response = requests.get(app_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return None
            
            html = response.text
            
            # Extract app name
            name_pattern = r'<title>([^<]+) - Apps on Google Play</title>'
            name_match = re.search(name_pattern, html)
            name = name_match.group(1) if name_match else package_id
            
            # Extract rating
            rating_pattern = r'"ratingValue":"([^"]+)"'
            rating_match = re.search(rating_pattern, html)
            rating = float(rating_match.group(1)) if rating_match else 0
            
            # Extract icon URL
            icon_pattern = r'"image":"([^"]+\.png[^"]*)"'
            icon_match = re.search(icon_pattern, html)
            icon_url = icon_match.group(1).replace('\\u003d', '=') if icon_match else ''
            
            return {
                'name': name,
                'package_id': package_id,
                'store_url': app_url,
                'rating': rating,
                'icon_url': icon_url,
                'category': 'Unknown'  # Would need more parsing
            }
            
        except Exception as e:
            print(f"❌ Error getting details for {package_id}: {e}")
            return None


class READMEGenerator:
    """Generates README.md with fetched app data"""
    
    def __init__(self):
        self.template_file = "README_TEMPLATE.md"
        self.output_file = "README.md"
    
    def generate(self, app_store_apps: List[Dict], play_store_apps: List[Dict]) -> str:
        """Generate README content with app data"""
        
        # Categorize apps
        language_apps = self._filter_language_apps(app_store_apps + play_store_apps)
        game_apps = self._filter_game_apps(app_store_apps + play_store_apps)
        
        # Generate app sections
        language_section = self._generate_language_section(language_apps)
        games_section = self._generate_games_section(game_apps)
        
        # Generate statistics
        total_apps = len(app_store_apps) + len(play_store_apps)
        avg_rating = self._calculate_average_rating(app_store_apps + play_store_apps)
        
        # Load template and replace placeholders
        template = self._load_template()
        
        content = template.format(
            total_apps=total_apps,
            app_store_count=len(app_store_apps),
            play_store_count=len(play_store_apps),
            avg_rating=avg_rating,
            language_section=language_section,
            games_section=games_section,
            last_updated=datetime.now().strftime("%B %d, %Y at %I:%M %p UTC")
        )
        
        return content
    
    def _load_template(self) -> str:
        """Load README template"""
        if os.path.exists(self.template_file):
            with open(self.template_file, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # Return a basic template if file doesn't exist
            return self._get_default_template()
    
    def _get_default_template(self) -> str:
        """Default README template with direct app store icons"""
        return """# 🚀 Welcome to Rahul Jalavadiya's Digital Universe

<div align="center">
  <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=28&duration=3000&pause=1000&color=36BCF7&background=00000000&center=true&vCenter=true&multiline=true&width=600&height=100&lines=📱+Mobile+App+Developer;🎯+{total_apps}%2B+Apps+Published;⭐+{avg_rating}%2F5+Average+Rating;🌍+5+Languages+%7C+SRKWebstudio" alt="Dynamic Typing" />
</div>

<div align="center">

[![Portfolio](https://img.shields.io/badge/📱_Portfolio-{total_apps}_Apps_Live-success?style=for-the-badge&labelColor=000000)](https://github.com/allstuffrj)
[![App Store](https://img.shields.io/badge/🍎_App_Store-{app_store_count}_Apps-0D96F6?style=for-the-badge&logo=app-store&logoColor=white)](https://apps.apple.com/us/developer/rahul-jalavadiya/id1759541512)
[![Google Play](https://img.shields.io/badge/🤖_Google_Play-{play_store_count}_Apps-34A853?style=for-the-badge&logo=google-play&logoColor=white)](https://play.google.com/store/apps/dev?id=7787318106254119550)
[![Rating](https://img.shields.io/badge/⭐_Rating-{avg_rating}%2F5.0-FFD700?style=for-the-badge&labelColor=000000)](#apps)

</div>

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=header&text=&fontSize=50&fontColor=fff&animation=twinkling"/>

## 🎯 Featured Apps Portfolio
*🔄 Live data from App Store & Google Play Store - Updated automatically!*

{language_section}

{games_section}

## 📊 Portfolio Analytics

<div align="center">

| Metric | Value | Store Distribution |
|--------|-------|-------------------|
| 📱 **Total Apps** | **{total_apps}** | 🍎 {app_store_count} • 🤖 {play_store_count} |
| ⭐ **Average Rating** | **{avg_rating}/5.0** | Across all platforms |
| 🎯 **Categories** | **Education & Games** | Language Learning + Entertainment |

</div>

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer&text=&fontSize=50&fontColor=fff&animation=twinkling"/>

<div align="center">
<i>🤖 Automatically updated: {last_updated}</i><br>
<i>📱 Live data from app stores • ⚡ Powered by GitHub Actions</i>
</div>
"""
    
    def _filter_language_apps(self, apps: List[Dict]) -> List[Dict]:
        """Filter language learning apps"""
        language_keywords = ['verb', 'learn', 'language', 'spanish', 'french', 'russian', 'chinese', 'german', 'english']
        return [app for app in apps if any(keyword in app['name'].lower() for keyword in language_keywords)]
    
    def _filter_game_apps(self, apps: List[Dict]) -> List[Dict]:
        """Filter game/entertainment apps"""
        game_keywords = ['game', 'memory', 'word', 'search', 'typr', 'typing', 'first', 'worst']
        return [app for app in apps if any(keyword in app['name'].lower() for keyword in game_keywords)]
    
    def _generate_language_section(self, apps: List[Dict]) -> str:
        """Generate language learning section with direct app icons"""
        if not apps:
            return ""
        
        section = "### 🌍 Language Learning Suite\n\n"
        section += "<div align='center'>\n\n"
        
        # Create a table layout for apps with icons
        section += "| App | Icon | Rating | Store |\n"
        section += "|-----|------|--------|-------|\n"
        
        for app in apps:
            # App name
            app_name = app['name']
            
            # App icon (use direct URL from store)
            icon_url = app.get('icon_url', '')
            if icon_url:
                icon_html = f"<img src='{icon_url}' width='64' height='64' style='border-radius: 12px;' alt='{app_name}' />"
            else:
                icon_html = "📱"
            
            # Rating
            rating_text = f"⭐ {app['rating']:.1f}/5" if app.get('rating') else "N/A"
            if app.get('rating_count'):
                rating_text += f"<br>({app['rating_count']} reviews)"
            
            # Store links
            store_links = ""
            if app.get('store_url'):
                if 'apps.apple.com' in app['store_url']:
                    store_links = f"[![App Store](https://img.shields.io/badge/App_Store-0D96F6?style=for-the-badge&logo=app-store&logoColor=white)]({app['store_url']})"
                elif 'play.google.com' in app['store_url']:
                    store_links = f"[![Google Play](https://img.shields.io/badge/Google_Play-34A853?style=for-the-badge&logo=google-play&logoColor=white)]({app['store_url']})"
            
            section += f"| **{app_name}** | {icon_html} | {rating_text} | {store_links} |\n"
        
        section += "\n</div>\n\n"
        return section
    
    def _generate_games_section(self, apps: List[Dict]) -> str:
        """Generate games/entertainment section with direct app icons"""
        if not apps:
            return ""
        
        section = "### 🎮 Entertainment & Games\n\n"
        section += "<div align='center'>\n\n"
        
        # Create a table layout for apps with icons
        section += "| App | Icon | Rating | Store |\n"
        section += "|-----|------|--------|-------|\n"
        
        for app in apps:
            # App name
            app_name = app['name']
            
            # App icon (use direct URL from store)
            icon_url = app.get('icon_url', '')
            if icon_url:
                icon_html = f"<img src='{icon_url}' width='64' height='64' style='border-radius: 12px;' alt='{app_name}' />"
            else:
                icon_html = "�"
            
            # Rating
            rating_text = f"⭐ {app['rating']:.1f}/5" if app.get('rating') else "N/A"
            if app.get('rating_count'):
                rating_text += f"<br>({app['rating_count']} reviews)"
            
            # Store links
            store_links = ""
            if app.get('store_url'):
                if 'apps.apple.com' in app['store_url']:
                    store_links = f"[![App Store](https://img.shields.io/badge/App_Store-0D96F6?style=for-the-badge&logo=app-store&logoColor=white)]({app['store_url']})"
                elif 'play.google.com' in app['store_url']:
                    store_links = f"[![Google Play](https://img.shields.io/badge/Google_Play-34A853?style=for-the-badge&logo=google-play&logoColor=white)]({app['store_url']})"
            
            section += f"| **{app_name}** | {icon_html} | {rating_text} | {store_links} |\n"
        
        section += "\n</div>\n\n"
        return section
    
    def _calculate_average_rating(self, apps: List[Dict]) -> str:
        """Calculate average rating across all apps"""
        ratings = [app['rating'] for app in apps if app.get('rating', 0) > 0]
        if not ratings:
            return "N/A"
        
        avg = sum(ratings) / len(ratings)
        return f"{avg:.1f}"


def main():
    """Main function to fetch apps and generate README"""
    print("🚀 Starting Automated App Fetcher...")
    print("=" * 50)
    
    # Configuration
    DEVELOPER_ID = "1759541512"  # Your Apple Developer ID
    PLAY_STORE_DEV_ID = "7787318106254119550"  # Your Google Play Developer ID
    
    # Fetch apps from both stores
    print("📱 Fetching from App Store...")
    app_store_fetcher = AppStoreFetcher(DEVELOPER_ID)
    app_store_apps = app_store_fetcher.get_developer_apps()
    
    print("\n🤖 Fetching from Google Play Store...")
    play_store_fetcher = GooglePlayFetcher(PLAY_STORE_DEV_ID)
    play_store_apps = play_store_fetcher.get_developer_apps()
    
    # Generate README
    print(f"\n📝 Generating README with {len(app_store_apps)} App Store apps and {len(play_store_apps)} Play Store apps...")
    generator = READMEGenerator()
    readme_content = generator.generate(app_store_apps, play_store_apps)
    
    # Save README
    with open("README_AUTO.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("✅ README_AUTO.md generated successfully!")
    print(f"📊 Total apps found: {len(app_store_apps) + len(play_store_apps)}")
    
    # Save app data as JSON for debugging
    all_apps = {
        "app_store": app_store_apps,
        "google_play": play_store_apps,
        "generated_at": datetime.now().isoformat()
    }
    
    with open("apps_data.json", "w", encoding="utf-8") as f:
        json.dump(all_apps, f, indent=2)
    
    print("📄 App data saved to apps_data.json")
    print("\n🎉 Automation complete! Your README will now update automatically when you publish new apps.")


if __name__ == "__main__":
    main()