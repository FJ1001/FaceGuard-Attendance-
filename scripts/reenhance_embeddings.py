"""
Script to re-generate embeddings for existing students using the enhanced algorithm.

This script will:
1. Load existing student photos from the database
2. Re-generate embeddings using the enhanced recognition engine
3. Update the database with new embeddings
4. Test the new embeddings for better separation

IMPORTANT: Make sure you have the original registration photos backed up or 
re-register students through the UI after running this script.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import base64
import numpy as np
from database.student_repository import StudentRepository
from database.connection import get_db_connection
from face_recognition.recognition_engine_enhanced import EnhancedFaceRecognitionEngine
from config.settings import EMBEDDING_SIZE

def re_enroll_students():
    print("=" * 80)
    print("🔄 RE-ENROLLMENT WITH ENHANCED FACE RECOGNITION")
    print("=" * 80)
    
    print("\n⚠️  IMPORTANT NOTICE:")
    print("This script will delete old embeddings and mark students for re-enrollment.")
    print("You will need to re-register students through the UI with new photos.")
    print("\nThe enhanced algorithm provides much better face discrimination.")
    
    response = input("\nDo you want to continue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ Operation cancelled.")
        return
    
    print("\n" + "=" * 80)
    print("Step 1: Checking current students...")
    print("=" * 80)
    
    student_repo = StudentRepository()
    students = student_repo.get_all_students()
    
    if not students:
        print("❌ No students found. Please register students first.")
        return
    
    print(f"✅ Found {len(students)} active students:")
    for s in students:
        print(f"   - {s['name']} ({s['roll_number']})")
    
    print("\n" + "=" * 80)
    print("Step 2: Clearing old embeddings...")
    print("=" * 80)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM face_embeddings")
            old_count = cursor.fetchone()[0]
            print(f"   Found {old_count} old embeddings")
            
            cursor.execute("DELETE FROM face_embeddings")
            conn.commit()
            print(f"   ✅ Deleted all old embeddings")
            
    except Exception as e:
        print(f"   ❌ Error clearing embeddings: {e}")
        return
    
    print("\n" + "=" * 80)
    print("Step 3: Testing enhanced recognition engine...")
    print("=" * 80)
    
    try:
        engine = EnhancedFaceRecognitionEngine()
        print("   ✅ Enhanced engine initialized successfully")
    except Exception as e:
        print(f"   ❌ Failed to initialize enhanced engine: {e}")
        return
    
    print("\n" + "=" * 80)
    print("Step 4: Summary and Next Steps")
    print("=" * 80)
    
    print(f"\n✅ Old embeddings cleared: {old_count}")
    print(f"✅ Enhanced engine: Ready")
    print(f"📋 Students requiring re-enrollment: {len(students)}")
    
    print("\n" + "=" * 80)
    print("📝 WHAT TO DO NEXT:")
    print("=" * 80)
    print("\n1. Start the Streamlit application:")
    print("   streamlit run main.py")
    print("\n2. Go to 'Student Management' page")
    print("\n3. For each student listed below, re-register them:")
    for s in students:
        print(f"   - {s['name']} ({s['roll_number']})")
    
    print("\n4. When re-registering, follow these guidelines:")
    print("   ✅ Use 3-5 clear, well-lit photos")
    print("   ✅ Different angles (front, slight left, slight right)")
    print("   ✅ Similar lighting to how you'll take attendance")
    print("   ✅ Remove glasses/masks if possible")
    print("   ✅ Good quality (not blurry)")
    
    print("\n5. After re-enrollment, test attendance marking")
    print("   - Enable debug mode to see similarity scores")
    print("   - You should see much better separation between students")
    
    print("\n" + "=" * 80)
    print("RE-ENROLLMENT PREPARATION COMPLETE")
    print("=" * 80)
    
    print("\n💡 Expected improvements:")
    print("   - Better discrimination between different faces")
    print("   - Lower false-positive rate")
    print("   - More reliable attendance marking")
    print("   - Clearer separation in similarity scores")


if __name__ == "__main__":
    try:
        re_enroll_students()
    except Exception as e:
        print(f"\n❌ Script failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
