#!/usr/bin/env python3
"""Reviewer-only DXF render using ezdxf SVG and system librsvg/cairo.

No author renderer is imported. Input/output paths are explicit arguments.
"""
import argparse
import ctypes as C
from pathlib import Path
import ezdxf
from ezdxf.addons.drawing import Frontend, RenderContext, svg, layout

def render(source, output):
    d=ezdxf.readfile(source); backend=svg.SVGBackend()
    Frontend(RenderContext(d),backend).draw_layout(d.modelspace(),finalize=True)
    xml=backend.get_string(layout.Page(350,150,margins=layout.Margins(5,5,5,5)))
    output.with_suffix('.svg').write_text(xml)
    rsvg=C.CDLL('librsvg-2.so.2');cairo=C.CDLL('libcairo.so.2');gobject=C.CDLL('libgobject-2.0.so.0')
    def bind(lib,name,args,result):
        fn=getattr(lib,name);fn.argtypes=args;fn.restype=result;return fn
    make=bind(rsvg,'rsvg_handle_new_from_data',[C.c_char_p,C.c_size_t,C.c_void_p],C.c_void_p)
    class Dimensions(C.Structure):
        _fields_=[('width',C.c_int),('height',C.c_int),('em',C.c_double),('ex',C.c_double)]
    dimensions=bind(rsvg,'rsvg_handle_get_dimensions',[C.c_void_p,C.POINTER(Dimensions)],None)
    raster=bind(rsvg,'rsvg_handle_render_cairo',[C.c_void_p,C.c_void_p],C.c_int)
    surface_create=bind(cairo,'cairo_image_surface_create',[C.c_int,C.c_int,C.c_int],C.c_void_p)
    context_create=bind(cairo,'cairo_create',[C.c_void_p],C.c_void_p)
    scale=bind(cairo,'cairo_scale',[C.c_void_p,C.c_double,C.c_double],None)
    write=bind(cairo,'cairo_surface_write_to_png',[C.c_void_p,C.c_char_p],C.c_int)
    destroy=bind(cairo,'cairo_destroy',[C.c_void_p],None)
    surface_destroy=bind(cairo,'cairo_surface_destroy',[C.c_void_p],None)
    unref=bind(gobject,'g_object_unref',[C.c_void_p],None)
    data=xml.encode();handle=make(data,len(data),None)
    if not handle:raise RuntimeError('Cannot parse reviewer SVG')
    dim=Dimensions();dimensions(handle,C.byref(dim))
    surface=surface_create(0,dim.width*2,dim.height*2);context=context_create(surface);scale(context,2,2)
    if not raster(handle,context):raise RuntimeError('Cannot rasterize reviewer SVG')
    if write(surface,str(output.with_suffix('.png')).encode()):raise RuntimeError('Cannot write PNG')
    destroy(context);surface_destroy(surface);unref(handle)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('output',type=Path)
    args=ap.parse_args();render(args.source,args.output)
