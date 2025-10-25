#!/usr/bin/env python3
"""
Test script to verify the new Hugging Face token works
"""
from huggingface_hub import InferenceClient, HfApi
from config import Config

def test_new_token():
    print("Testing new Hugging Face token...")
    
    # Test 1: Check if token is valid
    try:
        api = HfApi(token=Config.HF_TOKEN)
        user_info = api.whoami()
        print(f"✅ Token is valid for user: {user_info['name']}")
    except Exception as e:
        print(f"❌ Token validation failed: {e}")
        return False
    
    # Test 2: Test Inference API
    try:
        client = InferenceClient(token=Config.HF_TOKEN)
        print("✅ Inference client created successfully")
    except Exception as e:
        print(f"❌ Inference client failed: {e}")
        return False
    
    # Test 3: Test a simple API call
    try:
        response = client.text_generation("Hello", model="gpt2", max_new_tokens=5)
        print(f"✅ Text generation works: {response}")
    except Exception as e:
        print(f"❌ Text generation failed: {e}")
        return False
    
    print("🎉 All tests passed! Your token is working correctly.")
    return True

if __name__ == "__main__":
    test_new_token()
