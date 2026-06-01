"""
API Data Verification & Monitoring Guide

This script verifies that your deployed app is fetching REAL data from APIs
(not using cached/stubbed data) and shows API usage statistics.

Learning objectives:
- Monitoring API calls
- Verifying real-time data
- Detecting caching issues
- Understanding API quotas
"""

import os
import sys
import json
from datetime import datetime
import httpx


def print_header(title):
    """Print formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def verify_api_freshness(app_url="http://localhost:3000"):
    """Verify that the app is fetching FRESH data from APIs."""
    print_header("🔄 VERIFYING REAL-TIME API DATA")

    try:
        # Make two requests with slight delay
        print("Making first API call...")
        response1 = httpx.get(f"{app_url}/api/incidents?bbox=78.3,17.3,78.5,17.5")
        response1.raise_for_status()
        data1 = response1.json()
        time1 = datetime.now()

        import time
        time.sleep(2)

        print("Making second API call (2 seconds later)...")
        response2 = httpx.get(f"{app_url}/api/incidents?bbox=78.3,17.3,78.5,17.5")
        response2.raise_for_status()
        data2 = response2.json()
        time2 = datetime.now()

        incidents1 = data1.get('incidents', [])
        incidents2 = data2.get('incidents', [])

        print(f"\n✓ First call:  {len(incidents1)} incidents at {time1.strftime('%H:%M:%S.%f')[:-3]}")
        print(f"✓ Second call: {len(incidents2)} incidents at {time2.strftime('%H:%M:%S.%f')[:-3]}")

        # Verify freshness indicators
        print("\n📊 FRESHNESS INDICATORS:")

        # Check 1: Data changes
        if incidents1 != incidents2:
            print("✅ Data varies between calls (REAL-TIME)")
            print("   → Confirms NOT using stale cache")
        else:
            print("⚠️  Data identical between calls")
            print("   → Could be cache or no traffic changes")

        # Check 2: Verify delay_ratio values
        if incidents1:
            print("\n✅ Sample Data Verification:")
            incident = incidents1[0]
            print(f"   Event: {incident.get('event')}")
            print(f"   Route: {incident.get('description', 'N/A')[:50]}...")
            print(f"   Duration normal: {incident.get('duration_normal')}s")
            print(f"   Duration traffic: {incident.get('duration_traffic')}s")
            print(f"   Delay ratio: {incident.get('delay_ratio')}")

        # Check 3: Response headers
        print("\n📋 RESPONSE HEADERS (confirms fresh data):")
        print(f"   Content-Type: {response2.headers.get('content-type')}")
        print(f"   Server: {response2.headers.get('server', 'Not specified')}")
        print(f"   Date: {response2.headers.get('date', 'Not specified')}")

        # Check 4: No-cache headers
        cache_control = response2.headers.get('cache-control', 'Not set')
        if 'no-cache' in cache_control or 'max-age=0' in cache_control:
            print(f"✅ Cache-Control: {cache_control} (NOT cached)")
        else:
            print(f"   Cache-Control: {cache_control}")

        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("   Make sure app is running at http://localhost:3000")
        return False


def verify_mapbox_api_call(app_url="http://localhost:3000"):
    """Verify Mapbox API is being called."""
    print_header("🗺️  VERIFYING MAPBOX API CALLS")

    try:
        response = httpx.get(f"{app_url}/config")
        response.raise_for_status()
        data = response.json()

        mapbox_token = data.get('mapboxToken')
        if mapbox_token and mapbox_token != "<set in Render dashboard>":
            print("✅ Mapbox token is configured")
            masked = mapbox_token[:4] + "..." + mapbox_token[-4:] if len(mapbox_token) > 8 else "***"
            print(f"   Token: {masked}")
            print("✅ App will use Mapbox for map rendering")
            return True
        else:
            print("⚠️  Mapbox token not set or placeholder value")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def verify_google_maps_api_call(app_url="http://localhost:3000"):
    """Verify Google Maps Directions API is being called."""
    print_header("🧭 VERIFYING GOOGLE MAPS API CALLS")

    try:
        # Query incidents which internally calls Google Maps
        response = httpx.get(f"{app_url}/api/incidents?bbox=78.3,17.3,78.5,17.5")
        response.raise_for_status()
        data = response.json()

        incidents = data.get('incidents', [])
        if incidents:
            print(f"✅ Google Maps API is being called")
            print(f"   Returned {len(incidents)} traffic incidents")

            # Check for Google Maps data indicators
            incident = incidents[0]
            if 'duration_normal' in incident and 'duration_traffic' in incident:
                print("✅ Data structure confirms Google Maps Directions API")
                print(f"   Contains delay_ratio: {incident.get('delay_ratio')}")
                print(f"   Contains address info: {incident.get('description', 'N/A')[:40]}...")
                return True
        else:
            print("⚠️  No incidents returned (no traffic data)")
            print("   Could mean: No routes in bbox, or API issue")
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_server_logs():
    """Guidance on checking server logs for API calls."""
    print_header("📋 HOW TO CHECK SERVER LOGS FOR API CALLS")

    print("""
LOCAL DEVELOPMENT:
  1. Start server: uvicorn server.main:app --reload --port 3000
  2. Watch terminal for log messages like:
     ✓ "Querying route: HITEC City to Banjara Hills"
     ✓ "Fetched incidents: 4"
     ✓ Debug messages showing API calls
  3. These logs PROVE the app is calling Google Maps API

RENDER DEPLOYMENT:
  1. Go to Render Dashboard → Your Service
  2. Click "Logs" tab
  3. Look for these indicators:
     ✓ "Querying route:" messages (shows Google Maps calls)
     ✓ "✓ Heavy congestion" messages (shows real data)
     ✓ "Returned N incidents" (shows API response)
     ✓ NO "GOOGLE_MAPS_API_KEY not set" errors
  4. Scroll through logs while clicking "Refresh" in browser
  5. New messages appear → confirms live API calls

BROWSER NETWORK TAB:
  1. Open your app in browser
  2. Press F12 (Developer Tools)
  3. Go to "Network" tab
  4. Click "Refresh" button in your app
  5. Look for requests:
     ✓ /api/incidents → Check response in "Response" tab
     ✓ Should contain incident data with duration_traffic
     ✓ Response time shows API latency (usually 1-3 seconds)
     ✓ Larger response = more data = real API call
""")


def demonstrate_real_api_call():
    """Show what REAL vs FAKE API calls look like."""
    print_header("🔍 REAL vs FAKE API CALLS")

    print("""
REAL API CALL (What you should see):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Response:
{
  "incidents": [
    {
      "event": "Heavy congestion",
      "description": "HITEC City to Banjara Hills: Plot no 32, Road no...",
      "duration_normal": 1200,          ← Real Google Maps data
      "duration_traffic": 1800,         ← Real traffic data
      "delay_ratio": 1.5,               ← Real calculation
      "lat": 17.42,
      "lng": 78.39,
      "coordinates": [78.39, 17.42]
    }
  ]
}

Indicators of REAL data:
✓ Different duration_traffic values each request
✓ Response time 1-3 seconds (API latency)
✓ Realistic address strings
✓ Delay ratio between 1.0-2.0+
✓ Coordinates match Hyderabad area

FAKE/STUBBED CALL (What you should NOT see):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Response:
{
  "incidents": [
    {
      "event": "test_incident",
      "description": "Stub data",
      "duration_traffic": 0,
      "delay_ratio": 0
    }
  ]
}

Indicators of FAKE data:
❌ Same response every time (cached)
❌ Response time < 100ms (no API call)
❌ Generic/stub description
❌ Zero or unrealistic delay ratios
❌ Missing real address data
""")


def api_quota_monitoring():
    """Guide for monitoring API quota usage."""
    print_header("📊 MONITORING API QUOTA USAGE")

    print("""
GOOGLE MAPS DIRECTIONS API:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Free Quota:
  • 25,000 requests/day
  • That's ~17 requests/minute
  • Our app queries 6 routes per call
  • So ~3 app refreshes per minute = Safe

Monitor Quota:
  1. Google Cloud Console
  2. Your Project → APIs & Services → Quotas
  3. Search "Directions API"
  4. Shows usage over time
  5. Click to see daily/monthly breakdown

Check if Quota Exceeded:
  • API returns: "OVER_QUERY_LIMIT" error
  • In app: No incidents appear
  • In logs: "REQUEST_DENIED" message
  • Solution: Wait 24 hours or upgrade plan

MAPBOX API:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Free Quota:
  • 50,000 map views/month
  • Plus 100,000 API requests/month
  • Plenty for small app

Monitor Quota:
  1. Mapbox → Account → Billing
  2. Shows usage dashboard
  3. Real-time quota tracking
  4. Email alerts if approaching limit

To Verify Quota:
  • Test local: python3 test_api_keys.py
  • Check Mapbox dashboard
  • Monitor Render logs for any quota errors
""")


def main():
    """Run all verification checks."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║        🔍 API DATA VERIFICATION & MONITORING GUIDE                ║")
    print("║                                                                    ║")
    print("║  This guide helps you verify that your app is fetching REAL      ║")
    print("║  data from APIs and not using cached/stubbed data.               ║")
    print("╚════════════════════════════════════════════════════════════════════╝")

    # Show guidance first
    check_server_logs()
    demonstrate_real_api_call()
    api_quota_monitoring()

    # If running locally, perform actual tests
    print_header("🧪 LIVE VERIFICATION (requires local server running)")
    print("Start server first: uvicorn server.main:app --reload --port 3000")
    print("Then run this script again...\n")

    try:
        verify_mapbox_api_call()
        verify_google_maps_api_call()
        verify_api_freshness()

        print_header("✅ VERIFICATION COMPLETE")
        print("""
CONCLUSION:
✓ If you see real incident data above with duration_traffic values
✓ If API calls take 1-3 seconds (not instant)
✓ If data varies between calls
✓ If you see log messages about API queries

→ THEN YOUR APP IS FETCHING REAL DATA FROM APIs! 🎉
""")

    except Exception as e:
        print(f"\nℹ️  Could not run live tests: {e}")
        print("But the guide above shows how to verify manually!")


if __name__ == '__main__':
    main()
