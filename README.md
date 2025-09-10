# RenPy Race Condition Reproduction Application

## Overview

This application is designed to reliably reproduce a specific race condition crash in RenPy's video subsystem. The target crash occurs in `media_read_video` at offset `+0x86` with the failure hash `{1155885f-6360-d658-be01-ec1f620514b2}`.

### Technical Target

The application triggers a race condition where:
- `SDL_UnlockMutex(ms->lock)` releases protection in `media_read_video`
- Decoder thread deallocates surface queue entry containing `sqe->pixels`
- Main thread accesses null pointer (`rdi=0000000000000000`) in `SDL_CreateRGBSurfaceFrom`
- Crash occurs at instruction: `movsd xmm0,mmword ptr [rdi+10h]`

## System Requirements

### Target Environment
- **OS**: Windows 10 Build 26100.1 x64
- **RenPy**: Latest version with Python 3.9 embedded runtime
- **Architecture**: 64-bit execution environment
- **Memory**: 4GB+ RAM recommended
- **Storage**: 500MB free space for project and logs

### Required Software
- RenPy SDK (latest version)
- FFmpeg (for video asset generation)
- Python 3.7+ (for deployment scripts)
- Optional: WinDbg (for crash analysis)

## Quick Start

### 1. Project Setup

Clone or extract this project to a directory:
```
RaceConditionRepro/
├── game/
│   ├── script.rpy          # Main game logic
│   ├── options.rpy         # Configuration
│   └── videos/             # Generated video assets
├── generate_videos.py      # Video asset generator
├── deploy_test.py          # Deployment and testing
└── README.md              # This file
```

### 2. Generate Video Assets

Run the video generation script:

```bash
python generate_videos.py
```

This creates 12 short WebM videos (0.5-1.5 seconds each) with embedded audio tracks, designed to stress the surface queue turnover and trigger the race condition.

### 3. Deploy and Test

**Option A: Automated Testing**
```bash
python deploy_test.py
```
Select option 1 for 30-minute automated test or option 2 for 60-minute test.

**Option B: Manual Testing**
```bash
python deploy_test.py
```
Select option 3 for manual setup instructions, then:
```bash
renpy.exe /path/to/RaceConditionRepro
```

## Detailed Deployment Instructions

### Step 1: Environment Verification

Ensure your environment matches the crash specifications:

1. **Windows Version Check**:
   ```cmd
   winver
   ```
   Should show Build 26100.1 or similar Windows 11 build.

2. **Architecture Verification**:
   ```cmd
   echo %PROCESSOR_ARCHITECTURE%
   ```
   Should show `AMD64` for 64-bit.

3. **RenPy Installation**:
   - Download RenPy SDK from renpy.org
   - Extract to a permanent location (e.g., `C:\renpy\`)
   - Add to PATH or note installation directory

### Step 2: Video Asset Generation

The video assets are critical for reproducing the crash:

1. **Install FFmpeg**:
   - Download from ffmpeg.org
   - Add to system PATH
   - Verify: `ffmpeg -version`

2. **Generate Assets**:
   ```bash
   python generate_videos.py
   ```

3. **Verify Generation**:
   ```bash
   ls game/videos/
   ```
   Should show 12 `.webm` files (clip01.webm through clip12.webm).

### Step 3: Project Configuration

The project includes specific configurations targeting the race condition:

- **Skip Mode**: Automatically enabled for rapid execution
- **Zero Delays**: Immediate transitions between videos
- **Memory Pressure**: Garbage collection during video operations
- **Parallel Loading**: Multiple decoder threads stressed simultaneously
- **Surface Queue Stress**: Targets the 3-frame limit boundary

### Step 4: Execution and Monitoring

**Automated Execution**:
```bash
python deploy_test.py
```

The automated tester will:
1. Verify environment compatibility
2. Launch RenPy with the reproduction project
3. Monitor for crashes over the specified duration
4. Log all crash information for analysis
5. Generate detailed results report

**Manual Execution**:
1. Launch RenPy: `renpy.exe RaceConditionRepro`
2. The application auto-starts reproduction sequence
3. Monitor console for cycle counts and crash indicators
4. Check crash logs in project directory

## Crash Detection and Analysis

### Expected Crash Signature

When the race condition occurs, you should see:

1. **Crash Location**: `librenpython!media_read_video+0x86`
2. **Instruction**: `movsd xmm0,mmword ptr [rdi+10h]`
3. **Register State**: `rdi=0000000000000000` (null pointer)
4. **Call Stack**: Shows path through `RPS_read_video` and `renpy_audio_renpysound`
5. **Failure Hash**: `{1155885f-6360-d658-be01-ec1f620514b2}`

### Log Files

The application generates several log files:

- **crash_log.txt**: Detailed crash information and stack traces
- **crash_environment.log**: System environment details
- **test_results_*.json**: Comprehensive test execution results

### WinDbg Analysis (Advanced)

For detailed crash analysis:

1. **Attach Debugger**:
   ```
   windbg -pn renpy.exe
   ```

2. **Set Breakpoint**:
   ```
   bp librenpython!media_read_video+0x86
   ```

3. **Monitor Registers**:
   ```
   r rdi, rsi, rbx
   ```
   Look for `rdi=0` indicating null pointer access.

4. **Stack Analysis**:
   ```
   k
   ```
   Verify call stack matches expected decoder thread pattern.

## Troubleshooting

### Common Issues

**No Crashes Detected**:
- Verify video assets were generated correctly
- Check Windows build version (may need specific build)
- Try increasing test duration to 60+ minutes
- Ensure skip mode is enabled (should auto-activate)

**Video Generation Fails**:
- Install/update FFmpeg
- Check disk space (need ~50MB for assets)
- Verify write permissions in project directory

**RenPy Launch Issues**:
- Verify RenPy installation path
- Check project structure (game/script.rpy must exist)
- Try manual launch from RenPy launcher

**Environment Mismatch**:
- Race condition may be build-specific
- Try different Windows builds/versions
- Verify 64-bit architecture

### Performance Tuning

To increase crash probability:

1. **CPU Load**: Run CPU-intensive tasks in background
2. **Memory Pressure**: Limit available RAM
3. **Thread Scheduling**: Use high-priority process class
4. **Extended Duration**: Run tests for 2+ hours

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

### Amplification Strategies

The application uses several techniques to widen the race window:

- **Zero-delay transitions**: Maximizes `needs_decode = 1` signaling
- **Parallel loading**: Multiple decoder threads compete for resources
- **Memory pressure**: Garbage collection during critical sections
- **Variable frame rates**: Different video timing patterns
- **Surface queue stress**: Repeatedly hits the 3-frame limit

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
- **Asset generation**: 2-5 minutes
- **Crash occurrence**: Typically within 30-60 minutes of testing
- **Analysis time**: 5-10 minutes per crash

## Advanced Usage

### Custom Video Assets

To create specialized test videos:

```python
# Modify generate_videos.py
videos = [
    ("custom01.webm", duration, fps, "pattern_type"),
    # Add more custom configurations
]
```

### Extended Monitoring

For long-term testing:

```python
# Modify deploy_test.py
def run_extended_test(self, hours=8):
    # Extended monitoring logic
    pass
```

### Debug Builds

For additional debugging:

1. Use RenPy debug builds if available
2. Enable additional logging in options.rpy
3. Add custom crash handlers in script.rpy

## Contributing

When modifying this reproduction application:

1. **Preserve timing characteristics**: Don't add delays that might hide the race
2. **Maintain video patterns**: Keep the rapid transition structure
3. **Document changes**: Note any modifications to crash probability
4. **Test thoroughly**: Verify modifications still reproduce the crash

## License and Disclaimer

This application is provided for educational and debugging purposes only. The intentional reproduction of software crashes should only be performed in controlled environments for legitimate security research or bug fixing purposes.

## Support

For issues with this reproduction application:

1. Check the troubleshooting section above
2. Verify environment matches specifications exactly
3. Review log files for specific error details
4. Test with different Windows builds if crashes don't occur

Remember: This race condition may be sensitive to specific system configurations, timing, and software versions.