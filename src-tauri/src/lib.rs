//! Aura - The Intelligent Wellness Companion
//! 
//! This is the Tauri backend that manages:
//! - Python sidecar process lifecycle
//! - System tray integration
//! - IPC between frontend and Python engine

use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::{
    AppHandle, Emitter, Manager, State, PhysicalPosition,
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
};
use tauri_plugin_shell::{process::{CommandEvent, CommandChild}, ShellExt};
use tauri_plugin_autostart::MacosLauncher;

/// State for managing the Python sidecar process
struct SidecarState {
    is_running: Mutex<bool>,
    child: Mutex<Option<CommandChild>>,
}

/// State for pending break (shared between windows)
struct PendingBreakState {
    break_data: Mutex<Option<serde_json::Value>>,
}

/// Events emitted from the Python sidecar
#[derive(Debug, Clone, Serialize, Deserialize)]
struct SidecarEvent {
    #[serde(rename = "type")]
    event_type: String,
    data: Option<serde_json::Value>,
}

/// Send a command to the Python sidecar via stdin
#[tauri::command]
async fn send_to_sidecar(app: AppHandle, command: serde_json::Value) -> Result<(), String> {
    let state = app.state::<SidecarState>();
    let mut child_guard = state.child.lock().map_err(|e| e.to_string())?;
    
    if let Some(ref mut child) = *child_guard {
        let cmd_str = serde_json::to_string(&command).map_err(|e| e.to_string())?;
        child.write((cmd_str + "\n").as_bytes())
            .map_err(|e| format!("Failed to write to sidecar: {}", e))?;
        Ok(())
    } else {
        Err("Sidecar not running".to_string())
    }
}

/// Check if the sidecar is running
#[tauri::command]
fn is_sidecar_running(state: State<SidecarState>) -> bool {
    *state.is_running.lock().unwrap()
}

/// Log hydration with quick amounts
#[tauri::command]
async fn log_hydration(app: AppHandle, amount_ml: i32) -> Result<(), String> {
    let cmd = serde_json::json!({
        "cmd": "log_hydration",
        "amount_ml": amount_ml
    });
    send_to_sidecar(app, cmd).await
}

/// Complete a break
#[tauri::command]
async fn complete_break(app: AppHandle) -> Result<(), String> {
    // Hide overlay first
    if let Some(overlay) = app.get_webview_window("overlay") {
        let _ = overlay.hide();
    }
    let cmd = serde_json::json!({ "cmd": "complete_break" });
    send_to_sidecar(app, cmd).await
}

/// Snooze a break
#[tauri::command]
async fn snooze_break(app: AppHandle, minutes: i32) -> Result<(), String> {
    // Hide overlay first
    if let Some(overlay) = app.get_webview_window("overlay") {
        let _ = overlay.hide();
    }
    let cmd = serde_json::json!({
        "cmd": "snooze_break",
        "minutes": minutes
    });
    send_to_sidecar(app, cmd).await
}

/// Skip a break
#[tauri::command]
async fn skip_break(app: AppHandle) -> Result<(), String> {
    // Hide overlay first
    if let Some(overlay) = app.get_webview_window("overlay") {
        let _ = overlay.hide();
    }
    let cmd = serde_json::json!({ "cmd": "skip_break" });
    send_to_sidecar(app, cmd).await
}

/// Show the overlay window
#[tauri::command]
async fn show_overlay(app: AppHandle) -> Result<(), String> {
    if let Some(overlay) = app.get_webview_window("overlay") {
        overlay.show().map_err(|e| e.to_string())?;
        overlay.set_focus().map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err("Overlay window not found".to_string())
    }
}

/// Hide the overlay window
#[tauri::command]
async fn hide_overlay(app: AppHandle) -> Result<(), String> {
    if let Some(overlay) = app.get_webview_window("overlay") {
        overlay.hide().map_err(|e| e.to_string())?;
        Ok(())
    } else {
        Err("Overlay window not found".to_string())
    }
}

/// DEV: Trigger a test break - stores in state and shows overlay
#[tauri::command]
async fn trigger_test_break(app: AppHandle, break_type: String, duration_seconds: i32, theme_color: String) -> Result<(), String> {
    // Create the break event data
    let break_data = serde_json::json!({
        "break_type": break_type,
        "duration_seconds": duration_seconds,
        "theme_color": theme_color,
        "record_id": 999
    });
    
    // Store in shared state so overlay can retrieve it
    let pending_state = app.state::<PendingBreakState>();
    *pending_state.break_data.lock().unwrap() = Some(break_data.clone());
    
    // Show the overlay window
    if let Some(overlay) = app.get_webview_window("overlay") {
        overlay.show().map_err(|e| e.to_string())?;
        overlay.set_focus().map_err(|e| e.to_string())?;
        
        // Wait for overlay to initialize, then emit the event
        let app_clone = app.clone();
        let break_data_clone = break_data.clone();
        tauri::async_runtime::spawn(async move {
            // Give the overlay window time to set up its event listeners
            tokio::time::sleep(std::time::Duration::from_millis(300)).await;
            if let Some(overlay) = app_clone.get_webview_window("overlay") {
                let _ = overlay.emit("show-break", break_data_clone);
            }
        });
    }
    
    Ok(())
}

/// Get the pending break data (called by overlay window on mount)
#[tauri::command]
fn get_pending_break(app: AppHandle) -> Option<serde_json::Value> {
    let pending_state = app.state::<PendingBreakState>();
    let result = pending_state.break_data.lock().unwrap().clone();
    result
}

/// Clear the pending break (called after overlay handles it)
#[tauri::command]
fn clear_pending_break(app: AppHandle) {
    let pending_state = app.state::<PendingBreakState>();
    *pending_state.break_data.lock().unwrap() = None;
}

/// Pause reminders
#[tauri::command]
async fn pause_reminders(app: AppHandle, minutes: Option<i32>) -> Result<(), String> {
    let cmd = serde_json::json!({
        "cmd": "pause",
        "minutes": minutes
    });
    send_to_sidecar(app, cmd).await
}

/// Resume reminders
#[tauri::command]
async fn resume_reminders(app: AppHandle) -> Result<(), String> {
    let cmd = serde_json::json!({ "cmd": "resume" });
    send_to_sidecar(app, cmd).await
}

/// Get current status
#[tauri::command]
async fn get_status(app: AppHandle) -> Result<(), String> {
    let cmd = serde_json::json!({ "cmd": "get_status" });
    send_to_sidecar(app, cmd).await
}

/// Get training data stats
#[tauri::command]
async fn get_training_stats(app: AppHandle) -> Result<(), String> {
    let cmd = serde_json::json!({ "cmd": "get_training_stats" });
    send_to_sidecar(app, cmd).await
}

/// Get all settings
#[tauri::command]
async fn get_settings(app: AppHandle) -> Result<(), String> {
    let cmd = serde_json::json!({ "cmd": "get_settings" });
    send_to_sidecar(app, cmd).await
}

/// Update a single setting
#[tauri::command]
async fn update_setting(app: AppHandle, key: String, value: String) -> Result<(), String> {
    let cmd = serde_json::json!({
        "cmd": "update_setting",
        "key": key,
        "value": value
    });
    send_to_sidecar(app, cmd).await
}

/// Export training data to CSV
#[tauri::command]
async fn export_data(app: AppHandle, path: String) -> Result<(), String> {
    let cmd = serde_json::json!({
        "cmd": "export_data",
        "path": path
    });
    send_to_sidecar(app, cmd).await
}

// ===== SESSION CONTROL COMMANDS =====

/// Start a work session - timers begin counting
#[tauri::command]
async fn start_session(app: AppHandle) -> Result<(), String> {
    let cmd = serde_json::json!({ "cmd": "start_session" });
    send_to_sidecar(app, cmd).await
}

/// Pause the work session - timers freeze
#[tauri::command]
async fn pause_session(app: AppHandle) -> Result<(), String> {
    let cmd = serde_json::json!({ "cmd": "pause_session" });
    send_to_sidecar(app, cmd).await
}

/// Resume a paused work session
#[tauri::command]
async fn resume_session(app: AppHandle) -> Result<(), String> {
    let cmd = serde_json::json!({ "cmd": "resume_session" });
    send_to_sidecar(app, cmd).await
}

/// End the work session - resets all timers
#[tauri::command]
async fn end_session(app: AppHandle) -> Result<(), String> {
    let cmd = serde_json::json!({ "cmd": "end_session" });
    send_to_sidecar(app, cmd).await
}

// ===== SCHEDULE RULES COMMANDS =====

/// Get all schedule rules
#[tauri::command]
async fn get_schedule_rules(app: AppHandle) -> Result<(), String> {
    let cmd = serde_json::json!({ "cmd": "get_schedule_rules" });
    send_to_sidecar(app, cmd).await
}

/// Add a new schedule rule
#[tauri::command]
async fn add_schedule_rule(app: AppHandle, time: String, action: String, days: Vec<String>, title: Option<String>) -> Result<(), String> {
    let cmd = serde_json::json!({
        "cmd": "add_schedule_rule",
        "time": time,
        "action": action,
        "days": days,
        "title": title.unwrap_or_default()
    });
    send_to_sidecar(app, cmd).await
}

/// Update an existing schedule rule
#[tauri::command]
async fn update_schedule_rule(app: AppHandle, id: i32, time: String, action: String, days: Vec<String>, enabled: bool, title: Option<String>) -> Result<(), String> {
    let cmd = serde_json::json!({
        "cmd": "update_schedule_rule",
        "id": id,
        "time": time,
        "action": action,
        "days": days,
        "enabled": enabled,
        "title": title.unwrap_or_default()
    });
    send_to_sidecar(app, cmd).await
}

/// Delete a schedule rule
#[tauri::command]
async fn delete_schedule_rule(app: AppHandle, id: i32) -> Result<(), String> {
    let cmd = serde_json::json!({
        "cmd": "delete_schedule_rule",
        "id": id
    });
    send_to_sidecar(app, cmd).await
}

/// Reset all break timers without changing session state
#[tauri::command]
async fn reset_all_timers(app: AppHandle) -> Result<(), String> {
    let cmd = serde_json::json!({ "cmd": "reset_all_timers" });
    send_to_sidecar(app, cmd).await
}

/// Helper function to write command to sidecar stdin
fn write_to_sidecar(app: &AppHandle, command: serde_json::Value) {
    if let Some(state) = app.try_state::<SidecarState>() {
        if let Ok(mut child_guard) = state.child.lock() {
            if let Some(ref mut child) = *child_guard {
                if let Ok(cmd_str) = serde_json::to_string(&command) {
                    let _ = child.write((cmd_str + "\n").as_bytes());
                }
            }
        }
    }
}

/// Setup system tray
fn setup_tray(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let quit = MenuItem::with_id(app, "quit", "Quit Aura", true, None::<&str>)?;
    let show = MenuItem::with_id(app, "show", "Show Dashboard", true, None::<&str>)?;
    let separator1 = MenuItem::with_id(app, "sep1", "─────────────", false, None::<&str>)?;
    let pause_30m = MenuItem::with_id(app, "pause_30m", "⏸️ Pause 30 min", true, None::<&str>)?;
    let pause_1h = MenuItem::with_id(app, "pause_1h", "⏸️ Pause 1 hour", true, None::<&str>)?;
    let pause_2h = MenuItem::with_id(app, "pause_2h", "⏸️ Pause 2 hours", true, None::<&str>)?;
    let pause_movie = MenuItem::with_id(app, "pause_movie", "🎬 Movie mode (8h)", true, None::<&str>)?;
    let resume = MenuItem::with_id(app, "resume", "▶️ Resume", true, None::<&str>)?;
    let separator2 = MenuItem::with_id(app, "sep2", "─────────────", false, None::<&str>)?;
    
    let menu = Menu::with_items(app, &[
        &show, 
        &separator1,
        &pause_30m,
        &pause_1h, 
        &pause_2h,
        &pause_movie,
        &resume, 
        &separator2,
        &quit
    ])?;
    
    let _tray = TrayIconBuilder::new()
        .icon(app.default_window_icon().unwrap().clone())
        .menu(&menu)
        .tooltip("Aura - Wellness Companion")
        .show_menu_on_left_click(false)
        .on_menu_event(|app, event| match event.id.as_ref() {
            "quit" => {
                // Send shutdown to sidecar before quitting
                write_to_sidecar(app, serde_json::json!({"cmd": "shutdown"}));
                std::thread::sleep(std::time::Duration::from_millis(500));
                app.exit(0);
            }
            "show" => {
                if let Some(window) = app.get_webview_window("session") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            "pause_30m" => {
                write_to_sidecar(app, serde_json::json!({
                    "cmd": "pause",
                    "minutes": 30
                }));
                // Emit event to frontend so UI can update
                let _ = app.emit("sidecar-paused", serde_json::json!({"minutes": 30}));
            }
            "pause_1h" => {
                write_to_sidecar(app, serde_json::json!({
                    "cmd": "pause",
                    "minutes": 60
                }));
                let _ = app.emit("sidecar-paused", serde_json::json!({"minutes": 60}));
            }
            "pause_2h" => {
                write_to_sidecar(app, serde_json::json!({
                    "cmd": "pause",
                    "minutes": 120
                }));
                let _ = app.emit("sidecar-paused", serde_json::json!({"minutes": 120}));
            }
            "pause_movie" => {
                write_to_sidecar(app, serde_json::json!({
                    "cmd": "pause",
                    "minutes": 480
                }));
                let _ = app.emit("sidecar-paused", serde_json::json!({"minutes": 480}));
            }
            "resume" => {
                write_to_sidecar(app, serde_json::json!({"cmd": "resume"}));
                let _ = app.emit("sidecar-resumed", serde_json::json!({}));
            }
            _ => {}
        })
        .on_tray_icon_event(|tray, event| {
            if let TrayIconEvent::Click {
                button: MouseButton::Left,
                button_state: MouseButtonState::Up,
                ..
            } = event
            {
                let app = tray.app_handle();
                // Show Session Hub window on tray click
                if let Some(window) = app.get_webview_window("session") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        })
        .build(app)?;
    
    Ok(())
}

/// Start the Python sidecar process
fn start_sidecar(app: &AppHandle) {
    let app_handle = app.clone();
    let state = app.state::<SidecarState>();
    
    // In both development and production, use the bundled sidecar binary
    // The binary is built with PyInstaller and placed in src-tauri/
    println!("[Aura] Creating sidecar command...");
    let sidecar_cmd = match app_handle.shell().sidecar("aura-sidecar") {
        Ok(cmd) => {
            println!("[Aura] Sidecar command created successfully");
            cmd
        }
        Err(e) => {
            eprintln!("[Aura] Failed to create sidecar command: {}", e);
            return;
        }
    };
    
    println!("[Aura] Spawning sidecar...");
    let (mut rx, child) = match sidecar_cmd.spawn() {
        Ok(result) => {
            println!("[Aura] Sidecar spawned successfully");
            result
        }
        Err(e) => {
            eprintln!("[Aura] Failed to spawn sidecar: {}", e);
            return;
        }
    };
    
    // Store the child process for stdin writing
    {
        let mut child_guard = state.child.lock().unwrap();
        *child_guard = Some(child);
    }
    
    *state.is_running.lock().unwrap() = true;
    
    // Handle sidecar stdout events
    let app_for_events = app_handle.clone();
    println!("[Aura] Starting event listener loop...");
    tauri::async_runtime::spawn(async move {
        println!("[Aura] Event loop started, waiting for sidecar output...");
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    println!("[Aura] Received stdout: {}", line_str);
                    // Parse JSON and emit to frontend
                    match serde_json::from_slice::<SidecarEvent>(&line) {
                        Ok(sidecar_event) => {
                            let event_name = format!("sidecar-{}", sidecar_event.event_type);
                            println!("[Aura] Emitting event: {}", event_name);
                            
                            // IMPORTANT: Show overlay window when break is due
                            if sidecar_event.event_type == "break_due" {
                                println!("[Aura] Break due! Showing overlay window...");
                                
                                // Store break data in PendingBreakState so overlay can retrieve it
                                if let Some(data) = &sidecar_event.data {
                                    if let Some(pending_state) = app_for_events.try_state::<PendingBreakState>() {
                                        *pending_state.break_data.lock().unwrap() = Some(data.clone());
                                    }
                                }
                                
                                // Show overlay and emit event after delay
                                if let Some(overlay) = app_for_events.get_webview_window("overlay") {
                                    let _ = overlay.show();
                                    let _ = overlay.set_focus();
                                    
                                    // Emit event after delay to give JS time to initialize
                                    let break_data = sidecar_event.data.clone();
                                    let app_clone = app_for_events.clone();
                                    tauri::async_runtime::spawn(async move {
                                        tokio::time::sleep(std::time::Duration::from_millis(300)).await;
                                        if let Some(overlay) = app_clone.get_webview_window("overlay") {
                                            if let Some(data) = break_data {
                                                let _ = overlay.emit("show-break", data);
                                            }
                                        }
                                    });
                                }
                            } else if sidecar_event.event_type == "schedule_warning" {
                                println!("[Aura] Schedule warning! Showing notification window...");
                                
                                if let Some(window) = app_for_events.get_webview_window("notification") {
                                    // Calculate position (Bottom-Right)
                                    let monitor = window.current_monitor().ok().flatten()
                                        .or_else(|| window.primary_monitor().ok().flatten());
                                        
                                    if let Some(monitor) = monitor {
                                        let screen_size = monitor.size();
                                        // Hardcoded window size (must match tauri.conf.json)
                                        let window_width = 280;
                                        let window_height = 320;
                                        let padding = 20;
                                        
                                        // Calculate position
                                        let x = (screen_size.width as i32) - window_width - padding;
                                        let y = (screen_size.height as i32) - window_height - padding;
                                        
                                        let _ = window.set_position(PhysicalPosition::new(x, y));
                                    }
                                    
                                    let _ = window.show();
                                    // Use set_always_on_top to ensure visibility
                                    let _ = window.set_always_on_top(true);
                                    
                                    // Emit event with data
                                    let event_data = sidecar_event.data.clone();
                                    let app_clone = app_for_events.clone();
                                    tauri::async_runtime::spawn(async move {
                                        // Small delay for frontend init
                                        tokio::time::sleep(std::time::Duration::from_millis(800)).await;
                                        if let Some(win) = app_clone.get_webview_window("notification") {
                                            if let Some(data) = event_data {
                                                let _ = win.emit("show-schedule-warning", data);
                                            }
                                        }
                                    });
                                }
                            }
                            
                            let _ = app_for_events.emit(&event_name, sidecar_event);
                        }
                        Err(e) => {
                            eprintln!("[Aura] Failed to parse JSON: {} - raw: {}", e, line_str);
                        }
                    }
                }
                CommandEvent::Stderr(line) => {
                    let line_str = String::from_utf8_lossy(&line);
                    eprintln!("[Sidecar Error] {}", line_str);
                }
                CommandEvent::Error(err) => {
                    eprintln!("[Sidecar] Error: {}", err);
                }
                CommandEvent::Terminated(status) => {
                    eprintln!("[Sidecar] Terminated with status: {:?}", status);
                    if let Some(state) = app_for_events.try_state::<SidecarState>() {
                        *state.is_running.lock().unwrap() = false;
                        // Clear the child reference
                        if let Ok(mut child_guard) = state.child.lock() {
                            *child_guard = None;
                        }
                    }
                    // AUTO-RESTART: Try to restart sidecar after 2 seconds
                    let app_restart = app_for_events.clone();
                    println!("[Aura] Sidecar terminated, will attempt restart in 2 seconds...");
                    tauri::async_runtime::spawn(async move {
                        tokio::time::sleep(std::time::Duration::from_secs(2)).await;
                        println!("[Aura] Attempting sidecar restart...");
                        start_sidecar(&app_restart);
                    });
                }
                _ => {}
            }
        }
    });
}

/// Enable autostart (start with Windows)
#[tauri::command]
async fn enable_autostart(app: AppHandle) -> Result<(), String> {
    use tauri_plugin_autostart::ManagerExt;
    app.autolaunch().enable().map_err(|e| e.to_string())
}

/// Disable autostart
#[tauri::command]
async fn disable_autostart(app: AppHandle) -> Result<(), String> {
    use tauri_plugin_autostart::ManagerExt;
    app.autolaunch().disable().map_err(|e| e.to_string())
}

/// Check if autostart is enabled
#[tauri::command]
async fn is_autostart_enabled(app: AppHandle) -> Result<bool, String> {
    use tauri_plugin_autostart::ManagerExt;
    app.autolaunch().is_enabled().map_err(|e| e.to_string())
}

/// Debug command to show notification window
#[tauri::command]
fn debug_notification(app: AppHandle) {
    if let Some(window) = app.get_webview_window("notification") {
        // Position logic
        let monitor = window.current_monitor().ok().flatten()
            .or_else(|| window.primary_monitor().ok().flatten());
            
        if let Some(monitor) = monitor {
            let screen_size = monitor.size();
            let window_width = 280;
            let window_height = 320;
            let padding = 20;
            let x = (screen_size.width as i32) - window_width - padding;
            let y = (screen_size.height as i32) - window_height - padding;
            let _ = window.set_position(PhysicalPosition::new(x, y));
        }
        
        let _ = window.show();
        let _ = window.set_always_on_top(true);
        let _ = window.set_focus();
        
        // Spawn async task to wait and emit, preventing main thread block
        let window_clone = window.clone();
        tauri::async_runtime::spawn(async move {
            // Small delay to ensure frontend is ready
            tokio::time::sleep(std::time::Duration::from_millis(500)).await;
            
            // Emit dummy data
            let _ = window_clone.emit("show-schedule-warning", serde_json::json!({
                "title": "Debug Test Warning",
                "action": "pause",
                "seconds_remaining": 60
            }));
        });
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_autostart::init(MacosLauncher::LaunchAgent, Some(vec!["--minimized"])))
        .manage(SidecarState {
            is_running: Mutex::new(false),
            child: Mutex::new(None),
        })
        .manage(PendingBreakState {
            break_data: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            send_to_sidecar,
            is_sidecar_running,
            log_hydration,
            complete_break,
            snooze_break,
            skip_break,
            pause_reminders,
            resume_reminders,
            get_status,
            get_training_stats,
            get_settings,
            update_setting,
            export_data,
            show_overlay,
            hide_overlay,
            debug_notification,
            trigger_test_break,
            get_pending_break,
            clear_pending_break,
            enable_autostart,
            disable_autostart,
            is_autostart_enabled,
            // Session control
            start_session,
            pause_session,
            resume_session,
            end_session,
            // Schedule rules
            get_schedule_rules,
            add_schedule_rule,
            update_schedule_rule,
            delete_schedule_rule,
            reset_all_timers,
        ])
        .setup(|app| {
            // Check if started with --minimized flag (autostart at system boot)
            let args: Vec<String> = std::env::args().collect();
            let is_minimized = args.iter().any(|arg| arg == "--minimized");
            
            if is_minimized {
                println!("[Aura] Started with --minimized flag, hiding main window");
                // Hide the main window when started at system boot
                // This prevents the broken Edge error page that can appear
                // when WebView2 isn't fully ready at system startup
                if let Some(window) = app.get_webview_window("main") {
                    let _ = window.hide();
                }
            }
            
            // Setup system tray
            if let Err(e) = setup_tray(app.handle()) {
                eprintln!("Failed to setup tray: {}", e);
            }
            
            // Start Python sidecar (even when minimized, we need the engine running)
            start_sidecar(app.handle());
            
            Ok(())
        })
        .on_window_event(|window, event| {
            // Minimize to tray on close
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                window.hide().unwrap();
                api.prevent_close();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
