import sys
import os

print("--- COMMENCING MODULE VERIFICATION HARNESS ---")

try:
    print("Validating gamespy_backend_server...")
    import gamespy_backend_server
    print("SUCCESS: backend_server imported cleanly.")
    
    print("Validating gamespy_qr_server...")
    import gamespy_qr_server
    print("SUCCESS: qr_server imported cleanly.")
    
    print("Validating gamespy_server_browser_server...")
    import gamespy_server_browser_server
    print("SUCCESS: browser_server imported cleanly.")
    
    print("Validating gamespy_natneg_server...")
    import gamespy_natneg_server
    print("SUCCESS: natneg_server imported cleanly.")
    
    print("--- ABSOLUTE ARCHITECTURAL VERIFICATION COMPLETE ---")
except Exception as e:
    import traceback
    print("\nFATAL: Module verification regression triggered!")
    traceback.print_exc()
    sys.exit(1)
