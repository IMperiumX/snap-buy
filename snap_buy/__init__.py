__version__ = "0.1.0"
__version_info__ = tuple(int(num) if num.isdigit() else num for num in __version__.replace("-", ".", 1).split("."))

import secrets


def get_random_string(
    length: int = 12, allowed_chars: str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
) -> str:
    """Return a securely generated random string.

    Args:
        length (int, optional): Length of random string. Defaults to 12.
        allowed_chars (str, optional): Allowed characters in random string. Defaults to "abcdefghijk3456789".

    Returns:
        str: Random string.
    """
    return "".join(secrets.choice(allowed_chars) for i in range(length))


def unique_upload(instance, filename):
    """Return a unique filename for uploaded files."""
    path = f"{instance.__class__.__name__.lower()}s/{filename}"
    if instance.__class__.objects.filter(image=path).exists():
        # Get the extension of the file
        extension = filename.split(".")[-1]
        # Get the filename without extension
        filename_without_extension = filename.replace(f".{extension}", "")
        # Add a random string before the filename and after the extension
        filename = f"{filename_without_extension}_{get_random_string(10)}{extension}"
        return unique_upload(instance, filename)
    return path


def file_upload(folder_name, instance, filename):
    return f"{folder_name}/{unique_upload(instance, filename)}"
