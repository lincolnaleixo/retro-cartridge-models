"""Sanitize portable Blender source snapshots before saving."""

import bpy


def sanitize_source_paths():
    """Keep packed sources portable without retaining local machine paths."""
    extensions = {'JPEG': '.jpg', 'PNG': '.png', 'TARGA': '.tga', 'TIFF': '.tif'}
    for image in bpy.data.images:
        if not image.packed_file:
            continue
        extension = extensions.get(image.file_format, '')
        portable_path = '//textures/' + bpy.path.clean_name(image.name) + extension
        image.filepath = portable_path
        # The packed entry keeps its own source filename; changing only the
        # image filepath leaves the original absolute filename in the .blend.
        for packed in image.packed_files:
            packed.filepath = portable_path
    for scene in bpy.data.scenes:
        scene.render.filepath = '//renders/'
    for screen in bpy.data.screens:
        for area in screen.areas:
            for space in area.spaces:
                if space.type == 'FILE_BROWSER' and space.params:
                    space.params.directory = b'//'
