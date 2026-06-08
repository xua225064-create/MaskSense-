import random


def random_size():
    # Danh sách các kích thước cửa sổ từ TV đến điện thoại (đơn vị pixel)
    sizes = [
        # Kích thước TV
        (3840, 2160),  # 4K TV
        (1920, 1080),  # Full HD TV
        (1366, 768),  # HD TV
        (2560, 1440),  # 2K (Quad HD)
        (1280, 720),  # HD
        (1024, 768),  # XGA
        (800, 600),  # SVGA
        (640, 480),  # VGA
        (3840, 1600),  # 4K Ultra-Wide
        (2560, 1080),  # 2K Ultra-Wide
        (1920, 800),  # HD Ultra-Wide
        (1280, 480),  # FWVGA
        (1024, 600),  # WSVGA
        (800, 480),  # HVGA
        (2560, 1600),  # WQXGA
        (2048, 1152),  # QWXGA
        (1920, 1200),  # WUXGA
        (1600, 900),  # HD+
        (1440, 900),  # WXGA+
        (1366, 768),  # WXGA
        (1280, 800),  # WXGA
        (1280, 768),  # WXGA
        (1280, 720),  # HD
        (1024, 768),  # XGA
        (800, 600),  # SVGA
        (640, 480),  # VGA
        (3840, 1600),  # 4K Ultra-Wide
        (2560, 1080),  # 2K Ultra-Wide
        (1920, 800),  # HD Ultra-Wide
        (1280, 480),  # FWVGA
        (1024, 600),  # WSVGA
        (800, 480),  # HVGA
        (640, 360),  # nHD
        (2560, 1600),  # WQXGA
        (2048, 1152),  # QWXGA
        (1920, 1200),  # WUXGA
        (1600, 900),  # HD+
        (1440, 900),  # WXGA+
        (1366, 768),  # WXGA
        (1280, 800),  # WXGA
        (1280, 768),  # WXGA
        (1280, 720),  # HD
        (1024, 768),  # XGA
        (800, 600),  # SVGA
        (640, 480),  # VGA
        (3840, 1600),  # 4K Ultra-Wide
        (2560, 1080),  # 2K Ultra-Wide
        (1920, 800),  # HD Ultra-Wide
        (1280, 480),  # FWVGA
        (1024, 600),  # WSVGA
        (800, 480),  # HVGA
        (640, 360),  # nHD
        (320, 180),  # qHD
        (2560, 1600),  # WQXGA
        (2048, 1152),  # QWXGA
        (1920, 1200),  # WUXGA
        (1600, 900),  # HD+
        (1440, 900),  # WXGA+
        (1366, 768),  # WXGA
        (1280, 800),  # WXGA
        (1280, 768),  # WXGA
        (1280, 720),  # HD
        (1024, 768),  # XGA
        (800, 600),  # SVGA
        (640, 480),  # VGA
    ]

    # Chọn một kích thước ngẫu nhiên từ danh sách
    # return random.choice(sizes)
    return (640, 480)
