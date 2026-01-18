from flask import Flask, Response
from .auth import requires_auth
from .camera_stream import mjpeg_generator

def create_app(output):
    app = Flask(__name__)

    PAGE_HTML = """
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Home Security Dashboard</title>
  <style>
    body{margin:0;font-family:system-ui;background:#0b1020;color:#e9ecf1}
    header{padding:14px 16px;background:rgba(255,255,255,.06);border-bottom:1px solid rgba(255,255,255,.1)}
    .wrap{max-width:1000px;margin:0 auto;padding:16px}
    .card{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:16px;overflow:hidden}
    .top{display:flex;justify-content:space-between;gap:10px;align-items:center;padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.08)}
    .btn{cursor:pointer;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.09);color:#e9ecf1;padding:8px 10px;border-radius:12px;font-weight:700}
    img{width:100%;display:block;aspect-ratio:16/9;object-fit:cover;background:#000}
    small{opacity:.75}
  </style>
</head>
<body>
  <header><b>Home Security Dashboard</b> <small>Live Camera (Same Wi-Fi)</small></header>
  <div class="wrap">
    <div class="card">
      <div class="top">
        <div>
          <b>Live Stream</b><br><small id="host"></small>
        </div>
        <div>
          <button class="btn" onclick="refreshStream()">Refresh</button>
          <button class="btn" onclick="fs()">Fullscreen</button>
        </div>
      </div>
      <div id="box"><img id="cam" src="/video"></div>
    </div>
  </div>
<script>
  document.getElementById("host").textContent = "http://" + window.location.host;
  function refreshStream(){
    const img=document.getElementById("cam");
    img.src="/video?ts=" + Date.now();
  }
  function fs(){
    const el=document.getElementById("box");
    if(!document.fullscreenElement) el.requestFullscreen().catch(()=>{});
    else document.exitFullscreen().catch(()=>{});
  }
</script>
</body>
</html>
    """

    @app.route("/")
    @requires_auth
    def index():
        return PAGE_HTML

    @app.route("/video")
    @requires_auth
    def video():
        return Response(mjpeg_generator(output),
                        mimetype="multipart/x-mixed-replace; boundary=frame")

    return app
