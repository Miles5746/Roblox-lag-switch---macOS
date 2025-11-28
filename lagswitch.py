#!/usr/bin/env python3

# ==============================================================================
# All-in-One Lag Switch for macOS by miles5746
#
# This single script handles everything: setup, listening, and toggling.
#
# --- USAGE ---
#
# 1. ONE-TIME SETUP:
#    Run this command in your terminal ONCE to configure your firewall:
#    sudo python3 lagswitch.py --setup
#
# 2. RUN THE LISTENER:
#    To start the lag switch, run this command WITHOUT sudo:
#    python3 lagswitch.py
#
# 3. USE IN-GAME:
#    Press the hotkey (F6 by default) to toggle the lag. The terminal
#    window does NOT need to be in focus.
#
# ==============================================================================

import sys
import os
import keyboard
import subprocess
import time
import atexit

# --- SCRIPT CONFIGURATION ---
AUTHOR = "miles5746"
HOTKEY = "f6"
# ----------------------------

# --- MACOS FIREWALL SETTINGS (DO NOT CHANGE) ---
ANCHOR_NAME = "roblox_block"
ANCHOR_FILE_PATH = f"/etc/pf.anchors/com.{AUTHOR}.roblox"
PF_CONF = "/etc/pf.conf"
STATE_FILE = os.path.expanduser(f"~/.{AUTHOR}_lag_state") # State file in user's home directory
# -----------------------------------------------

def run_setup():
    """
    Handles the one-time firewall configuration. Must be run with sudo.
    """
    if os.geteuid() != 0:
        print("[ERROR] Setup must be run with sudo. Command: sudo python3 lagswitch.py --setup")
        sys.exit(1)

    print(f"[INFO] Running one-time setup by {AUTHOR}...")

    ANCHOR_RULE_1 = f"anchor \"{ANCHOR_NAME}\""
    ANCHOR_RULE_2 = f"load anchor \"{ANCHOR_NAME}\" from \"{ANCHOR_FILE_PATH}\""

    try:
        with open(PF_CONF, 'r') as f:
            content = f.read()
        if ANCHOR_RULE_1 in content and ANCHOR_RULE_2 in content:
            print("[OK] Firewall rules already exist. Skipping.")
        else:
            print("[ACTION] Adding firewall rules...")
            with open(PF_CONF, 'a') as f:
                f.write(f"\n{ANCHOR_RULE_1}\n")
                f.write(f"{ANCHOR_RULE_2}\n")
            print("[SUCCESS] Rules added.")

        print("[ACTION] Creating anchor file...")
        subprocess.run(["mkdir", "-p", "/etc/pf.anchors"], check=True)
        subprocess.run(["touch", ANCHOR_FILE_PATH], check=True)
        print("[SUCCESS] Anchor file created.")

        print("[ACTION] Reloading firewall configuration...")
        subprocess.run(["pfctl", "-f", PF_CONF], check=True, capture_output=True)
        print("[SUCCESS] Firewall reloaded.")
        
        print("\n[COMPLETE] Setup is finished. You can now run the listener.")

    except Exception as e:
        print(f"\n[FATAL ERROR] An error occurred during setup: {e}")
        print("Please ensure you are running with sudo and have permissions to modify system files.")
        sys.exit(1)


def run_worker():
    """
    Performs the actual firewall toggling. Called by the listener.
    """
    if os.geteuid() != 0:
        sys.exit(1) # This mode is internal and must have root.

    rule = f"block out quick proto udp from any to any port 49152:65535\n"
    
    # Check the state: if the file exists, lag is ON.
    if os.path.exists(STATE_FILE):
        # Turn it OFF
        active_rule = ""
        os.remove(STATE_FILE)
    else:
        # Turn it ON
        active_rule = rule
        open(STATE_FILE, 'w').close()

    try:
        with open(ANCHOR_FILE_PATH, 'w') as f:
            f.write(active_rule)
        subprocess.run(["pfctl", "-a", ANCHOR_NAME, "-f", ANCHOR_FILE_PATH], check=True, capture_output=True)
    except Exception:
        sys.exit(1) # Exit with an error code if firewall command fails.


def run_listener():
    """
    Starts the global hotkey listener. Must be run as a normal user.
    """
    if os.geteuid() == 0:
        print("[ERROR] Do not run the listener with sudo. Just run: python3 lagswitch.py")
        sys.exit(1)

    print(f"--- Lag Switch Listener by {AUTHOR} ---")
    
    script_path = os.path.abspath(__file__)

    print("[INFO] Initializing sudo session. You may be prompted for your password once.")
    try:
        subprocess.run(["sudo", "-v"], check=True)
    except subprocess.CalledProcessError:
        print("[FATAL ERROR] Failed to authenticate with sudo. Please try again.")
        sys.exit(1)

    print(f"\n[SUCCESS] Listener is armed. Hotkey '{HOTKEY}' is active globally.")
    print("You can now focus on Roblox or any other application.")
    print("Press Ctrl+C in this window to quit.")
    
    # Clean up the state file on exit to ensure lag is turned off.
    atexit.register(lambda: os.path.exists(STATE_FILE) and os.remove(STATE_FILE))

    # When the hotkey is pressed, re-run this same script in worker mode.
    keyboard.add_hotkey(HOTKEY, lambda: subprocess.run(["sudo", sys.executable, script_path, "--worker"]))

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[EXIT] Shutting down listener.")
        # Final cleanup to ensure firewall is reset
        subprocess.run(["sudo", sys.executable, script_path, "--worker"], input=b'', capture_output=True) if os.path.exists(STATE_FILE) else None
        sys.exit(0)


if __name__ == "__main__":
    # The main router that decides which mode to run.
    if len(sys.argv) > 1:
        if sys.argv[1] == "--setup":
            run_setup()
        elif sys.argv[1] == "--worker":
            run_worker()
        else:
            print(f"Unknown argument: {sys.argv[1]}")
    else:
        run_listener()
