"""
API Key Verification Script

This script tests if your Mapbox and Google Maps API keys are valid
and working correctly. Run this before deploying to Render!

Learning objective: How to validate external API credentials.
"""

import os
import sys
import httpx
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

MAPBOX_TOKEN = os.getenv('MAPBOX_ACCESS_TOKEN')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')


def print_header(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def check_env_vars():
    """Check if environment variables are set."""
    print_header("1️⃣  CHECKING ENVIRONMENT VARIABLES")

    print("\n✓ MAPBOX_ACCESS_TOKEN is set:", bool(MAPBOX_TOKEN))
    if MAPBOX_TOKEN:
        # Show first and last 4 chars for security
        masked = MAPBOX_TOKEN[:4] + "..." + MAPBOX_TOKEN[-4:] if len(MAPBOX_TOKEN) > 8 else "***"
        print(f"  Value: {masked}")
    else:
        print("  ⚠️  NOT SET - You need to add this to server/.env")
        return False

    print("\n✓ GOOGLE_MAPS_API_KEY is set:", bool(GOOGLE_MAPS_API_KEY))
    if GOOGLE_MAPS_API_KEY:
        masked = GOOGLE_MAPS_API_KEY[:4] + "..." + GOOGLE_MAPS_API_KEY[-4:] if len(GOOGLE_MAPS_API_KEY) > 8 else "***"
        print(f"  Value: {masked}")
    else:
        print("  ⚠️  NOT SET - You need to add this to server/.env")
        return False

    return True


def test_mapbox():
    """Test Mapbox API key by fetching available styles."""
    print_header("2️⃣  TESTING MAPBOX API KEY")

    if not MAPBOX_TOKEN:
        print("❌ SKIPPED - Mapbox token not set")
        return False

    try:
        print("Testing Mapbox token by fetching styles...")
        url = f"https://api.mapbox.com/styles/v1?access_token={MAPBOX_TOKEN}"

        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        print("✅ MAPBOX API KEY WORKS!")
        print(f"   Available styles: {len(data)}")
        if data:
            print(f"   Example style: {data[0]['name']}")
        return True

    except httpx.HTTPStatusError as e:
        print(f"❌ MAPBOX API KEY FAILED!")
        print(f"   Status: {e.response.status_code}")
        if e.response.status_code == 401:
            print("   Error: Invalid or expired token")
        elif e.response.status_code == 404:
            print("   Error: Token not found")
        return False
    except Exception as e:
        print(f"❌ ERROR TESTING MAPBOX: {e}")
        return False


def test_google_maps():
    """Test Google Maps API key using Directions API."""
    print_header("3️⃣  TESTING GOOGLE MAPS API KEY")

    if not GOOGLE_MAPS_API_KEY:
        print("❌ SKIPPED - Google Maps key not set")
        return False

    try:
        print("Testing Google Maps key using Directions API...")

        # Query a simple route: Hyderabad Center to HITEC City
        origin = "17.3850,78.4867"
        destination = "17.4454,78.3794"

        url = (
            f"https://maps.googleapis.com/maps/api/directions/json?"
            f"origin={origin}"
            f"&destination={destination}"
            f"&departure_time=now"
            f"&traffic_model=best_guess"
            f"&key={GOOGLE_MAPS_API_KEY}"
        )

        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Check if request was successful
        if data.get('status') == 'OK':
            print("✅ GOOGLE MAPS API KEY WORKS!")
            if data.get('routes'):
                route = data['routes'][0]
                leg = route['legs'][0]
                duration = leg.get('duration', {}).get('text', 'N/A')
                duration_traffic = leg.get('duration_in_traffic', {}).get('text', 'N/A')
                print(f"   Normal duration: {duration}")
                print(f"   Duration in traffic: {duration_traffic}")
                print(f"   Start address: {leg.get('start_address')}")
                print(f"   End address: {leg.get('end_address')}")
            return True
        else:
            error = data.get('status', 'UNKNOWN')
            error_msg = data.get('error_message', 'No error message')
            print(f"❌ GOOGLE MAPS REQUEST FAILED!")
            print(f"   Status: {error}")
            print(f"   Message: {error_msg}")

            if error == 'REQUEST_DENIED':
                print("   → Check if Directions API is enabled in Google Cloud Console")
                print("   → Check if API key has quota remaining")
            elif error == 'INVALID_REQUEST':
                print("   → Check if the API key is valid")

            return False

    except httpx.HTTPStatusError as e:
        print(f"❌ GOOGLE MAPS API FAILED!")
        print(f"   HTTP Status: {e.response.status_code}")
        print(f"   Response: {e.response.text[:200]}")
        return False
    except Exception as e:
        print(f"❌ ERROR TESTING GOOGLE MAPS: {e}")
        return False


def test_backend_api():
    """Test the backend /api/incidents endpoint."""
    print_header("4️⃣  TESTING BACKEND API ENDPOINT")

    try:
        print("Testing local backend at http://localhost:3000/api/incidents...")

        # Test with a bounding box for Hyderabad
        bbox = "78.3,17.3,78.5,17.5"  # Hyderabad area
        url = f"http://localhost:3000/api/incidents?bbox={bbox}"

        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        print("✅ BACKEND API WORKS!")
        incidents = data.get('incidents', [])
        print(f"   Incidents returned: {len(incidents)}")
        if incidents:
            print(f"   Example incident: {incidents[0]['event']}")
        return True

    except Exception as e:
        print(f"⚠️  BACKEND NOT RUNNING OR ERROR: {e}")
        print("   Make sure to run: uvicorn server.main:app --reload --port 3000")
        return False


def print_summary(results):
    """Print summary of all tests."""
    print_header("📊 TEST SUMMARY")

    tests = [
        ("Environment Variables", results.get('env_vars')),
        ("Mapbox API", results.get('mapbox')),
        ("Google Maps API", results.get('google_maps')),
        ("Backend API", results.get('backend')),
    ]

    passed = sum(1 for _, result in tests if result)
    total = len(tests)

    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL" if result is False else "⏭️  SKIP"
        print(f"{status:10} {test_name}")

    print(f"\nResult: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Your API keys are working correctly!")
        print("✅ Safe to deploy to Render")
        return True
    elif passed >= 2:
        print("\n⚠️  SOME TESTS FAILED")
        print("Review the errors above and fix your API keys")
        return False
    else:
        print("\n❌ CRITICAL: Multiple tests failed")
        print("Check your API keys and setup before deploying")
        return False


def main():
    """Run all verification tests."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║           🔑 API KEY VERIFICATION SCRIPT                          ║")
    print("║                                                                    ║")
    print("║  This script tests if your Mapbox and Google Maps API keys       ║")
    print("║  are valid and working before deploying to Render.               ║")
    print("╚════════════════════════════════════════════════════════════════════╝")

    results = {}

    # Test 1: Environment variables
    results['env_vars'] = check_env_vars()

    if not results['env_vars']:
        print_summary(results)
        print("\n❌ Cannot proceed without API keys in server/.env")
        sys.exit(1)

    # Test 2: Mapbox API
    results['mapbox'] = test_mapbox()

    # Test 3: Google Maps API
    results['google_maps'] = test_google_maps()

    # Test 4: Backend API (optional - only if running locally)
    print_header("4️⃣  TESTING BACKEND API ENDPOINT (Optional)")
    print("Skipping - only available if running locally")
    print("To test: Start server first with: uvicorn server.main:app --reload --port 3000")
    results['backend'] = None

    # Print summary
    success = print_summary(results)

    print("\n" + "="*70)
    if success:
        print("✅ READY TO DEPLOY!")
        print("   Your API keys are working. Safe to deploy to Render.")
    else:
        print("⚠️  FIX ISSUES BEFORE DEPLOYING")
        print("   Address the errors shown above.")
    print("="*70 + "\n")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
