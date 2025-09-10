# Minimal options.rpy for race condition reproduction

define config.name = "Race Condition Repro"
define config.version = "1.0"

# Enable skip mode for rapid execution
define config.allow_skipping = True
define config.fast_skipping = True
define config.skip_delay = 0
define config.skip_indicator = True

# Handle window close button
define config.quit_action = Quit(confirm=False)

# Enable developer mode
define config.developer = True