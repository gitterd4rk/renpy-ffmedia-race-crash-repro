# RenPy Race Condition Repro App

## Overview

This application is designed to reliably reproduce a specific race condition crash in RenPy's video subsystem. The target crash occurs in `media_read_video` at offset `+0x86`.

### Technical Target

The application triggers a race condition where:
- `SDL_UnlockMutex(ms->lock)` releases protection in `media_read_video`
- Decoder thread deallocates surface queue entry containing `sqe->pixels`
- Main thread accesses null pointer (`rdi=0000000000000000`) in `SDL_CreateRGBSurfaceFrom`
- Crash occurs at instruction: `movsd xmm0,mmword ptr [rdi+10h]`

## System Requirements

### Target Environment
- **OS**: Windows
- **RenPy**: tested on 8.3.4 and 8.4.1

### Required Software
- RenPy SDK (latest version)

## Quick Start

### 1. Project Setup

Clone or extract this project to a directory:
```
RaceConditionRepro/
├── game/
│   ├── script.rpy          # Main game logic
│   ├── options.rpy         # Configuration
│   └── videos/             # Generated video assets
└── README.md              # This file
```

### 2. Test

```bash
renpy.exe /path/to/RaceConditionRepro
```

**Manual Execution**:
1. Launch RenPy: `renpy.exe RaceConditionRepro`
2. The application auto-starts reproduction sequence
4. Check Windows Event Viewer > Windows Logs > Application

### Expected Crash Signature

When the race condition occurs, you should see (in WinDbg):

1. **Crash Location**: `librenpython!media_read_video+0x86`
2. **Instruction**: `movsd xmm0,mmword ptr [rdi+10h]`
3. **Register State**: `rdi=0000000000000000` (null pointer)
4. **Call Stack**: Shows path through `RPS_read_video` and `renpy_audio_renpysound` to `media_read_video`

## Technical Details

### Race Condition Mechanics

The crash occurs due to a timing window in the video decoder:

1. Main thread calls `media_read_video`
2. Function acquires mutex lock on surface queue
3. Surface queue entry is prepared with pixel data
4. `SDL_UnlockMutex(ms->lock)` releases protection
5. **RACE WINDOW**: Decoder thread can now modify surface queue
6. Decoder thread deallocates the surface queue entry
7. Main thread attempts to access `sqe->pixels` (now null)
8. `SDL_CreateRGBSurfaceFrom` dereferences null pointer
9. Crash at `movsd xmm0,mmword ptr [rdi+10h]` instruction

## Results and Validation

### Success Criteria

A successful reproduction must demonstrate:

1. **Exact crash location**: `media_read_video+0x86`
2. **Correct instruction**: `movsd xmm0,mmword ptr [rdi+10h]`
3. **Null pointer state**: `rdi=0000000000000000`
4. **Threading context**: Race between main and decoder threads
5. **Call stack match**: Path through audio subsystem initialization

### Expected Timeline

- **Setup time**: 5-10 minutes
- **Crash occurrence**: Typically within 3-20 minutes of testing
