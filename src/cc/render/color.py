class C:
    # ANSI escape codes for colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"  # Bright Black
    RESET = "\033[0m"  # Reset to default

    # Background colors (optional, but good to have)
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

    # Styles (optional)
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    INVERT = "\033[7m"

    # Aliases for common usage in renderer
    R = RESET
    r = RED
    g = GREEN
    y = YELLOW
    b = BLUE
    m = MAGENTA
    c = CYAN
    w = WHITE
    k = BLACK
    G = GRAY

    # Lowercase aliases
    red = RED
    green = GREEN
    yellow = YELLOW
    blue = BLUE
    magenta = MAGENTA
    cyan = CYAN
    white = WHITE
    black = BLACK
    gray = GRAY
