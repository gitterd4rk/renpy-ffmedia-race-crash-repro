# RenPy media_read_video Race Condition Analysis - Developer Brief

## Problem Summary

The `media_read_video` function in RenPy's `ffmedia.c` contains race conditions that result in use-after-free crashes during skip mode acceleration. Two distinct crash locations have been observed at offsets +0xd and +0x86.

## Technical Evidence

### Observed Crashes

**Crash 1: Offset +0xd**
```
Instruction: cmp dword ptr [rcx+50h],0FFFFFFFFh
Register State: rcx = 0x0 (null pointer)
Location: Early function entry, checking ms->video_stream
```

**Crash 2: Offset +0x86**  
```
Instruction: movsd xmm0,mmword ptr [rdi+10h]
Register State: rdi = 0x0 (null pointer)
Location: Later in function, accessing video data structure
```

### Source Code Analysis

**Function Entry - No Parameter Validation**
```c
SDL_Surface *media_read_video(MediaState *ms) {
    if (ms->video_stream == -1) {  // ← Crash 1: No null check on ms
```

**Critical Race Window**
```c
SDL_UnlockMutex(ms->lock);  // ← Protection ends here

if (sqe) {
    rv = SDL_CreateRGBSurfaceFrom(
        sqe->pixels,  // ← Crash 2: sqe->pixels can be freed after unlock
        sqe->w, sqe->h, /* ... */
    );
    rv->flags &= ~SDL_PREALLOC;
    av_free(sqe);
}
```

## Root Cause Analysis

### Race Condition 1: MediaState Use-After-Free

**Vulnerable Code Path:**
1. Main thread calls `media_read_video(ms)`
2. Decoder thread calls `deallocate(ms)` → `av_free(ms)`
3. Main thread accesses `ms->video_stream` → crash at offset +0xd

### Race Condition 2: Surface Queue Use-After-Free

**Vulnerable Code Path:**
1. Main thread dequeues `sqe` while holding mutex
2. Main thread releases mutex
3. Decoder thread calls `deallocate()` → `dequeue_surface()` → `SDL_free(sqe->pixels)`
4. Main thread accesses `sqe->pixels` → crash at offset +0x86

### SDL_PREALLOC Flag Behavior

From SDL source code analysis (`SDL_surface.c`):
```c
void SDL_FreeSurface(SDL_Surface *surface) {
    if (surface->flags & SDL_PREALLOC) {
        /* Don't free */  // SDL won't free pixel memory
    } else {
        SDL_free(surface->pixels);  // SDL will free pixel memory
    }
}
```

**RenPy's Pattern:**
```c
rv = SDL_CreateRGBSurfaceFrom(sqe->pixels, ...);  // Sets SDL_PREALLOC
rv->flags &= ~SDL_PREALLOC;  // Clears flag → SDL will free pixels
```

This creates a double-free risk: both RenPy and SDL may attempt to free `sqe->pixels`.

## Concurrent Thread Analysis

**Decoder Thread (`decode_thread` function):**
```c
while (!ms->quit) {
    // ... decoding work ...
}
// Exit loop and call cleanup:
deallocate(ms);
```

**Deallocation Trigger (`media_close` function):**
```c
SDL_LockMutex(ms->lock);
ms->quit = 1;  // Signals decoder thread to exit
SDL_CondBroadcast(ms->cond);
SDL_UnlockMutex(ms->lock);
```

**Race Condition Sequence:**
1. Main thread: `media_read_video` dequeues `sqe`, releases mutex
2. Another thread: calls `media_close(ms)` → sets `ms->quit = 1`  
3. Decoder thread: exits loop, calls `deallocate(ms)` → frees `sqe->pixels`
4. Main thread: accesses `sqe->pixels` → crash

## Recommended Fix

```c
SDL_Surface *media_read_video(MediaState *ms) {
    SDL_Surface *rv = NULL;
    SurfaceQueueEntry *sqe = NULL;
    void *pixel_copy = NULL;
    
    // Fix 1: Add parameter validation
    if (!ms) {
        return NULL;
    }
    
    if (ms->video_stream == -1) {
        return NULL;
    }
    
    double offset_time = current_time - ms->time_offset;
    
    SDL_LockMutex(ms->lock);
    
    // ... existing dequeue logic unchanged ...
    
    if (sqe) {
        // Fix 2: Copy pixel data while mutex protects from deallocation
        size_t pixel_size = sqe->pitch * sqe->h;
        pixel_copy = SDL_malloc(pixel_size);
        if (pixel_copy) {
            memcpy(pixel_copy, sqe->pixels, pixel_size);
        }
        
        ms->needs_decode = 1;
        ms->video_read_time = offset_time;
        SDL_CondBroadcast(ms->cond);
    }
    
    SDL_UnlockMutex(ms->lock);
    
    if (sqe && pixel_copy) {
        rv = SDL_CreateRGBSurfaceFrom(
            pixel_copy,  // Safe copy instead of potentially freed memory
            sqe->w, sqe->h,
            sqe->format->BitsPerPixel,
            sqe->pitch,
            sqe->format->Rmask,
            sqe->format->Gmask,
            sqe->format->Bmask,
            sqe->format->Amask
        );
        
        if (rv) {
            // Let SDL manage the copied memory
            rv->flags &= ~SDL_PREALLOC;
        } else {
            SDL_free(pixel_copy);
        }
        av_free(sqe);
    }
    
    return rv;
}
```

## Fix Rationale

1. **Eliminates Race Windows**: Pixel data copied while mutex prevents concurrent deallocation
2. **Prevents Use-After-Free**: No shared memory access after mutex release  
3. **Resolves Double-Free**: SDL manages its own copy of pixel data
4. **Minimal Performance Impact**: Only copies pixels for actually displayed frames
5. **Preserves Existing Logic**: All other function behavior unchanged

## Supporting Evidence

- **ffmedia.c source code**: Shows vulnerable mutex unlock pattern
- **SDL_surface.c source code**: Confirms SDL_PREALLOC flag behavior
- **WinDbg crash analysis**: Demonstrates null pointer dereferences at documented locations
- **Call stack traces**: Shows crashes during skip mode acceleration with display rendering

## Impact Assessment

- **Severity**: Critical application crashes during normal operation  
- **Scope**: Any RenPy application using video content with skip functionality
- **Frequency**: Intermittent but reproducible under skip mode stress conditions