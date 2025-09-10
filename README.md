# RenPy Race Condition Repro App

## Overview

This application is designed to reliably (eventually) reproduce a specific race condition crash in RenPy's video subsystem. The target crash occurs in `media_read_video` at offsets `+0xd` and `+0x86`.

### Technical Target

The application triggers race conditions in RenPy's video subsystem where:
- `media_close()` sets quit flag while `media_read_video()` is executing
- Decoder thread calls `deallocate()` and frees MediaState or surface data
- Main thread accesses freed memory, causing null pointer dereferences
- Crashes occur at two locations:
  - **+0xd**: `cmp dword ptr [rcx+50h],0FFFFFFFFh` (MediaState freed)
  - **+0x86**: `movsd xmm0,mmword ptr [rdi+10h]` (surface data freed)

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

When the race condition occurs, you may see one of two crash patterns in WinDbg:

**Crash Type 1: MediaState Use-After-Free**
1. **Crash Location**: `librenpython!media_read_video+0xd`
2. **Instruction**: `cmp dword ptr [rcx+50h],0FFFFFFFFh`
3. **Register State**: `rcx=0000000000000000` (null MediaState pointer)
4. **Cause**: MediaState freed while function executing

**Crash Type 2: Surface Queue Use-After-Free**
1. **Crash Location**: `librenpython!media_read_video+0x86`
2. **Instruction**: `movsd xmm0,mmword ptr [rdi+10h]`
3. **Register State**: `rdi=0000000000000000` (null surface data pointer)
4. **Call Stack**: Shows path through `RPS_read_video` and `renpy_audio_renpysound` to `media_read_video`

**Both crashes indicate the same underlying race condition** but manifest at different points in the function depending on timing. Type 1 occurs earlier (function entry) while Type 2 occurs later (surface creation).

## Technical Details

### Race Condition Mechanics

Two distinct race conditions have been identified:

**Race 1: MediaState Use-After-Free (+0xd)**
1. Thread A calls `media_read_video(ms)`
2. Thread B calls `media_close(ms)` → sets `ms->quit = 1`
3. Decoder thread exits, calls `deallocate(ms)` → frees MediaState
4. Thread A accesses `ms->video_stream` → crash at +0xd

**Race 2: Surface Queue Use-After-Free (+0x86)**
1. Main thread dequeues surface entry, releases mutex
2. `media_close()` triggers decoder thread shutdown
3. `deallocate()` frees `sqe->pixels`
4. Main thread accesses freed `sqe->pixels` → crash at +0x86

## Results and Validation

### Success Criteria

A successful reproduction demonstrates either:

**Crash Type 1 (+0xd)**:
- Location: `media_read_video+0xd`
- Instruction: `cmp dword ptr [rcx+50h],0FFFFFFFFh`
- Register: `rcx=0000000000000000`

**Crash Type 2 (+0x86)**:
- Location: `media_read_video+0x86`  
- Instruction: `movsd xmm0,mmword ptr [rdi+10h]`
- Register: `rdi=0000000000000000`

### Expected Timeline

- **Setup time**: 5-10 minutes
- **Crash occurrence**: Typically within 3 minutes to an hour of testing
