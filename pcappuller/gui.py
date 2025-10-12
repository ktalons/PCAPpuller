from __future__ import annotations

import threading
import traceback
import tempfile
from pathlib import Path
import datetime as dt

try:
    import PySimpleGUI as sg
except Exception:
    raise SystemExit("PySimpleGUI not installed. Install with: python3 -m pip install PySimpleGUI")

from .workflow import ThreeStepWorkflow
from .core import Window, parse_workers
from .time_parse import parse_dt_flexible
from .errors import PCAPPullerError
from .filters import COMMON_FILTERS, FILTER_EXAMPLES
from .cache import CapinfosCache, default_cache_path


def compute_recommended_v2(duration_minutes: int) -> dict:
    """Compute recommended settings for the new three-step workflow."""
    if duration_minutes <= 15:
        batch = 500
        slop = 120
    elif duration_minutes <= 60:
        batch = 400
        slop = 60
    elif duration_minutes <= 240:
        batch = 300
        slop = 30
    elif duration_minutes <= 720:
        batch = 200
        slop = 20
    else:
        batch = 150
        slop = 15
    return {
        "workers": "auto",
        "batch": batch,
        "slop": slop,
        "trim_per_batch": duration_minutes > 60,
        "precise_filter": True,
    }


def _open_advanced_settings_v2(parent: "sg.Window", reco: dict, current: dict | None) -> dict | None:
    """Advanced settings dialog for v2 workflow."""
    cur = {
        "workers": (current.get("workers") if current else reco["workers"]),
        "batch": (current.get("batch") if current else reco["batch"]),
        "slop": (current.get("slop") if current else reco["slop"]),
        "trim_per_batch": (current.get("trim_per_batch") if current else reco["trim_per_batch"]),
        "precise_filter": (current.get("precise_filter") if current else reco["precise_filter"]),
    }
    
    layout = [
        [sg.Text("Advanced Settings (override recommendations)", font=("Arial", 12, "bold"))],
        [sg.HSeparator()],
        [sg.Text("Step 1: Selection", font=("Arial", 10, "bold"))],
        [sg.Text("Workers"), sg.Input(str(cur["workers"]), key="-A-WORKERS-", size=(8,1)), sg.Text("(use 'auto' or integer 1-64)")],
        [sg.Text("Slop min"), sg.Input(str(cur["slop"]), key="-A-SLOP-", size=(8,1)), sg.Text("Extra minutes around window for mtime prefilter")],
        [sg.Checkbox("Precise filter", key="-A-PRECISE-", default=bool(cur["precise_filter"]), tooltip="Use capinfos to verify packet times")],
        [sg.HSeparator()],
        [sg.Text("Step 2: Processing", font=("Arial", 10, "bold"))],
        [sg.Text("Batch size"), sg.Input(str(cur["batch"]), key="-A-BATCH-", size=(8,1)), sg.Text("Files per merge batch")],
        [sg.Checkbox("Trim per batch", key="-A-TRIMPB-", default=bool(cur["trim_per_batch"]), tooltip="Trim each batch vs final file only")],
        [sg.HSeparator()],
        [sg.Button("Save"), sg.Button("Cancel")],
    ]
    
    win = sg.Window("Advanced Settings", layout, modal=True, keep_on_top=True, size=(500, 350))
    overrides = current or {}
    
    while True:
        ev, vals = win.read()
        if ev in (sg.WINDOW_CLOSED, "Cancel"):
            win.close()
            return current
        if ev == "Save":
            # Validate and save workers
            wv = (vals.get("-A-WORKERS-") or "auto").strip()
            if wv.lower() != "auto":
                try:
                    w_int = int(wv)
                    if not (1 <= w_int <= 64):
                        raise ValueError
                    overrides["workers"] = w_int
                except Exception:
                    sg.popup_error("Workers must be 'auto' or an integer 1-64")
                    continue
            else:
                overrides["workers"] = "auto"
            
            # Validate other settings
            try:
                b_int = int(vals.get("-A-BATCH-") or reco["batch"])
                s_int = int(vals.get("-A-SLOP-") or reco["slop"])
                if b_int < 1 or s_int < 0:
                    raise ValueError
                overrides["batch"] = b_int
                overrides["slop"] = s_int
            except Exception:
                sg.popup_error("Batch size must be >=1 and Slop >=0")
                continue
                
            overrides["trim_per_batch"] = bool(vals.get("-A-TRIMPB-"))
            overrides["precise_filter"] = bool(vals.get("-A-PRECISE-"))
            win.close()
            return overrides


def _open_filters_dialog(parent: "sg.Window") -> str | None:
    """Display filters selection dialog."""
    entries = [f"Examples: {e}" for e in FILTER_EXAMPLES]
    for cat, items in COMMON_FILTERS.items():
        for it in items:
            entries.append(f"{cat}: {it}")
            
    layout = [
        [sg.Text("Search"), sg.Input(key="-FSEARCH-", enable_events=True, expand_x=True)],
        [sg.Listbox(values=entries, key="-FLIST-", size=(80, 20), enable_events=True)],
        [sg.Button("Insert"), sg.Button("Close")],
    ]
    
    win = sg.Window("Display Filters", layout, modal=True, keep_on_top=True)
    selected: str | None = None
    current = entries
    
    while True:
        ev, vals = win.read()
        if ev in (sg.WINDOW_CLOSED, "Close"):
            break
        if ev == "-FSEARCH-":
            q = (vals.get("-FSEARCH-") or "").lower()
            current = [e for e in entries if q in e.lower()] if q else entries
            win["-FLIST-"].update(current)
        elif ev == "-FLIST-" and vals.get("-FLIST-"):
            if isinstance(vals["-FLIST-"], list) and vals["-FLIST-"]:
                selected = vals["-FLIST-"][0]
        elif ev == "Insert":
            if isinstance(vals.get("-FLIST-"), list) and vals["-FLIST-"]:
                selected = vals["-FLIST-"][0]
                break
                
    win.close()
    if selected and ":" in selected:
        selected = selected.split(":", 1)[1].strip()
    return selected


def _open_pattern_settings(parent: "sg.Window", current_include: list, current_exclude: list) -> tuple | None:
    """Pattern settings dialog for file filtering."""
    layout = [
        [sg.Text("File Pattern Filtering", font=("Arial", 12, "bold"))],
        [sg.Text("Use patterns to control which files are selected in Step 1")],
        [sg.HSeparator()],
        [sg.Text("Include Patterns (files matching these will be selected):")],
        [sg.Multiline("\n".join(current_include), key="-INCLUDE-", size=(50, 5))],
        [sg.Text("Examples: *.chunk_*.pcap, capture_*.pcap, *.pcapng")],
        [sg.HSeparator()],
        [sg.Text("Exclude Patterns (files matching these will be skipped):")],
        [sg.Multiline("\n".join(current_exclude), key="-EXCLUDE-", size=(50, 5))],
        [sg.Text("Examples: *.sorted.pcap, *.backup.pcap, *.temp.*")],
        [sg.HSeparator()],
        [sg.Button("Save"), sg.Button("Reset to Defaults"), sg.Button("Cancel")],
    ]
    
    win = sg.Window("File Pattern Settings", layout, modal=True, keep_on_top=True, size=(600, 400))
    
    while True:
        ev, vals = win.read()
        if ev in (sg.WINDOW_CLOSED, "Cancel"):
            win.close()
            return None
        elif ev == "Reset to Defaults":
            win["-INCLUDE-"].update("*.pcap\n*.pcapng")
            win["-EXCLUDE-"].update("")
        elif ev == "Save":
            include_text = vals.get("-INCLUDE-", "").strip()
            exclude_text = vals.get("-EXCLUDE-", "").strip()
            
            include_patterns = [p.strip() for p in include_text.split("\n") if p.strip()]
            exclude_patterns = [p.strip() for p in exclude_text.split("\n") if p.strip()]
            
            if not include_patterns:
                sg.popup_error("At least one include pattern is required")
                continue
                
            win.close()
            return (include_patterns, exclude_patterns)
    
    win.close()
    return None


def run_workflow_v2(values: dict, window: "sg.Window", stop_flag: dict, adv_overrides: dict | None) -> None:
    """Run the three-step workflow."""
    try:
        # Parse time window
        start = parse_dt_flexible(values["-START-"])
        hours = int(values.get("-HOURS-", 0) or 0)
        mins = int(values.get("-MINS-", 0) or 0)
        total_minutes = min(hours * 60 + mins, 1440)
        
        if total_minutes <= 0:
            raise PCAPPullerError("Duration must be greater than 0 minutes")
            
        desired_end = start + dt.timedelta(minutes=total_minutes)
        if desired_end.date() != start.date():
            desired_end = dt.datetime.combine(start.date(), dt.time(23, 59, 59, 999999))
            
        window_obj = Window(start=start, end=desired_end)
        roots = [Path(values["-SOURCE-"])] if values.get("-SOURCE-") else []
        
        if not roots:
            raise PCAPPullerError("Source directory is required")
            
        # Create workspace in temp directory
        workspace_name = f"pcappuller_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        workspace_dir = Path(tempfile.gettempdir()) / workspace_name
        
        # Initialize workflow
        workflow = ThreeStepWorkflow(workspace_dir)
        
        # Get pattern settings from values
        include_patterns = values.get("-INCLUDE-PATTERNS-", ["*.pcap", "*.pcapng"])
        exclude_patterns = values.get("-EXCLUDE-PATTERNS-", [])
        
        state = workflow.initialize_workflow(
            root_dirs=roots,
            window=window_obj,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns
        )
        
        # Setup progress callback
        def progress_callback(phase: str, current: int, total: int):
            if stop_flag["stop"]:
                raise PCAPPullerError("Cancelled")
            window.write_event_value("-PROGRESS-", (phase, current, total))
        
        # Get effective settings
        reco = compute_recommended_v2(total_minutes)
        eff_settings = adv_overrides.copy() if adv_overrides else {}
        for key, val in reco.items():
            if key not in eff_settings:
                eff_settings[key] = val
        
        # Setup cache
        cache = None
        if not values.get("-NO-CACHE-"):
            cache_path = default_cache_path()
            cache = CapinfosCache(cache_path)
            if values.get("-CLEAR-CACHE-"):
                cache.clear()
        
        # Determine which steps to run
        run_step1 = values.get("-RUN-STEP1-", True)
        run_step2 = values.get("-RUN-STEP2-", True) 
        run_step3 = values.get("-RUN-STEP3-", False)
        
        try:
            # Verbose: announce core settings
            print("Configuration:")
            print(f"  Source: {roots[0]}")
            print(f"  Window: {window_obj.start} .. {window_obj.end}")
            print(f"  Selection: manifest (Step 1 uses mtime+pattern only)")
            print(f"  Output: {values.get('-OUT-', '(workspace default)')}")
            print(f"  Tmpdir: {values.get('-TMPDIR-', '(workspace tmp)')}")
            print(f"  Effective settings: workers={eff_settings['workers']}, batch={eff_settings['batch']}, slop={eff_settings['slop']}, trim_per_batch={eff_settings['trim_per_batch']}, precise_in_step2={eff_settings['precise_filter']}")
            
            # Step 1: Select and Move
            if run_step1:
                window.write_event_value("-STEP-UPDATE-", ("Step 1: Selecting files...", 1))
                
                workers = parse_workers(eff_settings["workers"], 1000)
                state = workflow.step1_select_and_move(
                    state=state,
                    slop_min=eff_settings["slop"],
                    precise_filter=False,  # moved to Step 2
                    workers=workers,
                    cache=cache,
                    dry_run=values.get("-DRYRUN-", False),
                    progress_callback=progress_callback
                )
                
                if values.get("-DRYRUN-", False):
                    if state.selected_files:
                        total_size = sum(f.stat().st_size for f in state.selected_files) / (1024*1024)
                        window.write_event_value("-DONE-", f"Dry-run complete: {len(state.selected_files)} files selected ({total_size:.1f} MB)")
                    else:
                        window.write_event_value("-DONE-", "Dry-run complete: 0 files selected")
                    return
                    
                if not state.selected_files:
                    print("Step 1 selected 0 files.")
                    window.write_event_value("-DONE-", "No files selected in Step 1")
                    return
                else:
                    total_size_mb = sum(f.stat().st_size for f in state.selected_files) / (1024*1024)
                    print(f"Step 1 selected {len(state.selected_files)} files ({total_size_mb:.1f} MB)")
            
            # Step 2: Process
            if run_step2:
                window.write_event_value("-STEP-UPDATE-", ("Step 2: Processing files...", 2))
                print("Step 2: Applying precise filter and processing...")
                print(f"  Batch size: {eff_settings['batch']} | Trim per batch: {eff_settings['trim_per_batch']}")
                if values.get("-DFILTER-"):
                    print(f"  Display filter: {values['-DFILTER-']}")
                
                state = workflow.step2_process(
                    state=state,
                    batch_size=eff_settings["batch"],
                    out_format=values["-FORMAT-"],
                    display_filter=values["-DFILTER-"] or None,
                    trim_per_batch=eff_settings["trim_per_batch"],
                    progress_callback=progress_callback,
                    verbose=values.get("-VERBOSE-", False),
                    out_path=(Path(values["-OUT-"]) if values.get("-OUT-") else None),
                    tmpdir_parent=(Path(values["-TMPDIR-"]) if values.get("-TMPDIR-") else None),
                    precise_filter=eff_settings["precise_filter"],
                    workers=parse_workers(eff_settings["workers"], 1000),
                    cache=cache,
                )
            
            # Step 3: Clean
            if run_step3:
                window.write_event_value("-STEP-UPDATE-", ("Step 3: Cleaning output...", 3))
                
                clean_options = {}
                if values.get("-CLEAN-SNAPLEN-"):
                    try:
                        snaplen = int(values["-CLEAN-SNAPLEN-"])
                        if snaplen > 0:
                            clean_options["snaplen"] = snaplen
                    except ValueError:
                        pass
                        
                if values.get("-CLEAN-CONVERT-"):
                    clean_options["convert_to_pcap"] = True
                    
                if values.get("-GZIP-"):
                    clean_options["gzip"] = True
                
                # If no options were specified but Step 3 is enabled, apply sensible defaults
                if not clean_options:
                    clean_options = {"snaplen": 256, "gzip": True}
                state = workflow.step3_clean(
                    state=state,
                    options=clean_options,
                    progress_callback=progress_callback,
                    verbose=values.get("-VERBOSE-", False)
                )
            
            # Determine final output
            final_file = state.cleaned_file or state.processed_file
            if final_file and final_file.exists():
                size_mb = final_file.stat().st_size / (1024*1024)
                window.write_event_value("-WORKFLOW-RESULT-", str(final_file))
                window.write_event_value("-DONE-", f"Workflow complete! Final output: {final_file} ({size_mb:.1f} MB)")
            else:
                window.write_event_value("-DONE-", "Workflow complete but no output file found")
                
        finally:
            if cache:
                cache.close()
                
    except Exception as e:
        tb = traceback.format_exc()
        window.write_event_value("-DONE-", f"Error: {e}\n{tb}")


def main():
    """Main GUI function using the three-step workflow."""
    sg.theme("SystemDefault")
    
    # Default patterns
    default_include = ["*.pcap", "*.pcapng"]
    default_exclude = []
    
    # Create layout with three-step workflow
    layout = [
        [sg.Text("PCAPpuller - Three-Step Workflow", font=("Arial", 14, "bold"))],
        [sg.HSeparator()],
        
        # Basic settings
        [sg.Text("Source Directory"), sg.Input(key="-SOURCE-", expand_x=True), sg.FolderBrowse()],
        [sg.Text("Start Time (YYYY-MM-DD HH:MM:SS)"), sg.Input(key="-START-", expand_x=True)],
        [sg.Text("Duration"), 
         sg.Text("Hours"), sg.Slider(range=(0, 24), orientation="h", key="-HOURS-", default_value=0, size=(20,15), enable_events=True),
         sg.Text("Minutes"), sg.Slider(range=(0, 59), orientation="h", key="-MINS-", default_value=15, size=(20,15), enable_events=True),
         sg.Button("All Day", key="-ALLDAY-")],
        [sg.Text("Output File"), sg.Input(key="-OUT-", expand_x=True), sg.FileSaveAs()],
        [sg.Text("Temporary Directory"), sg.Input(key="-TMPDIR-", expand_x=True), sg.FolderBrowse()],
        
        [sg.HSeparator()],
        
        # Workflow steps
        [sg.Frame("Workflow Steps", [
            [sg.Checkbox("Step 1: Select & Filter Files", key="-RUN-STEP1-", default=True, tooltip="Filter and copy relevant files to workspace")],
            [sg.Checkbox("Step 2: Merge & Process", key="-RUN-STEP2-", default=True, tooltip="Merge, trim, and filter selected files")],
            [sg.Checkbox("Step 3: Clean & Compress", key="-RUN-STEP3-", default=False, tooltip="Remove headers/metadata and compress")],
        ], expand_x=True)],
        
        [sg.HSeparator()],
        
        # Step 2 & 3 settings
        [sg.Frame("Processing Options", [
            [sg.Text("Output Format"), sg.Combo(values=["pcap", "pcapng"], default_value="pcapng", key="-FORMAT-"),
             sg.Checkbox("Verbose", key="-VERBOSE-"), sg.Checkbox("Dry Run", key="-DRYRUN-")],
            [sg.Text("Display Filter"), sg.Input(key="-DFILTER-", expand_x=True), sg.Button("Filters...", key="-DFILTERS-")],
        ], expand_x=True)],
        
        [sg.Frame("Step 3: Cleaning Options", [
            [sg.Text("Snaplen (bytes)"), sg.Input("", key="-CLEAN-SNAPLEN-", size=(8,1), tooltip="Truncate packets to save space (leave blank to keep full payload)"),
             sg.Checkbox("Convert to PCAP", key="-CLEAN-CONVERT-", tooltip="Force conversion to pcap format"),
             sg.Checkbox("Gzip Compress", key="-GZIP-", tooltip="Compress final output")],
        ], expand_x=True)],
        
        [sg.HSeparator()],
        
        # Recommended settings display
        [sg.Text("Recommended settings based on duration", key="-RECO-INFO-", size=(100,2), text_color="gray")],
        [sg.Text("", key="-STATUS-", size=(80,1))],
        [sg.ProgressBar(100, orientation="h", size=(40, 20), key="-PB-")],
        [sg.Text("Current Step: ", size=(15,1)), sg.Text("Ready", key="-CURRENT-STEP-", text_color="blue")],
        
        [sg.HSeparator()],
        
        # Action buttons
        [sg.Text("", expand_x=True), 
         sg.Button("Pattern Settings", key="-PATTERNS-"), 
         sg.Button("Advanced Settings", key="-SETTINGS-"), 
         sg.Button("Run Workflow"), 
         sg.Button("Cancel"), 
         sg.Button("Exit")],
         
        # Output area
        [sg.Output(size=(100, 15))],
    ]
    
    window = sg.Window("PCAPpuller", layout, size=(900, 800))
    # Try to set a custom window icon if assets exist
    try:
        here = Path(__file__).resolve()
        assets_dir = None
        # Search upwards for a top-level 'assets' directory (repo layout)
        for p in [here.parent, *here.parents]:
            cand = p / "assets"
            if cand.exists():
                assets_dir = cand
                break
        if assets_dir is None:
            assets_dir = here.parent.parent / "assets"
        for icon_name in ["PCAPpuller.ico", "PCAPpuller.png", "PCAPpuller.icns"]:
            ip = assets_dir / icon_name
            if ip.exists():
                window.set_icon(str(ip))
                break
    except Exception:
        pass
    stop_flag = {"stop": False}
    worker = None
    adv_overrides: dict | None = None
    include_patterns = default_include.copy()
    exclude_patterns = default_exclude.copy()
    
    def _update_reco_label():
        try:
            h = int(values.get("-HOURS-", 0) or 0)
            m = int(values.get("-MINS-", 0) or 0)
            dur = min(h*60 + m, 1440)
            reco = compute_recommended_v2(dur)
            parts = [
                f"workers={reco['workers']}",
                f"batch={reco['batch']}",
                f"slop={reco['slop']}",
                f"precise={'on' if reco['precise_filter'] else 'off'}",
                f"trim-per-batch={'on' if reco['trim_per_batch'] else 'off'}",
            ]
            suffix = " (Advanced overrides active)" if adv_overrides else ""
            window["-RECO-INFO-"].update("Recommended: " + ", ".join(parts) + suffix)
        except Exception:
            pass
    
    # Initialize display
    _update_reco_label()
    
    while True:
        event, values = window.read(timeout=200)
        
        if event in (sg.WINDOW_CLOSED, "Exit"):
            stop_flag["stop"] = True
            break
            
        if event == "Run Workflow" and worker is None:
            # Validation
            if not values.get("-SOURCE-"):
                sg.popup_error("Source directory is required")
                continue
            if not values.get("-START-"):
                sg.popup_error("Start time is required")
                continue
                
            # Check if any steps are selected
            if not any([values.get("-RUN-STEP1-"), values.get("-RUN-STEP2-"), values.get("-RUN-STEP3-")]):
                sg.popup_error("At least one workflow step must be selected")
                continue
            
            # Long window warning
            hours_val = int(values.get("-HOURS-", 0) or 0)
            mins_val = int(values.get("-MINS-", 0) or 0)
            total_minutes = min(hours_val * 60 + mins_val, 1440)
            
            if total_minutes > 60:
                resp = sg.popup_ok_cancel(
                    "Warning: Long window (>60 min) can take a long time.\n"
                    "Consider using Dry Run first to preview file selection.",
                    title="Long window warning"
                )
                if resp != "OK":
                    continue
            
            # Add patterns to values
            values["-INCLUDE-PATTERNS-"] = include_patterns
            values["-EXCLUDE-PATTERNS-"] = exclude_patterns
            
            stop_flag["stop"] = False
            window["-STATUS-"].update("Starting workflow...")
            worker = threading.Thread(target=run_workflow_v2, args=(values, window, stop_flag, adv_overrides), daemon=True)
            worker.start()
            
        elif event == "Cancel":
            stop_flag["stop"] = True
            window["-STATUS-"].update("Cancelling...")
            
        elif event == "-PATTERNS-":
            result = _open_pattern_settings(window, include_patterns, exclude_patterns)
            if result:
                include_patterns, exclude_patterns = result
                print("Pattern settings updated:")
                print(f"  Include: {include_patterns}")
                print(f"  Exclude: {exclude_patterns}")
                
        elif event == "-SETTINGS-":
            duration = min(int(values.get("-HOURS-", 0) or 0) * 60 + int(values.get("-MINS-", 0) or 0), 1440)
            adv_overrides = _open_advanced_settings_v2(window, compute_recommended_v2(duration), adv_overrides)
            _update_reco_label()
            
        elif event in ("-HOURS-", "-MINS-"):
            _update_reco_label()
            
        elif event == "-ALLDAY-":
            try:
                start_str = (values.get("-START-") or "").strip()
                if start_str:
                    base = parse_dt_flexible(start_str)
                    midnight = dt.datetime.combine(base.date(), dt.time.min)
                else:
                    now = dt.datetime.now()
                    midnight = dt.datetime.combine(now.date(), dt.time.min)
                window["-START-"].update(midnight.strftime("%Y-%m-%d %H:%M:%S"))
                window["-HOURS-"].update(24)
                window["-MINS-"].update(0)
            except Exception:
                now = dt.datetime.now()
                midnight = dt.datetime.combine(now.date(), dt.time.min)
                window["-START-"].update(midnight.strftime("%Y-%m-%d %H:%M:%S"))
                window["-HOURS-"].update(24)
                window["-MINS-"].update(0)
                
        elif event == "-DFILTERS-":
            picked = _open_filters_dialog(window)
            if picked:
                prev = values.get("-DFILTER-") or ""
                if prev and not prev.endswith(" "):
                    prev += " "
                window["-DFILTER-"].update(prev + picked)
                
        elif event == "-PROGRESS-":
            phase, cur, tot = values[event]
            friendly = {
                "pattern-filter": "Filtering by pattern",
                "precise": "Precise filtering",
                "merge-batches": "Merging batches",
                "trim-batches": "Trimming batches",
                "trim": "Trimming final",
                "display-filter": "Applying display filter",
                "gzip": "Compressing",
            }
            if str(phase).startswith("scan"):
                window["-STATUS-"].update(f"Scanning... {cur} files visited")
                window["-PB-"].update(cur % 100)
            else:
                label = friendly.get(str(phase), str(phase))
                window["-STATUS-"].update(f"{label}: {cur}/{tot}")
                pct = 0 if tot <= 0 else int((cur / tot) * 100)
                window["-PB-"].update(pct)
            print(f"{phase}: {cur}/{tot}")
            
        elif event == "-STEP-UPDATE-":
            step_msg, step_num = values[event]
            window["-CURRENT-STEP-"].update(step_msg)
            
        elif event == "-WORKFLOW-RESULT-":
            result_path = values[event]
            print(f"Workflow output saved to: {result_path}")
            
        elif event == "-DONE-":
            print(values[event])
            worker = None
            window["-PB-"].update(0)
            window["-STATUS-"].update("")
            window["-CURRENT-STEP-"].update("Ready")
    
    window.close()