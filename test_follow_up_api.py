#!/usr/bin/env python3
"""
Test script to debug the API response for follow-up questions.
"""

import requests
import json

API_BASE = "http://localhost:8000/api"

def test_follow_up_questions():
    print("Testing follow-up questions generation...")
    
    # Step 1: Initial request
    print("\n1. Initial request...")
    response1 = requests.post(f"{API_BASE}/chat", json={
        "message": "Create a customer onboarding process"
    })
    
    if response1.status_code != 200:
        print(f"❌ Initial request failed: {response1.status_code}")
        return
    
    data1 = response1.json()
    session_id = data1["session_id"]
    
    print(f"✅ Initial response received")
    print(f"   Session ID: {session_id}")
    print(f"   Questions count: {len(data1.get('questions', []))}")
    print(f"   Questions: {data1.get('questions', [])}")
    
    # Step 2: Follow-up request using one of the initial questions
    if data1.get('questions'):
        follow_up_message = data1['questions'][0]
        print(f"\n2. Follow-up request with: '{follow_up_message}'")
        
        response2 = requests.post(f"{API_BASE}/chat", json={
            "message": follow_up_message,
            "session_id": session_id
        })
        
        if response2.status_code != 200:
            print(f"❌ Follow-up request failed: {response2.status_code}")
            return
        
        data2 = response2.json()
        print(f"✅ Follow-up response received")
        print(f"   Questions count: {len(data2.get('questions', []))}")
        print(f"   Questions: {data2.get('questions', [])}")
        
        if data2.get('questions'):
            print("🎉 SUCCESS: Follow-up questions are being generated!")
        else:
            print("❌ PROBLEM: No follow-up questions generated")
            print(f"   Full response: {json.dumps(data2, indent=2)}")
    else:
        print("❌ No initial questions to test with")

if __name__ == "__main__":
    test_follow_up_questions()
