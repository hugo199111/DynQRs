# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 OpenFollow Project
"""Windows camera capture through GStreamer's native device providers."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from openfollow.video.failure import SourceKind
from openfollow.video.inputs._base import (
    ConfigField,
    InputCapabilities,
    ReconnectPolicy,
    VideoInputBase,
    WebRoute,
    coerce_positive_int,
)


def _devices() -> list[tuple[str, Any]]:
    if sys.platform != "win32":
        return []
    from gi.repository import Gst

    Gst.init(None)
    monitor = Gst.DeviceMonitor.new()
    monitor.add_filter("Video/Source", Gst.Caps.from_string("video/x-raw"))
    if not monitor.start():
        return []
    try:
        result = []
        for device in monitor.get_devices() or []:
            props = device.get_properties()
            path = props.get_string("device.path") if props is not None else None
            result.append((path or device.get_display_name(), device))
        return result
    finally:
        monitor.stop()


class WindowsCameraInput(VideoInputBase):
    input_id = "windows_camera"
    display_name = "USB Camera (Windows)"
    source_element_name = "windows_camera"
    source_kind = SourceKind.LOCAL

    @classmethod
    def config_fields(cls) -> list[ConfigField]:
        return [
            ConfigField("windows_camera", str, "", "Device"),
            ConfigField("windows_camera_width", int, 1920, "Width"),
            ConfigField("windows_camera_height", int, 1080, "Height"),
            ConfigField("windows_camera_framerate", int, 30, "Framerate"),
        ]

    @classmethod
    def capabilities(cls) -> InputCapabilities:
        return InputCapabilities(
            has_source_discovery=True,
            has_source_selection=True,
            selection_title="SELECT USB CAMERA",
            force_zero_latency=True,
        )

    @classmethod
    def reconnect_policy(cls) -> ReconnectPolicy:
        return ReconnectPolicy(
            max_attempts=3, min_delay=1.0, max_delay=5.0, connection_timeout=5.0, fallback_to_selection=True
        )

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        if sys.platform != "win32":
            return False, "Windows-only camera input"
        try:
            from gi.repository import Gst

            Gst.init(None)
            available = any(Gst.ElementFactory.find(name) for name in ("mfvideosrc", "ksvideosrc", "dshowvideosrc"))
            return (True, "") if available else (False, "Windows GStreamer camera plugin not installed")
        except (ImportError, ValueError):
            return False, "GStreamer not available"

    @classmethod
    def discover_sources(cls, timeout: float = 2.0) -> list[str]:
        return [name for name, _device in _devices()]

    @classmethod
    def get_source_label(cls, config: dict[str, Any]) -> str:
        return str(config.get("windows_camera", "") or "Default camera")

    def create_pipeline(
        self,
        config: dict[str, Any],
        sink: Any,
        build_overlay_tail: Callable[..., Any],
        prepare_sink: Callable[..., Any],
    ) -> Any:
        from gi.repository import Gst

        selected = str(config.get("windows_camera", ""))
        devices = _devices()
        matches = [device for name, device in devices if name == selected] if selected else [d for _, d in devices[:1]]
        if len(matches) != 1:
            raise RuntimeError("Selected Windows camera is unavailable or ambiguous")
        source = matches[0].create_element(self.source_element_name)
        if source is None:
            raise RuntimeError("Could not create the Windows camera source")
        caps = Gst.ElementFactory.make("capsfilter", "camera_caps")
        queue = Gst.ElementFactory.make("queue", "camera_queue")
        convert = Gst.ElementFactory.make("videoconvert", "camera_convert")
        sink = prepare_sink()
        if any(element is None for element in (caps, queue, convert, sink)):
            raise RuntimeError("Windows camera pipeline dependencies are unavailable")
        width = coerce_positive_int(config.get("windows_camera_width"), 1920)
        height = coerce_positive_int(config.get("windows_camera_height"), 1080)
        fps = coerce_positive_int(config.get("windows_camera_framerate"), 30)
        caps.set_property("caps", Gst.Caps.from_string(f"video/x-raw,width={width},height={height},framerate={fps}/1"))
        queue.set_property("max-size-buffers", 2)
        queue.set_property("max-size-bytes", 0)
        queue.set_property("max-size-time", 0)
        queue.set_property("leaky", 2)
        pipeline = Gst.Pipeline.new("windows-camera")
        for element in (source, caps, queue, convert, sink):
            pipeline.add(element)
        for left, right in ((source, caps), (caps, queue), (queue, convert)):
            if not left.link(right):
                raise RuntimeError("Could not link the Windows camera pipeline")
        build_overlay_tail(pipeline, convert, sink)
        return pipeline

    @classmethod
    def web_routes(cls) -> list[WebRoute]:
        return [WebRoute("GET", "/video-input/windows-camera/devices", "handle_devices")]

    def handle_devices(self, config: dict[str, Any]) -> str:
        current = config.get("windows_camera", "")
        options = ['<option value="">Default camera</option>']
        for name, device in _devices():
            selected = " selected" if name == current else ""
            options.append(
                f'<option value="{self._esc(name)}"{selected}>{self._esc(device.get_display_name())}</option>'
            )
        return "".join(options)

    @classmethod
    def web_ui_html(cls, config: dict[str, Any]) -> str:
        selected = cls._esc(config.get("windows_camera", ""))
        html = '<div class="row"><div class="field wide"><label>Device</label>'
        html += '<select name="windows_camera" hx-get="/video-input/windows-camera/devices"'
        html += f' hx-trigger="load" hx-target="this" hx-swap="innerHTML"><option value="{selected}">'
        html += f'{selected or "Default camera"}</option></select></div></div><div class="row">'
        for field in cls.config_fields()[1:]:
            value = coerce_positive_int(config.get(field.name), field.default)
            html += f'<div class="field"><label>{field.label}</label><input type="number" name="{field.name}"'
            html += f' value="{value}" min="1"></div>'
        return html + "</div>"

    def on_bus_async_done(self, pipeline: Any) -> None:
        pipeline.set_latency(0)
