#!/usr/bin/env python3
"""
API Diagnostic Tool - Debug Laravel API Key Issues
Run: python -m src.utils.api_debug
"""

import requests
import sys
from ..config import Config

def test_api_connection():
    """Test Laravel API connection and diagnose issues."""
    
    print("🔍 API Diagnostic Tool")
    print("=" * 60)
    
    # Check configuration
    print("\n📋 Configuration Check:")
    print(f"   URL: {Config.LARAVEL_API_URL}")
    print(f"   Key: {Config.LARAVEL_API_KEY[:10]}...{Config.LARAVEL_API_KEY[-5:]}" if Config.LARAVEL_API_KEY else "   Key: NOT SET")
    print(f"   Key Length: {len(Config.LARAVEL_API_KEY)} characters")
    
    if not Config.LARAVEL_API_KEY:
        print("\n❌ LARAVEL_API_KEY is not set in .env")
        return False
    
    # Test basic connectivity
    print("\n🌐 Connection Test:")
    try:
        response = requests.get(
            f"{Config.LARAVEL_API_URL}/agent/opportunities/1",
            headers={"X-API-Key": Config.LARAVEL_API_KEY},
            timeout=5
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        
        if response.status_code == 401:
            print("\n❌ API Key Invalid!")
            print("\n   Possible solutions:")
            print("   1. Verify the API key in your Laravel app's database")
            print("   2. Check if the key is active/enabled in Laravel")
            print("   3. Ensure the key is copied correctly (no spaces/typos)")
            print("   4. Check if the Laravel API uses a different header (Api-Key, API-KEY, Authorization)")
            return False
        elif response.status_code == 200:
            print("✅ API Key is Valid!")
            return True
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Laravel app!")
        print(f"   Make sure the app is running at {Config.LARAVEL_API_URL}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_header_formats():
    """Test different header formats to find the correct one."""
    print("\n🔑 Header Format Tests:")
    print("-" * 60)
    
    headers_to_test = {
        "X-API-Key": {"X-API-Key": Config.LARAVEL_API_KEY},
        "Authorization (Bearer)": {"Authorization": f"Bearer {Config.LARAVEL_API_KEY}"},
        "Authorization (Direct)": {"Authorization": Config.LARAVEL_API_KEY},
        "Api-Key": {"Api-Key": Config.LARAVEL_API_KEY},
        "API-KEY": {"API-KEY": Config.LARAVEL_API_KEY},
        "api-key": {"api-key": Config.LARAVEL_API_KEY},
    }
    
    for name, headers in headers_to_test.items():
        try:
            response = requests.get(
                f"{Config.LARAVEL_API_URL}/agent/opportunities/1",
                headers=headers,
                timeout=3
            )
            status = "✅ WORKS" if response.status_code == 200 else f"❌ {response.status_code}"
            print(f"   {name:<25} {status}")
        except Exception as e:
            print(f"   {name:<25} ❌ Error")

if __name__ == "__main__":
    success = test_api_connection()
    test_header_formats()
    
    print("\n" + "=" * 60)
    if not success:
        print("\n📝 NEXT STEPS:")
        print("   1. Go to your Laravel app and verify the API key:")
        print("      - Check the database table where API keys are stored")
        print("      - Confirm the key is: " + Config.LARAVEL_API_KEY)
        print("      - Verify the key is active/enabled")
        print("   2. Check Laravel's API middleware/routes")
        print("   3. Look for any rate limiting or IP restrictions")
        sys.exit(1)
    else:
        print("\n✅ API connection is working!")
        sys.exit(0)
