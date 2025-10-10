from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any
import datetime as dt

from .core import Window, candidate_files, precise_filter_parallel, build_output
from .tools import run_editcap_snaplen, try_convert_to_pcap
from .errors import PCAPPullerError
from .cache import CapinfosCache


@dataclass
class WorkflowState:
    """Tracks the state of a three-step workflow."""
    workspace_dir: Path
    root_dirs: List[Path]
    window: Window
    include_patterns: List[str]
    exclude_patterns: List[str]
    selected_files: List[Path] = None
    processed_file: Path = None
    cleaned_file: Path = None
    step1_complete: bool = False
    step2_complete: bool = False
    step3_complete: bool = False
    
    def save(self, state_file: Path) -> None:
        """Save workflow state to JSON file."""
        state_dict = asdict(self)
        # Convert Path objects to strings for JSON serialization
        state_dict['workspace_dir'] = str(self.workspace_dir)
        state_dict['root_dirs'] = [str(p) for p in self.root_dirs]
        state_dict['window'] = {
            'start': self.window.start.isoformat(),
            'end': self.window.end.isoformat()
        }
        state_dict['selected_files'] = [str(p) for p in self.selected_files] if self.selected_files else None
        state_dict['processed_file'] = str(self.processed_file) if self.processed_file else None
        state_dict['cleaned_file'] = str(self.cleaned_file) if self.cleaned_file else None
        
        with open(state_file, 'w') as f:
            json.dump(state_dict, f, indent=2)
    
    @classmethod
    def load(cls, state_file: Path) -> 'WorkflowState':
        """Load workflow state from JSON file."""
        with open(state_file, 'r') as f:
            state_dict = json.load(f)
        
        # Convert strings back to Path objects
        state_dict['workspace_dir'] = Path(state_dict['workspace_dir'])
        state_dict['root_dirs'] = [Path(p) for p in state_dict['root_dirs']]
        state_dict['window'] = Window(
            start=dt.datetime.fromisoformat(state_dict['window']['start']),
            end=dt.datetime.fromisoformat(state_dict['window']['end'])
        )
        state_dict['selected_files'] = [Path(p) for p in state_dict['selected_files']] if state_dict['selected_files'] else None
        state_dict['processed_file'] = Path(state_dict['processed_file']) if state_dict['processed_file'] else None
        state_dict['cleaned_file'] = Path(state_dict['cleaned_file']) if state_dict['cleaned_file'] else None
        
        return cls(**state_dict)


class ThreeStepWorkflow:
    """Manages the three-step PCAPpuller workflow: Select -> Process -> Clean."""
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.workspace_dir / "workflow_state.json"
        self.selected_dir = self.workspace_dir / "selected"
        self.processed_dir = self.workspace_dir / "processed"
        self.cleaned_dir = self.workspace_dir / "cleaned"
        
    def initialize_workflow(
        self,
        root_dirs: List[Path],
        window: Window,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None
    ) -> WorkflowState:
        """Initialize a new workflow state."""
        state = WorkflowState(
            workspace_dir=self.workspace_dir,
            root_dirs=root_dirs,
            window=window,
            include_patterns=include_patterns or [],
            exclude_patterns=exclude_patterns or []
        )
        state.save(self.state_file)
        return state
    
    def load_workflow(self) -> WorkflowState:
        """Load existing workflow state."""
        if not self.state_file.exists():
            raise PCAPPullerError(f"No workflow state found at {self.state_file}")
        return WorkflowState.load(self.state_file)
    
    def step1_select_and_move(
        self,
        state: WorkflowState,
        slop_min: int = 120,
        precise_filter: bool = True,
        workers: int = None,
        cache: Optional[CapinfosCache] = None,
        dry_run: bool = False,
        progress_callback: Optional[callable] = None
    ) -> WorkflowState:
        """
        Step 1: Select and move PCAP files based on time window and patterns.
        
        This step:
        1. Scans root directories for candidate files
        2. Applies include/exclude patterns
        3. Optionally applies precise time filtering
        4. Copies selected files to workspace
        """
        if state.step1_complete and not dry_run:
            logging.info("Step 1 already complete, skipping...")
            return state
            
        # Create selected directory
        if not dry_run:
            self.selected_dir.mkdir(parents=True, exist_ok=True)
        
        # Find candidates using existing logic
        all_candidates = candidate_files(state.root_dirs, state.window, slop_min, progress_callback)
        
        # Apply include/exclude patterns
        filtered_candidates = self._apply_patterns(all_candidates, state.include_patterns, state.exclude_patterns)
        
        if progress_callback:
            progress_callback("pattern-filter", len(filtered_candidates), len(all_candidates))
        
        # Apply precise filtering if requested
        if precise_filter and filtered_candidates:
            if workers is None:
                from .core import parse_workers
                workers = parse_workers("auto", len(filtered_candidates))
            
            final_candidates = precise_filter_parallel(
                filtered_candidates, state.window, workers, 0, progress_callback, cache
            )
        else:
            final_candidates = filtered_candidates
        
        if dry_run:
            logging.info(f"Step 1 dry run results:")
            logging.info(f"  Total files found: {len(all_candidates)}")
            logging.info(f"  After pattern filtering: {len(filtered_candidates)}")
            logging.info(f"  After precise filtering: {len(final_candidates)}")
            return state
        
        # Copy files to workspace
        copied_files = []
        for i, src_file in enumerate(final_candidates):
            dst_file = self.selected_dir / src_file.name
            # Handle name conflicts by appending a counter
            counter = 1
            while dst_file.exists():
                stem = src_file.stem
                suffix = src_file.suffix
                dst_file = self.selected_dir / f"{stem}_{counter:03d}{suffix}"
                counter += 1
            
            shutil.copy2(src_file, dst_file)
            copied_files.append(dst_file)
            
            if progress_callback:
                progress_callback("copy-files", i + 1, len(final_candidates))
        
        # Update state
        state.selected_files = copied_files
        state.step1_complete = True
        state.save(self.state_file)
        
        logging.info(f"Step 1 complete: Selected and copied {len(copied_files)} files to {self.selected_dir}")
        return state
    
    def step2_process(
        self,
        state: WorkflowState,
        batch_size: int = 500,
        out_format: str = "pcapng",
        display_filter: Optional[str] = None,
        trim_per_batch: bool = None,
        progress_callback: Optional[callable] = None,
        verbose: bool = False
    ) -> WorkflowState:
        """
        Step 2: Process selected files using existing merge/trim logic.
        
        This step:
        1. Uses the files from Step 1's workspace
        2. Applies the existing build_output logic
        3. Saves result to processed directory
        """
        if state.step2_complete:
            logging.info("Step 2 already complete, skipping...")
            return state
        
        if not state.step1_complete:
            raise PCAPPullerError("Step 1 must be completed before Step 2")
        
        if not state.selected_files:
            raise PCAPPullerError("No files selected in Step 1")
        
        # Create processed directory
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine output filename
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.processed_dir / f"merged_{timestamp}.{out_format}"
        
        # Auto-determine trim_per_batch if not specified
        if trim_per_batch is None:
            duration_minutes = int((state.window.end - state.window.start).total_seconds() // 60)
            trim_per_batch = duration_minutes > 60
        
        # Ensure tmp directory exists
        tmp_dir = self.workspace_dir / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        
        # Use existing build_output logic
        result_file = build_output(
            candidates=state.selected_files,
            window=state.window,
            out_path=output_file,
            tmpdir_parent=tmp_dir,
            batch_size=batch_size,
            out_format=out_format,
            display_filter=display_filter,
            gzip_out=False,  # Don't gzip in step 2, save for step 3 if needed
            progress=progress_callback,
            verbose=verbose,
            trim_per_batch=trim_per_batch
        )
        
        # Update state
        state.processed_file = result_file
        state.step2_complete = True
        state.save(self.state_file)
        
        logging.info(f"Step 2 complete: Processed file saved to {result_file}")
        return state
    
    def step3_clean(
        self,
        state: WorkflowState,
        options: Dict[str, Any],
        progress_callback: Optional[callable] = None,
        verbose: bool = False
    ) -> WorkflowState:
        """
        Step 3: Clean the processed file by removing headers/metadata.
        
        Available cleaning options:
        - snaplen: Truncate packets to specified length
        - remove_ethernet: Convert to raw IP (remove Ethernet headers)
        - convert_to_pcap: Force conversion to pcap format
        - anonymize: Basic IP anonymization (if available)
        - gzip: Compress final output
        """
        if state.step3_complete:
            logging.info("Step 3 already complete, skipping...")
            return state
        
        if not state.step2_complete:
            raise PCAPPullerError("Step 2 must be completed before Step 3")
        
        if not state.processed_file or not state.processed_file.exists():
            raise PCAPPullerError("No processed file found from Step 2")
        
        # Create cleaned directory
        self.cleaned_dir.mkdir(parents=True, exist_ok=True)
        
        current_file = state.processed_file
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Apply cleaning operations in sequence
        step_count = 0
        total_steps = sum(1 for key in ['snaplen', 'convert_to_pcap', 'gzip'] if key in options and options[key])
        
        # Snaplen truncation
        if options.get('snaplen'):
            step_count += 1
            snaplen_file = self.cleaned_dir / f"snaplen_{timestamp}.{current_file.suffix[1:]}"
            run_editcap_snaplen(current_file, snaplen_file, options['snaplen'], verbose=verbose)
            current_file = snaplen_file
            if progress_callback:
                progress_callback("clean-snaplen", step_count, total_steps)
            logging.info(f"Applied snaplen {options['snaplen']} bytes")
        
        # Convert to pcap format
        if options.get('convert_to_pcap'):
            step_count += 1
            pcap_file = self.cleaned_dir / f"converted_{timestamp}.pcap"
            success = try_convert_to_pcap(current_file, pcap_file, verbose=verbose)
            if success:
                current_file = pcap_file
                logging.info("Converted to pcap format")
            else:
                logging.warning("Failed to convert to pcap format, keeping original")
            if progress_callback:
                progress_callback("clean-convert", step_count, total_steps)
        
        # Gzip compression
        if options.get('gzip'):
            step_count += 1
            from .tools import gzip_file
            gz_file = current_file.with_suffix(current_file.suffix + '.gz')
            gzip_file(current_file, gz_file)
            current_file = gz_file
            if progress_callback:
                progress_callback("clean-gzip", step_count, total_steps)
            logging.info("Applied gzip compression")
        
        # Update state
        state.cleaned_file = current_file
        state.step3_complete = True
        state.save(self.state_file)
        
        logging.info(f"Step 3 complete: Cleaned file saved to {current_file}")
        return state
    
    def _apply_patterns(self, files: List[Path], include_patterns: List[str], exclude_patterns: List[str]) -> List[Path]:
        """Apply include/exclude patterns to filter files."""
        import fnmatch
        
        result = files
        
        # Apply include patterns (if any)
        if include_patterns:
            included = []
            for file in result:
                if any(fnmatch.fnmatch(file.name, pattern) for pattern in include_patterns):
                    included.append(file)
            result = included
        
        # Apply exclude patterns (if any)
        if exclude_patterns:
            excluded = []
            for file in result:
                if not any(fnmatch.fnmatch(file.name, pattern) for pattern in exclude_patterns):
                    excluded.append(file)
            result = excluded
        
        return result
    
    def get_summary(self, state: WorkflowState) -> Dict[str, Any]:
        """Get a summary of the workflow state."""
        summary = {
            'workspace_dir': str(state.workspace_dir),
            'window': f"{state.window.start} to {state.window.end}",
            'steps_complete': {
                'step1_select': state.step1_complete,
                'step2_process': state.step2_complete, 
                'step3_clean': state.step3_complete
            }
        }
        
        if state.selected_files:
            total_size = sum(f.stat().st_size for f in state.selected_files if f.exists())
            summary['selected_files'] = {
                'count': len(state.selected_files),
                'total_size_mb': round(total_size / (1024*1024), 2)
            }
        
        if state.processed_file and state.processed_file.exists():
            size = state.processed_file.stat().st_size
            summary['processed_file'] = {
                'path': str(state.processed_file),
                'size_mb': round(size / (1024*1024), 2)
            }
            
        if state.cleaned_file and state.cleaned_file.exists():
            size = state.cleaned_file.stat().st_size
            summary['cleaned_file'] = {
                'path': str(state.cleaned_file),
                'size_mb': round(size / (1024*1024), 2)
            }
        
        return summary