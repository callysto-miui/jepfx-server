from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import time
import psutil
import platform
from datetime import datetime, timedelta
from functools import wraps
import threading
import requests

app = Flask(__name__)
CORS(app)

# ==============================
# CONFIGURATION
# ==============================
# UptimeRobot settings
UPTIME_ROBOT_API_KEY = os.environ.get('UPTIME_ROBOT_API_KEY', '')
MONITOR_ID = os.environ.get('MONITOR_ID', '')

# Rate limiting (simple in-memory)
rate_limit_store = {}
RATE_LIMIT = 100  # requests per minute per IP

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        now = time.time()
        window_start = now - 60
        
        # Clean old entries
        for key in list(rate_limit_store.keys()):
            if rate_limit_store[key]['timestamp'] < window_start:
                del rate_limit_store[key]
        
        if ip not in rate_limit_store:
            rate_limit_store[ip] = {'count': 1, 'timestamp': now}
        else:
            if rate_limit_store[ip]['count'] >= RATE_LIMIT:
                return jsonify({'success': False, 'error': 'Rate limit exceeded'}), 429
            rate_limit_store[ip]['count'] += 1
            rate_limit_store[ip]['timestamp'] = now
        
        return f(*args, **kwargs)
    return decorated_function

# ==============================
# SERVER METRICS
# ==============================
start_time = time.time()
request_count = 0
error_count = 0

def get_server_uptime():
    """Get server uptime in seconds"""
    return int(time.time() - start_time)

def get_system_stats():
    """Get system statistics"""
    try:
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'platform': platform.platform(),
            'python_version': platform.python_version()
        }
    except:
        return {
            'cpu_percent': 0,
            'memory_percent': 0,
            'disk_percent': 0,
            'platform': platform.platform(),
            'python_version': platform.python_version()
        }

# ==============================
# COMMAND DATABASE
# ==============================
COMMANDS = {
    "reboot_system": {
        "name": "Reboot System",
        "category": "reboot",
        "adb_commands": [["adb", "reboot"]],
        "fastboot_commands": [],
        "description": "Reboot device to system"
    },
    "reboot_recovery": {
        "name": "Reboot Recovery",
        "category": "reboot",
        "adb_commands": [["adb", "reboot", "recovery"]],
        "fastboot_commands": [],
        "description": "Reboot device to recovery mode"
    },
    "reboot_bootloader": {
        "name": "Reboot Bootloader",
        "category": "reboot",
        "adb_commands": [["adb", "reboot", "bootloader"]],
        "fastboot_commands": [["fastboot", "reboot"]],
        "description": "Reboot device to bootloader/fastboot mode"
    },
    "reboot_edl": {
        "name": "Reboot EDL",
        "category": "reboot",
        "adb_commands": [["adb", "reboot", "edl"]],
        "fastboot_commands": [],
        "description": "Reboot to EDL 9008 mode"
    },
    "wipe_cache": {
        "name": "Wipe Cache",
        "category": "maintenance",
        "adb_commands": [
            ["adb", "shell", "dd if=/dev/zero of=/dev/block/by-name/cache"]
        ],
        "fastboot_commands": [],
        "description": "Wipe cache partition",
        "requires_confirmation": True
    },
    "unlock_bootloader": {
        "name": "Unlock Bootloader",
        "category": "bootloader",
        "adb_commands": [],
        "fastboot_commands": [["fastboot", "flashing", "unlock"]],
        "description": "Unlock bootloader (WIPES DATA!)",
        "requires_confirmation": True,
        "warning": "This will wipe ALL data on your device!"
    },
    "lock_bootloader": {
        "name": "Lock Bootloader",
        "category": "bootloader",
        "adb_commands": [],
        "fastboot_commands": [["fastboot", "flashing", "lock"]],
        "description": "Lock bootloader (WIPES DATA!)",
        "requires_confirmation": True,
        "warning": "This will wipe ALL data on your device!"
    },
    "sideload": {
        "name": "Sideload ZIP",
        "category": "flash",
        "adb_commands": [
            ["adb", "reboot", "sideload"],
            ["adb", "sideload", "{file_path}"]
        ],
        "fastboot_commands": [],
        "description": "Sideload a ZIP file",
        "requires_file": True,
        "file_type": "zip"
    },
    "flash_boot": {
        "name": "Flash Boot",
        "category": "flash",
        "adb_commands": [],
        "fastboot_commands": [["fastboot", "flash", "boot", "{file_path}"]],
        "description": "Flash boot.img",
        "requires_file": True,
        "file_type": "img"
    },
    "flash_init_boot": {
        "name": "Flash Init Boot",
        "category": "flash",
        "adb_commands": [],
        "fastboot_commands": [["fastboot", "flash", "init_boot", "{file_path}"]],
        "description": "Flash init_boot.img",
        "requires_file": True,
        "file_type": "img"
    },
    "flash_recovery": {
        "name": "Flash Recovery",
        "category": "flash",
        "adb_commands": [],
        "fastboot_commands": [
            ["fastboot", "flash", "recovery", "{file_path}"],
            ["fastboot", "flash", "recovery_a", "{file_path}"],
            ["fastboot", "flash", "recovery_b", "{file_path}"]
        ],
        "description": "Flash custom recovery",
        "requires_file": True,
        "file_type": "img"
    },
    "flash_vbmeta_disable": {
        "name": "Flash Vbmeta (Verity Disabled)",
        "category": "flash",
        "adb_commands": [],
        "fastboot_commands": [["fastboot", "--disable-verity", "--disable-verification", "flash", "vbmeta", "{file_path}"]],
        "description": "Flash vbmeta with verity disabled",
        "requires_file": True,
        "file_type": "img"
    },
    "backup_partition": {
        "name": "Backup Partition",
        "category": "backup",
        "adb_commands": [
            ["adb", "shell", "dd if={partition_path} of=/sdcard/{partition}.img"],
            ["adb", "pull", "/sdcard/{partition}.img", "{save_path}"],
            ["adb", "shell", "rm /sdcard/{partition}.img"]
        ],
        "fastboot_commands": [],
        "description": "Backup a partition",
        "requires_params": ["partition", "partition_path"]
    },
    "install_magisk": {
        "name": "Install Magisk",
        "category": "root",
        "adb_commands": [
            ["adb", "install", "-r", "{apk_path}"]
        ],
        "fastboot_commands": [],
        "description": "Install Magisk APK",
        "requires_download": True,
        "download_url": "https://api.github.com/repos/topjohnwu/Magisk/releases/latest"
    },
    "install_kernelsu": {
        "name": "Install KernelSU",
        "category": "root",
        "adb_commands": [
            ["adb", "install", "-r", "{apk_path}"]
        ],
        "fastboot_commands": [],
        "description": "Install KernelSU APK",
        "requires_download": True,
        "download_url": "https://api.github.com/repos/tiann/KernelSU/releases/latest"
    },
    "patch_magisk": {
        "name": "Patch Boot (Magisk)",
        "category": "root",
        "adb_commands": [
            ["adb", "push", "{stock_img}", "/sdcard/boot.img"],
            ["adb", "shell", "magisk --patch /sdcard/boot.img /sdcard/magisk_patched.img"],
            ["adb", "pull", "/sdcard/magisk_patched.img", "{output_path}"],
            ["adb", "shell", "rm /sdcard/boot.img /sdcard/magisk_patched.img"]
        ],
        "fastboot_commands": [],
        "description": "Patch boot.img with Magisk",
        "requires_file": True,
        "file_type": "img"
    },
    "pull_patched": {
        "name": "Pull Patched Images",
        "category": "root",
        "adb_commands": [
            ["adb", "pull", "/sdcard/Download/magisk_patched*.img", "{save_folder}"],
            ["adb", "pull", "/sdcard/magisk_patched*.img", "{save_folder}"],
            ["adb", "pull", "/sdcard/patched*.img", "{save_folder}"]
        ],
        "fastboot_commands": [],
        "description": "Pull patched images from device"
    },
    "list_devices": {
        "name": "List Devices",
        "category": "info",
        "adb_commands": [["adb", "devices"]],
        "fastboot_commands": [["fastboot", "devices"]],
        "description": "List connected ADB/Fastboot devices"
    },
    "device_info": {
        "name": "Get Device Info",
        "category": "info",
        "adb_commands": [
            ["adb", "shell", "getprop", "ro.product.model"],
            ["adb", "shell", "getprop", "ro.product.brand"],
            ["adb", "shell", "getprop", "ro.build.version.release"],
            ["adb", "shell", "getprop", "ro.product.cpu.abi"]
        ],
        "fastboot_commands": [],
        "description": "Get device information"
    },
    "check_root": {
        "name": "Check Root Status",
        "category": "info",
        "adb_commands": [
            ["adb", "shell", "which", "su"],
            ["adb", "shell", "magisk", "-c"]
        ],
        "fastboot_commands": [],
        "description": "Check if device is rooted"
    },
    "screencap": {
        "name": "Take Screenshot",
        "category": "tools",
        "adb_commands": [
            ["adb", "shell", "screencap", "/sdcard/screenshot.png"],
            ["adb", "pull", "/sdcard/screenshot.png", "{save_path}"],
            ["adb", "shell", "rm", "/sdcard/screenshot.png"]
        ],
        "fastboot_commands": [],
        "description": "Take screenshot from device"
    },
    "record_screen": {
        "name": "Record Screen",
        "category": "tools",
        "adb_commands": [
            ["adb", "shell", "screenrecord", "/sdcard/record.mp4"]
        ],
        "fastboot_commands": [],
        "description": "Record device screen",
        "requires_confirmation": True
    },
    "clear_logs": {
        "name": "Clear Logs",
        "category": "maintenance",
        "adb_commands": [
            ["adb", "logcat", "-c"]
        ],
        "fastboot_commands": [],
        "description": "Clear device logs"
    },
    "reboot_fastbootd": {
        "name": "Reboot Fastbootd",
        "category": "reboot",
        "adb_commands": [["adb", "reboot", "fastboot"]],
        "fastboot_commands": [],
        "description": "Reboot to fastbootd (dynamic partitions)"
    }
}

# ==============================
# API ENDPOINTS
# ==============================

@app.route('/api/commands', methods=['GET'])
@rate_limit
def get_commands():
    """Get all available commands"""
    global request_count, error_count
    request_count += 1
    
    try:
        categories = {}
        for cmd_id, cmd_data in COMMANDS.items():
            cat = cmd_data.get('category', 'other')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                'id': cmd_id,
                'name': cmd_data['name'],
                'description': cmd_data.get('description', ''),
                'requires_file': cmd_data.get('requires_file', False),
                'requires_confirmation': cmd_data.get('requires_confirmation', False),
                'file_type': cmd_data.get('file_type', ''),
                'warning': cmd_data.get('warning', '')
            })
        
        return jsonify({
            'success': True,
            'categories': categories,
            'commands': COMMANDS,
            'total_commands': len(COMMANDS)
        })
    except Exception as e:
        error_count += 1
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/command/<command_id>', methods=['GET'])
@rate_limit
def get_command(command_id):
    """Get specific command details"""
    global request_count, error_count
    request_count += 1
    
    if command_id not in COMMANDS:
        error_count += 1
        return jsonify({'success': False, 'error': 'Command not found'}), 404
    
    return jsonify({
        'success': True,
        'command': COMMANDS[command_id]
    })

@app.route('/api/execute', methods=['POST'])
@rate_limit
def execute_command():
    """Execute a command (returns the command structure, actual execution happens client-side)"""
    global request_count, error_count
    request_count += 1
    
    try:
        data = request.json
        command_id = data.get('command_id')
        params = data.get('params', {})
        
        if command_id not in COMMANDS:
            error_count += 1
            return jsonify({'success': False, 'error': 'Command not found'}), 404
        
        command = COMMANDS[command_id].copy()
        
        # Process params in commands
        if 'adb_commands' in command:
            processed_adb = []
            for cmd in command['adb_commands']:
                processed = []
                for part in cmd:
                    if isinstance(part, str):
                        # Replace placeholders
                        for key, value in params.items():
                            part = part.replace(f'{{{key}}}', str(value))
                    processed.append(part)
                processed_adb.append(processed)
            command['adb_commands'] = processed_adb
        
        if 'fastboot_commands' in command:
            processed_fastboot = []
            for cmd in command['fastboot_commands']:
                processed = []
                for part in cmd:
                    if isinstance(part, str):
                        for key, value in params.items():
                            part = part.replace(f'{{{key}}}', str(value))
                    processed.append(part)
                processed_fastboot.append(processed)
            command['fastboot_commands'] = processed_fastboot
        
        return jsonify({
            'success': True,
            'command': command
        })
    except Exception as e:
        error_count += 1
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/download-info/<command_id>', methods=['GET'])
@rate_limit
def get_download_info(command_id):
    """Get download information for commands that require downloads"""
    global request_count, error_count
    request_count += 1
    
    if command_id not in COMMANDS:
        error_count += 1
        return jsonify({'success': False, 'error': 'Command not found'}), 404
    
    command = COMMANDS[command_id]
    if not command.get('requires_download'):
        error_count += 1
        return jsonify({'success': False, 'error': 'Command does not require download'}), 400
    
    return jsonify({
        'success': True,
        'download_url': command.get('download_url'),
        'download_type': command.get('download_type', 'github_release')
    })

@app.route('/api/partition-list', methods=['GET'])
@rate_limit
def get_partitions():
    """Get list of common partitions"""
    global request_count
    request_count += 1
    
    partitions = {
        'boot': '/dev/block/by-name/boot',
        'recovery': '/dev/block/by-name/recovery',
        'system': '/dev/block/by-name/system',
        'vendor': '/dev/block/by-name/vendor',
        'userdata': '/dev/block/by-name/userdata',
        'cache': '/dev/block/by-name/cache',
        'dtbo': '/dev/block/by-name/dtbo',
        'vbmeta': '/dev/block/by-name/vbmeta',
        'super': '/dev/block/by-name/super',
        'init_boot': '/dev/block/by-name/init_boot'
    }
    return jsonify({'success': True, 'partitions': partitions})

# ==============================
# HEALTH AND UPTIME ENDPOINTS (For UptimeRobot)
# ==============================

@app.route('/api/health', methods=['GET'])
def health():
    """Basic health check endpoint (for UptimeRobot)"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'uptime_seconds': get_server_uptime(),
        'uptime_formatted': str(timedelta(seconds=get_server_uptime()))
    })

@app.route('/api/uptime', methods=['GET'])
def uptime():
    """Detailed uptime information (for UptimeRobot)"""
    uptime_seconds = get_server_uptime()
    return jsonify({
        'status': 'online',
        'uptime': {
            'seconds': uptime_seconds,
            'minutes': uptime_seconds // 60,
            'hours': uptime_seconds // 3600,
            'days': uptime_seconds // 86400,
            'formatted': str(timedelta(seconds=uptime_seconds))
        },
        'start_time': datetime.fromtimestamp(start_time).isoformat(),
        'current_time': datetime.now().isoformat()
    })

@app.route('/api/stats', methods=['GET'])
def stats():
    """Server statistics (for monitoring)"""
    uptime_seconds = get_server_uptime()
    return jsonify({
        'status': 'online',
        'uptime': uptime_seconds,
        'uptime_formatted': str(timedelta(seconds=uptime_seconds)),
        'requests': {
            'total': request_count,
            'errors': error_count,
            'success_rate': f"{((request_count - error_count) / request_count * 100):.2f}%" if request_count > 0 else "100%"
        },
        'system': get_system_stats(),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/ping', methods=['GET', 'HEAD'])
def ping():
    """Simple ping endpoint (fast response for monitoring)"""
    return jsonify({
        'pong': True,
        'timestamp': time.time()
    })

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with server information"""
    return jsonify({
        'name': 'JEPFX Command Server',
        'version': '2.0.0',
        'status': 'running',
        'endpoints': [
            '/api/health',
            '/api/uptime', 
            '/api/stats',
            '/api/ping',
            '/api/commands',
            '/api/command/<command_id>',
            '/api/execute',
            '/api/download-info/<command_id>',
            '/api/partition-list'
        ],
        'uptime': str(timedelta(seconds=get_server_uptime())),
        'documentation': 'https://github.com/JEPFX/command-server'
    })

# ==============================
# BACKGROUND UPTIME MONITORING (Optional)
# ==============================

def send_heartbeat():
    """Send heartbeat to UptimeRobot (if configured)"""
    if UPTIME_ROBOT_API_KEY and MONITOR_ID:
        try:
            # This is for UptimeRobot's push monitor feature
            url = f"https://api.uptimerobot.com/v2/push/{MONITOR_ID}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"Heartbeat sent to UptimeRobot at {datetime.now()}")
        except Exception as e:
            print(f"Failed to send heartbeat: {e}")

def heartbeat_loop():
    """Background thread to send periodic heartbeats"""
    while True:
        send_heartbeat()
        time.sleep(300)  # Send every 5 minutes

# Start heartbeat thread if configured
if UPTIME_ROBOT_API_KEY and MONITOR_ID:
    heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    print("Heartbeat monitoring enabled for UptimeRobot")

# ==============================
# MAIN ENTRY POINT
# ==============================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print("=" * 60)
    print("JEPFX COMMAND SERVER")
    print("=" * 60)
    print(f"Server starting on port {port}")
    print(f"Debug mode: {debug}")
    print(f"Total commands available: {len(COMMANDS)}")
    print(f"Rate limit: {RATE_LIMIT} requests/minute per IP")
    print("=" * 60)
    print("\nUptimeRobot Endpoints:")
    print(f"  • GET /api/health - Basic health check")
    print(f"  • GET /api/uptime - Uptime information")
    print(f"  • GET /api/stats - Server statistics")
    print(f"  • GET /api/ping - Simple ping response")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
