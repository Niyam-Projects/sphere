import pkgutil

# Allow other distributions (packages/*) to extend the `sphere` namespace.
# This makes `sphere` a namespace package when multiple distributions
# provide the same top-level package name.
__path__ = pkgutil.extend_path(__path__, __name__)


def main() -> None:
    print("Hello from sphere!")
