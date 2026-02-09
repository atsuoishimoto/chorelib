# /// script
# dependencies = [
#   "chorelib",
#   "pillow"
# ]
# ///

"""
Thumbnail banner builder — generates banner images from flag PNGs.

Reads flag images organized by region (flags/<region>/*.png) and builds:
  1. Per-region banners — flags resized and joined horizontally (e.g. asia.jpeg)
  2. World banner      — all region banners stacked vertically (world.jpeg)

Demonstrates:
  - Regex targets with named groups: (?P<REGION>...) to match any <region>.jpeg
  - Callable dependencies: a function that dynamically returns file lists
  - Two-level dependency chain: flag PNGs → region banners → world banner
  - Parallel builds: independent region banners can be built concurrently with -w

Usage:
    uv run make.py            # Build world.jpeg (default target)
    uv run make.py -w 4       # Build with 4 parallel workers
    uv run make.py asia.jpeg  # Build only the Asia banner
    uv run make.py clean      # Remove generated files
"""

from pathlib import Path

from PIL import Image

from chorelib import Main, rule, shell, task

main = Main()
BANNER_HEIGHT = 64


def get_regions():
    """Discover region names from subdirectories under flags/."""
    return list(p.name for p in Path("flags").glob("*") if p.is_dir())


# Top-level target: stack all region banners vertically into one world banner.
# Depends on each <region>.jpeg, so changing any flag triggers a rebuild
# through the dependency chain: flag PNG → region banner → world banner.
@rule("world.jpeg", depends=[f"{region}.jpeg" for region in get_regions()])
def world_banner(target, deps, needs):
    """Build world banner"""
    print("Building:", target, "depends:", deps)
    region_banners = [Image.open(filename) for filename in deps]

    width = sum(w.width for w in region_banners)
    banner = Image.new("RGB", (width, BANNER_HEIGHT * len(region_banners)))

    for n, img in enumerate(region_banners):
        banner.paste(img, (0, BANNER_HEIGHT * n))
    banner.save(target, format="JPEG")


def get_region_files(rule, match):
    """Callable dependency: return all flag PNGs for the matched region.

    Called by chorelib when resolving dependencies for a region banner.
    The `match` argument is the regex match object, so match["REGION"]
    gives the region name captured by the named group.
    """
    region = match["REGION"]
    return sorted((Path("flags") / region).glob("*"))


# Regex target with a named group (?P<REGION>...) — matches any <name>.jpeg.
# The `depends` parameter is a callable (get_region_files) instead of a static
# list, so chorelib calls it at build time to discover the actual flag files
# for the matched region.
@rule("^(?P<REGION>[^.]+).jpeg", depends=get_region_files)
def region_banner(target, deps, needs):
    """Build region banner"""

    print("Building:", target, "depends:", deps)
    flags = [Image.open(filename) for filename in deps]

    def resize_image(img):
        scale = BANNER_HEIGHT / img.height
        target_w = max(int(img.width * scale), 1)
        return img.resize((target_w, BANNER_HEIGHT))

    resized = [resize_image(flag) for flag in flags]
    width = sum(img.width for img in resized)
    banner = Image.new("RGBA", (width, 64))
    x_offset = 0
    for img in resized:
        banner.paste(img, (x_offset, 0))
        x_offset += img.width

    banner.convert("RGB").save(target, format="JPEG")


@task
def clean():
    """Clean banner files"""
    shell("rm -f", (f"{region}.jpeg" for region in get_regions()), "world.jpeg")


if __name__ == "__main__":
    main.run()
