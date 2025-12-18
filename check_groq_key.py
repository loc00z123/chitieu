"""Script kiểm tra GROQ_API_KEY"""
from dotenv import load_dotenv
import os

load_dotenv()

groq_key = os.getenv('GROQ_API_KEY', '')

print("=" * 60)
print("KIEM TRA GROQ_API_KEY")
print("=" * 60)

if groq_key:
    print(f"GROQ_API_KEY: CO")
    print(f"Do dai: {len(groq_key)} ky tu")
    print(f"Key (4 ky tu dau): {groq_key[:4]}...")
    print(f"Key (4 ky tu cuoi): ...{groq_key[-4:]}")
    
    # Kiểm tra format
    if groq_key.startswith('gsk_'):
        print("Format hop le (bat dau bang 'gsk_')")
    else:
        print("Format khong dung (nen bat dau bang 'gsk_')")
else:
    print("GROQ_API_KEY: KHONG CO")
    print("Hay them GROQ_API_KEY vao file .env")

print("=" * 60)

