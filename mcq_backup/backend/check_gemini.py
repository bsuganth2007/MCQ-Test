import google.generativeai as genai
import os

# Get API key from environment variable only
api_key = os.getenv('GEMINI_API_KEY')

if not api_key or api_key == 'YOUR_GEMINI_API_KEY_HERE':
    print("❌ ERROR: GEMINI_API_KEY environment variable not set or using placeholder!")
    print("\n📝 Setup Instructions:")
    print("   1. Get your API key from: https://aistudio.google.com/app/apikey")
    print("   2. Copy backend/.env.example to backend/.env")
    print("   3. Replace YOUR_GEMINI_API_KEY_HERE with your actual API key")
    print("   4. Never commit the .env file to version control!")
    exit(1)

print("Testing Gemini API...")
print(f"API Key: {api_key[:20]}...")

try:
    # Configure
    genai.configure(api_key=api_key)
    
    # List available models
    print("\n📋 Available models:")
    available_models = []
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"  ✅ {model.name}")
            available_models.append(model.name)
    
    # Test simple generation with available model
    print("\n🧪 Testing content generation...")
    
    # Try different model names in order of preference
    model_names_to_try = [
        'gemini-1.5-flash-latest',
        'gemini-1.5-pro-latest', 
        'gemini-pro',
        'models/gemini-pro',
        'models/gemini-1.5-flash-latest',
        'models/gemini-1.5-pro-latest'
    ]
    
    # Filter to only models that are available
    available_model_to_use = None
    for model_name in model_names_to_try:
        # Check if this model or its full path is in available models
        if model_name in available_models or f"models/{model_name}" in available_models:
            available_model_to_use = model_name
            break
        # Also check without 'models/' prefix
        for avail_model in available_models:
            if model_name in avail_model:
                available_model_to_use = avail_model
                break
        if available_model_to_use:
            break
    
    if not available_model_to_use and available_models:
        available_model_to_use = available_models[0]
    
    if not available_model_to_use:
        raise Exception("No models available for content generation")
    
    print(f"\n🎯 Using model: {available_model_to_use}")
    
    model = genai.GenerativeModel(available_model_to_use)
    response = model.generate_content("Write a simple math question")
    
    print(f"\n✅ SUCCESS!")
    print(f"Response: {response.text[:200]}...")
    print(f"\n💡 Use this model name in your app: {available_model_to_use}")
    
except Exception as e:
    print(f"\n❌ FAILED!")
    print(f"Error: {e}")
    print(f"Error type: {type(e).__name__}")
    
    # Common issues
    if "API_KEY_INVALID" in str(e) or "API key not valid" in str(e):
        print("\n💡 Solution: Your API key is invalid. Get a new one from:")
        print("   https://aistudio.google.com/app/apikey")
    elif "PERMISSION_DENIED" in str(e):
        print("\n💡 Solution: API key doesn't have permission. Check restrictions.")
    elif "RESOURCE_EXHAUSTED" in str(e):
        print("\n💡 Solution: Rate limit exceeded. Wait a few minutes.")
    elif "quota" in str(e).lower():
        print("\n💡 Solution: You've exceeded your quota. Wait for reset or upgrade.")
    elif "not found" in str(e).lower():
        print("\n💡 Solution: Model not found. The API version may have changed.")
        print("   Available models are listed above.")