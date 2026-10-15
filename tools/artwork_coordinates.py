"""Map a label's UVs into an unedited reference photograph."""


def photo_uv(u, v, rectangle=(0, 0, 1, 1), quadrilateral=None):
    """Return source UVs; quad corners are bottom-left, bottom-right, top-right, top-left.

    Coordinates use an image's bottom-left origin. A quadrilateral removes a
    photographed label's small rotation/keystone without resampling its pixels.
    This is bilinear mapping, intended for nearly frontal photographs.
    """
    if quadrilateral is None:
        left, bottom, right, top = rectangle
        return left + u * (right - left), bottom + v * (top - bottom)
    if len(quadrilateral) != 8 or any(not 0 <= value <= 1 for value in quadrilateral):
        raise ValueError('Photo quadrilateral needs four normalized UV corners')
    bl, br, tr, tl = [quadrilateral[i:i + 2] for i in range(0, 8, 2)]
    return tuple((1 - v) * ((1 - u) * bl[i] + u * br[i])
                 + v * ((1 - u) * tl[i] + u * tr[i]) for i in range(2))
