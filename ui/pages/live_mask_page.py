"""
Live face mask detection using WebRTC (streamlit-webrtc).
"""

import logging

import streamlit as st

from config.settings import MASK_FRAME_SKIP
from face_mask.webrtc_processor import MaskVideoProcessor
from ui.components.layout import render_page_header, render_info_strip

logger = logging.getLogger(__name__)

try:
    from streamlit_webrtc import RTCConfiguration, webrtc_streamer
except ImportError as e:
    webrtc_streamer = None
    RTCConfiguration = None
    _IMPORT_ERROR = str(e)
else:
    _IMPORT_ERROR = None


class LiveMaskPage:
    """Full-page live webcam mask overlay (Option B: WebRTC)."""

    def render(self) -> None:
        render_page_header(
            title="Live Mask Detection",
            subtitle="Real-time webcam stream with on-device mask heuristics. "
            "Use good lighting and face the camera.",
            icon="🎥",
        )

        render_info_strip(
            items=[
                ("Privacy", "Video stays in your browser session; frames are processed locally."),
                ("Tip", "Works best on localhost or HTTPS deployments."),
                ("Policy", "Heuristic only—not a medical device. Tune thresholds for your site."),
            ]
        )

        if webrtc_streamer is None:
            st.error("streamlit-webrtc is not installed.")
            st.code("pip install streamlit-webrtc av ultralytics", language="bash")
            if _IMPORT_ERROR:
                st.caption(_IMPORT_ERROR)
            return

        st.markdown('<div class="webrtc-shell">', unsafe_allow_html=True)

        ctx = webrtc_streamer(
            key="live-mask-webrtc",
            rtc_configuration=RTCConfiguration(
                {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
            ),
            video_processor_factory=lambda: MaskVideoProcessor(
                frame_skip=MASK_FRAME_SKIP
            ),
            media_stream_constraints={"video": True, "audio": False},
            # Sync processing avoids some threading/OpenCV issues on Windows
            async_processing=False,
        )

        st.markdown("</div>", unsafe_allow_html=True)

        playing = getattr(getattr(ctx, "state", None), "playing", False)
        if playing:
            st.success("Stream active — look at the camera. Labels: MASK · NO MASK · UNCERTAIN.")
        else:
            st.info("Start the camera using the controls above. Allow browser permissions if prompted.")

        with st.expander("How it works", expanded=False):
            st.markdown(
                """
                - **Detection**: OpenCV Haar frontal faces.
                - **Mask guess**: Lower-face region — HSV skin coverage + texture (Laplacian variance).
                - **Colors**: Orange = mask-like, green = no mask, yellow = uncertain.
                """
            )

        with st.expander("Troubleshooting", expanded=False):
            st.markdown(
                """
                - **Stream won't start**: Use **Chrome or Edge**, allow camera, try `http://localhost:8501` (not `127.0.0.1` if one fails).
                - **Black / frozen video**: Close other apps using the webcam; reload the page; set `MASK_FRAME_SKIP=3` in `.env` if CPU is overloaded.
                - **No boxes**: Face the camera straight on; improve lighting; move closer.
                - **Wrong label**: Detection uses color/texture heuristics (not a medical-grade model). For attendance, use **Mark Attendance** — it blocks masks before recognition.
                """
            )
