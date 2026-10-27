"""
Puzzle #31 — local QR code generator microservice (Python).

GET  /qr?data=<text>&size=<box_size 1-40>&border=<modules 0-20>&format=png|svg
  Generates a real QR code (python `qrcode` library, Reed-Solomon
  error-corrected per the actual QR spec) and streams it back as an image.

GET  /          — tiny local form for manual use (type text, see the QR live).
GET  /health
"""
import io

import qrcode
import qrcode.image.svg
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse

app = FastAPI(title="qr-code-service")

ERROR_CORRECT = {
    "L": qrcode.constants.ERROR_CORRECT_L,
    "M": qrcode.constants.ERROR_CORRECT_M,
    "Q": qrcode.constants.ERROR_CORRECT_Q,
    "H": qrcode.constants.ERROR_CORRECT_H,
}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def form():
    return """
    <!doctype html><html><head><title>QR Code Service</title>
    <style>
      body{font-family:system-ui;max-width:480px;margin:4rem auto;padding:0 1rem}
      input,select{font-size:1rem;padding:0.5rem;width:100%;margin:0.4rem 0 1rem;box-sizing:border-box}
      img{display:block;margin-top:1rem;border:1px solid #ddd}
    </style></head>
    <body>
      <h2>Local QR Code Generator</h2>
      <input id="data" placeholder="Text or URL to encode" value="https://example.com" />
      <select id="ec">
        <option value="L">L — 7% recovery</option>
        <option value="M" selected>M — 15% recovery</option>
        <option value="Q">Q — 25% recovery</option>
        <option value="H">H — 30% recovery</option>
      </select>
      <button onclick="go()">Generate</button>
      <img id="out" width="300" height="300" />
      <script>
        function go(){
          const data = encodeURIComponent(document.getElementById('data').value);
          const ec = document.getElementById('ec').value;
          document.getElementById('out').src = `/qr?data=${data}&ec=${ec}&_=${Date.now()}`;
        }
        go();
      </script>
    </body></html>
    """


@app.get("/qr")
def generate_qr(
    data: str = Query(..., min_length=1, max_length=2000),
    size: int = Query(10, ge=1, le=40, description="box_size in pixels per module"),
    border: int = Query(4, ge=0, le=20, description="quiet-zone width in modules"),
    ec: str = Query("M", pattern="^[LMQH]$"),
    fmt: str = Query("png", pattern="^(png|svg)$"),
):
    if fmt == "svg":
        factory = qrcode.image.svg.SvgPathImage
        qr = qrcode.QRCode(
            error_correction=ERROR_CORRECT[ec], box_size=size, border=border,
            image_factory=factory,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image()
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/svg+xml")

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT[ec], box_size=size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")
