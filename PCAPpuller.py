#!/usr/bin/env python3
"""
PCAPpuller CLI
Enhanced with three-step workflow: Select -> Process -> Clean
Solves file size inflation issues with smart pattern filtering.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    print("tqdm not installed. Please run: python3 -m pip install tqdm", file=sys.stderr)
    sys.exit(1)

from pcappuller.workflow import ThreeStepWorkflow, WorkflowState
from pcappuller.core import Window, parse_workers
from pcappuller.errors import PCAPPullerError
from pcappuller.logging_setup import setup_logging
from pcappuller.time_parse import parse_start_and_window
from pcappuller.cache import CapinfosCache, default_cache_path


class ExitCodes:
    OK = 0
    ARGS = 2
    TIME = 3
    RANGE = 5
    OSERR = 10
    TOOL = 11


def parse_args():
    ap = argparse.ArgumentParser(
        description="PCAPpuller: Three-step workflow for PCAP processing (Select -> Process -> Clean)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    # Workflow control
    ap.add_argument("--workspace", help="Workspace directory for the workflow (required for all operations)")
    ap.add_argument("--step", choices=["1", "2", "3", "all"], default="all", 
                   help="Which step to run: 1=Select, 2=Process, 3=Clean, all=Run all steps")
    ap.add_argument("--resume", action="store_true", help="Resume from existing workflow state")
    ap.add_argument("--status", action="store_true", help="Show workflow status and exit")
    
    # Step 1: File Selection
    step1_group = ap.add_argument_group("Step 1: File Selection")
    # New preferred flag
    step1_group.add_argument("--source", nargs="+", help="Source directories to search (required for new workflow)")
    # Backward-compat alias (hidden)
    step1_group.add_argument("--root", nargs="+", dest="source", help=argparse.SUPPRESS)
    step1_group.add_argument("--include-pattern", nargs="*", default=["*.pcap", "*.pcapng"], 
                           help="Include files matching these patterns (default: *.pcap, *.pcapng)")
    step1_group.add_argument("--exclude-pattern", nargs="*", default=[], 
                           help="Exclude files matching these patterns (optional)")
    step1_group.add_argument("--slop-min", type=int, default=None, help="Extra minutes around window for mtime prefilter (auto by default)")
    step1_group.add_argument("--selection-mode", choices=["manifest", "symlink"], default="manifest",
                           help="How to materialize Step 1 selections. 'manifest' (default) avoids any data copy; 'symlink' creates symlinks in the workspace.")
    
    # Time window (required for new workflow)
    time_group = ap.add_argument_group("Time Window")
    time_group.add_argument("--start", help="Start datetime: 'YYYY-MM-DD HH:MM:SS' (local time)")
    window_group = time_group.add_mutually_exclusive_group()
    window_group.add_argument("--minutes", type=int, help="Duration in minutes (1-1440)")
    window_group.add_argument("--end", help="End datetime (must be same calendar day as start)")
    
    # Step 2: Processing parameters  
    step2_group = ap.add_argument_group("Step 2: Processing")
    step2_group.add_argument("--batch-size", type=int, default=None, help="Files per merge batch (auto by default)")
    step2_group.add_argument("--out-format", choices=["pcap", "pcapng"], default="pcapng", help="Output format")
    step2_group.add_argument("--display-filter", help="Wireshark display filter")
    step2_group.add_argument("--trim-per-batch", action="store_true", help="Trim each batch before final merge")
    step2_group.add_argument("--no-trim-per-batch", action="store_false", dest="trim_per_batch", 
                           help="Only trim final merged file")
    step2_group.add_argument("--out", help="Explicit output file path for Step 2 (e.g., /path/to/output.pcapng). If omitted, a timestamped file is written under the workspace.")
    step2_group.add_argument("--no-precise-filter", action="store_true", help="Disable precise filtering in Step 2 (advanced)")
    
    # Step 3: Cleaning parameters
    step3_group = ap.add_argument_group("Step 3: Cleaning")
    step3_group.add_argument("--snaplen", type=int, help="Truncate packets to N bytes")
    step3_group.add_argument("--convert-to-pcap", action="store_true", help="Convert final output to pcap format")
    step3_group.add_argument("--gzip", action="store_true", help="Compress final output")
    
    # General options
    ap.add_argument("--workers", default="auto", help="Parallel workers: 'auto' or integer")
    ap.add_argument("--tmpdir", help="Temporary files directory")
    ap.add_argument("--cache", default="auto", help="Capinfos cache database path or 'auto'")
    ap.add_argument("--no-cache", action="store_true", help="Disable capinfos cache")
    ap.add_argument("--clear-cache", action="store_true", help="Clear capinfos cache before running")
    ap.add_argument("--dry-run", action="store_true", help="Show what would be selected/processed without doing it")
    ap.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = ap.parse_args()
    
    # Validation
    if not args.workspace:
        ap.error("--workspace is required")
    
    if args.status:
        return args
    
    if not args.resume:
        # New workflow requires certain parameters
        if not args.source:
            ap.error("--source is required for new workflow (use --resume to continue existing)")
        if not args.start:
            ap.error("--start is required for new workflow")
        if not args.minutes and not args.end:
            ap.error("Either --minutes or --end is required for new workflow")
    
    if args.minutes is not None and not (1 <= args.minutes <= 1440):
        ap.error("--minutes must be between 1 and 1440")
    
    return args


def setup_progress_callback(desc: str) -> tuple:
    """Setup tqdm progress bar with callback function."""
    pbar = None
    
    def progress_callback(phase: str, current: int, total: int):
        nonlocal pbar
        if pbar is None or pbar.total != total:
            if pbar:
                pbar.close()
            pbar = tqdm(total=total, desc=f"{desc} ({phase})", unit="items")
        pbar.n = current
        pbar.refresh()
        if current >= total:
            pbar.close()
            pbar = None
    
    return progress_callback, lambda: pbar.close() if pbar else None


def run_step1(workflow: ThreeStepWorkflow, state: WorkflowState, args) -> WorkflowState:
    """Execute Step 1: File Selection."""
    print("🔍 Step 1: Selecting PCAP files...")
    
    # Setup cache (not strictly needed for Step 1 now, but keep for future-proofing)
    cache = None
    if not args.no_cache:
        cache_path = default_cache_path() if args.cache == "auto" else Path(args.cache)
        cache = CapinfosCache(cache_path)
        if args.clear_cache:
            cache.clear()
    
    # Setup progress tracking
    progress_cb, cleanup_pb = setup_progress_callback("Step 1: File Selection")
    
    try:
        # Auto defaults: compute slop based on requested duration when not provided
        try:
            start, end = parse_start_and_window(args.start, args.minutes, args.end)
            duration_minutes = int((end - start).total_seconds() // 60)
        except Exception:
            duration_minutes = 60
        if args.slop_min is None:
            if duration_minutes <= 15:
                slop_min = 120
            elif duration_minutes <= 60:
                slop_min = 60
            elif duration_minutes <= 240:
                slop_min = 30
            elif duration_minutes <= 720:
                slop_min = 20
            else:
                slop_min = 15
        else:
            slop_min = args.slop_min
        
        workers = parse_workers(args.workers, 1000)  # Estimate for auto calculation
        
        state = workflow.step1_select_and_move(
            state=state,
            slop_min=slop_min,
            precise_filter=False,  # moved to Step 2 by default
            workers=workers,
            cache=cache,
            dry_run=args.dry_run,
            progress_callback=progress_cb,
            selection_mode=args.selection_mode
        )
        
        if not args.dry_run:
            files = state.selected_files or []
            print(f"✅ Step 1 complete: {len(files)} files selected")
            total_size_mb = sum(int(f.stat().st_size) for f in files) / (1024*1024)
            print(f"   Total size: {total_size_mb:.1f} MB")
        
        return state
        
    finally:
        cleanup_pb()
        if cache:
            cache.close()


def run_step2(workflow: ThreeStepWorkflow, state: WorkflowState, args) -> WorkflowState:
    """Execute Step 2: Processing (merge, trim, filter)."""
    print("⚙️  Step 2: Processing files (merge, trim, filter)...")
    
    progress_cb, cleanup_pb = setup_progress_callback("Step 2: Processing")
    
    try:
        trim_per_batch = None
        if args.trim_per_batch is not None:
            trim_per_batch = args.trim_per_batch
        
        # Auto defaults for Step 2 if not provided
        # Determine duration from state
        duration_minutes = int((state.window.end - state.window.start).total_seconds() // 60)
        if args.batch_size is None:
            if duration_minutes <= 15:
                batch_size = 500
            elif duration_minutes <= 60:
                batch_size = 400
            elif duration_minutes <= 240:
                batch_size = 300
            elif duration_minutes <= 720:
                batch_size = 200
            else:
                batch_size = 150
        else:
            batch_size = int(args.batch_size)
        if trim_per_batch is None:
            trim_per_batch = duration_minutes > 60
        
        # Setup cache for Step 2 precise filtering (default on)
        cache = None
        if not args.no_cache:
            cache_path = default_cache_path() if args.cache == "auto" else Path(args.cache)
            cache = CapinfosCache(cache_path)
            if args.clear_cache:
                cache.clear()
        
        workers = parse_workers(args.workers, total_files=1000)
        
        state = workflow.step2_process(
            state=state,
            batch_size=batch_size,
            out_format=args.out_format,
            display_filter=args.display_filter,
            trim_per_batch=trim_per_batch,
            progress_callback=progress_cb,
            verbose=args.verbose,
            out_path=Path(args.out) if args.out else None,
            tmpdir_parent=Path(args.tmpdir) if args.tmpdir else None,
            precise_filter=not bool(getattr(args, "no_precise_filter", False)),
            workers=workers,
            cache=cache,
        )
        
        print("✅ Step 2 complete: Processed file saved")
        if state.processed_file and state.processed_file.exists():
            size_mb = state.processed_file.stat().st_size / (1024*1024)
            print(f"   Output: {state.processed_file}")
            print(f"   Size: {size_mb:.1f} MB")
        
        return state
        
    finally:
        cleanup_pb()


def run_step3(workflow: ThreeStepWorkflow, state: WorkflowState, args) -> WorkflowState:
    """Execute Step 3: Cleaning (headers, metadata removal)."""
    # Collect cleaning options
    clean_options = {}
    if args.snaplen:
        clean_options['snaplen'] = args.snaplen
    if args.convert_to_pcap:
        clean_options['convert_to_pcap'] = True
    if args.gzip:
        clean_options['gzip'] = True
    
    # If user did not specify options, apply safe defaults that do not truncate payloads
    if not clean_options:
        clean_options = {"convert_to_pcap": True, "gzip": True}
    
    print("🧹 Step 3: Cleaning output (removing headers/metadata)...")
    
    progress_cb, cleanup_pb = setup_progress_callback("Step 3: Cleaning")
    
    try:
        state = workflow.step3_clean(
            state=state,
            options=clean_options,
            progress_callback=progress_cb,
            verbose=args.verbose
        )
        
        print("✅ Step 3 complete: Cleaned file saved")
        if state.cleaned_file and state.cleaned_file.exists():
            size_mb = state.cleaned_file.stat().st_size / (1024*1024)
            print(f"   Output: {state.cleaned_file}")
            print(f"   Size: {size_mb:.1f} MB")
        
        return state
        
    finally:
        cleanup_pb()


def show_status(workflow: ThreeStepWorkflow):
    """Show workflow status."""
    try:
        state = workflow.load_workflow()
        summary = workflow.get_summary(state)
        
        print("📊 Workflow Status")
        print(f"   Workspace: {summary['workspace_dir']}")
        print(f"   Time window: {summary['window']}")
        print()
        
        steps = summary['steps_complete']
        print(f"   Step 1 (Select): {'✅ Complete' if steps['step1_select'] else '⏳ Pending'}")
        if 'selected_files' in summary:
            sf = summary['selected_files']
            print(f"            Files: {sf['count']}, Size: {sf['total_size_mb']} MB")
        
        print(f"   Step 2 (Process): {'✅ Complete' if steps['step2_process'] else '⏳ Pending'}")
        if 'processed_file' in summary:
            pf = summary['processed_file']
            print(f"            File: {Path(pf['path']).name}, Size: {pf['size_mb']} MB")
        
        print(f"   Step 3 (Clean): {'✅ Complete' if steps['step3_clean'] else '⏳ Pending'}")
        if 'cleaned_file' in summary:
            cf = summary['cleaned_file']
            print(f"            File: {Path(cf['path']).name}, Size: {cf['size_mb']} MB")
        
    except PCAPPullerError as e:
        print(f"❌ No workflow found: {e}")


def main():
    args = parse_args()
    setup_logging(args.verbose)
    
    workspace = Path(args.workspace)
    workflow = ThreeStepWorkflow(workspace)
    
    # Status check
    if args.status:
        show_status(workflow)
        sys.exit(ExitCodes.OK)
    
    try:
        # Load or create workflow state
        if args.resume:
            print("📂 Resuming existing workflow...")
            state = workflow.load_workflow()
        else:
            print("🚀 Starting new workflow...")
            # Parse time window
            start, end = parse_start_and_window(args.start, args.minutes, args.end)
            window = Window(start=start, end=end)
            
            # Initialize new workflow
            root_dirs = [Path(r) for r in args.source]
            state = workflow.initialize_workflow(
                root_dirs=root_dirs,
                window=window,
                include_patterns=args.include_pattern,
                exclude_patterns=args.exclude_pattern
            )
        
        # Run requested steps
        if args.step in ["1", "all"]:
            if not state.step1_complete:
                state = run_step1(workflow, state, args)
                if args.dry_run:
                    sys.exit(ExitCodes.OK)
            else:
                print("✅ Step 1 already complete")
        
        if args.step in ["2", "all"]:
            if not state.step2_complete:
                state = run_step2(workflow, state, args)
            else:
                print("✅ Step 2 already complete")
        
        if args.step in ["3", "all"]:
            if not state.step3_complete:
                state = run_step3(workflow, state, args)
            else:
                print("✅ Step 3 already complete")
        
        # Final summary
        if args.step == "all" or (args.step == "3" and state.step3_complete):
            final_file = state.cleaned_file or state.processed_file
            if final_file and final_file.exists():
                size_mb = final_file.stat().st_size / (1024*1024)
                print()
                print("🎉 Workflow complete!")
                print(f"   Final output: {final_file}")
                print(f"   Size: {size_mb:.1f} MB")
        
        sys.exit(ExitCodes.OK)
        
    except PCAPPullerError as e:
        logging.error(str(e))
        sys.exit(ExitCodes.OSERR if "OS error" in str(e) else ExitCodes.TOOL)
    except Exception:
        logging.exception("Unexpected error")
        sys.exit(1)


if __name__ == "__main__":
    main()