from flask import Flask, Response, jsonify, request
from .auth import requires_auth
from .camera_stream import mjpeg_generator

VALID_CMDS = {"STOP", "AUTO_LF", "MANUAL", "FWD", "BACK", "LEFT", "RIGHT"}


def create_app(output, robot=None):
    """
    output: StreamingOutput from camera_stream.create_camera()
    robot:  RobotSerial (optional). If None, control buttons will show but return 'not connected'.
    """
    app = Flask(__name__)

    PAGE_HTML = r"""
<!doctype html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Surveillance Bot Dashboard</title>
  <style>
    body{margin:0;font-family:system-ui;background:#0b1020;color:#e9ecf1}
    header{padding:14px 16px;background:rgba(255,255,255,.06);border-bottom:1px solid rgba(255,255,255,.1)}
    .wrap{max-width:1100px;margin:0 auto;padding:16px;display:grid;grid-template-columns:1.6fr .9fr;gap:14px}
    @media (max-width: 900px){ .wrap{grid-template-columns:1fr} }
    .card{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:16px;overflow:hidden}
    .top{display:flex;justify-content:space-between;gap:10px;align-items:center;padding:12px 14px;border-bottom:1px solid rgba(255,255,255,.08)}
    .btn{cursor:pointer;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.09);color:#e9ecf1;padding:10px 12px;border-radius:12px;font-weight:800}
    .btn:active{transform:scale(.98)}
    img{width:100%;display:block;aspect-ratio:16/9;object-fit:cover;background:#000}
    small{opacity:.75}
    .pad{padding:12px 14px}
    .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
    .wide{grid-column:1/-1}
    .status{font-weight:700}
    .pill{display:inline-block;padding:4px 10px;border-radius:999px;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.08);font-weight:800;font-size:12px}
    .row{display:flex;gap:10px;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.08)}
    .row:last-child{border-bottom:none}
    input[type=range]{width:100%}
    .muted{opacity:.8;font-size:13px;line-height:1.35}
  </style>
</head>
<body>
  <header><b>Surveillance Bot</b> <small>Live Stream + Robot Control</small></header>

  <div class="wrap">
    <div class="card">
      <div class="top">
        <div>
          <b>Live Camera</b><br><small id="host"></small>
        </div>
        <div>
          <button class="btn" onclick="refreshStream()">Refresh</button>
          <button class="btn" onclick="fs()">Fullscreen</button>
        </div>
      </div>
      <div id="box"><img id="cam" src="/video"></div>
    </div>

    <div class="card">
      <div class="top">
        <div>
          <b>Robot Control</b><br><small class="status" id="st">Ready</small>
        </div>
        <button class="btn" onclick="sendCmd('STOP')">STOP</button>
      </div>

      <div class="pad">
        <div class="grid">
          <button class="btn wide" onmousedown="hold('FWD')" ontouchstart="hold('FWD')" onmouseup="release()" ontouchend="release()">▲ Forward</button>
          <button class="btn" onmousedown="hold('LEFT')" ontouchstart="hold('LEFT')" onmouseup="release()" ontouchend="release()">◀ Left</button>
          <button class="btn" onclick="sendCmd('AUTO_LF')">AUTO LFR</button>
          <button class="btn" onmousedown="hold('RIGHT')" ontouchstart="hold('RIGHT')" onmouseup="release()" ontouchend="release()">Right ▶</button>
          <button class="btn wide" onmousedown="hold('BACK')" ontouchstart="hold('BACK')" onmouseup="release()" ontouchend="release()">▼ Back</button>
          <button class="btn wide" onclick="sendCmd('MANUAL')">Manual Mode</button>
        </div>

        <div style="margin-top:14px">
          <b>Speed</b> <small id="spdLbl">(120)</small>
          <input id="spd" type="range" min="0" max="255" value="120" oninput="spdLbl.textContent='(' + this.value + ')'">
          <button class="btn wide" style="margin-top:10px" onclick="setSpeed()">Set Speed</button>
        </div>

        <p class="muted" style="margin-top:14px">
          Tip: Hold Forward/Back/Left/Right to move, release to stop. AUTO LFR runs the line follower logic on Arduino.
        </p>

        <div style="margin-top:14px" class="card" id="sensorCard" hidden>
          <div class="top">
            <div>
              <b>Sensors</b><br><small class="muted">Flame + MQ-2</small>
            </div>
            <span class="pill" id="serPill">Serial: ?</span>
          </div>
          <div class="pad" style="padding-top:0">
            <div class="row"><div>Flame</div><div><span class="pill" id="flamePill">-</span></div></div>
            <div class="row"><div>MQ-2 Gas/Smoke</div><div><span class="pill" id="gasPill">-</span></div></div>
            <div class="row"><div>MQ-2 Value</div><div><b id="mq2Val">-</b></div></div>
            <div class="row"><div>Flame Value</div><div><b id="flameVal">-</b></div></div>
            <div class="row"><div>Warm-up</div><div><span class="pill" id="warmPill">-</span></div></div>
          </div>
        </div>
      </div>
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

  let holdTimer=null;
  function setStatus(msg){ document.getElementById("st").textContent = msg; }

  async function sendCmd(cmd){
    try{
      setStatus("Sending: " + cmd + " …");
      const r = await fetch("/cmd?c=" + encodeURIComponent(cmd), {cache:"no-store"});
      const j = await r.json();
      if(j.ok) setStatus("✅ " + j.msg);
      else setStatus("⚠️ " + j.msg);
    }catch(e){
      setStatus("❌ error");
    }
  }

  function hold(cmd){
    sendCmd(cmd);
    clearInterval(holdTimer);
    holdTimer=setInterval(()=>sendCmd(cmd), 250); // keep moving
  }
  function release(){
    clearInterval(holdTimer);
    holdTimer=null;
    sendCmd("STOP");
  }

  function setSpeed(){
    const v=document.getElementById("spd").value;
    sendCmd("SPEED " + v);
  }

  async function pollStatus(){
    try{
      const r = await fetch('/status', {cache:'no-store'});
      const j = await r.json();
      const card = document.getElementById('sensorCard');
      if(j && j.sensor){
        card.hidden = false;
        document.getElementById('serPill').textContent = 'Serial: ' + (j.serial_connected ? 'OK' : 'OFF');

        const flame = !!j.sensor.flame;
        const gas = !!j.sensor.gas;
        document.getElementById('flamePill').textContent = flame ? '🔥 DETECTED' : 'OK';
        document.getElementById('gasPill').textContent = gas ? '⚠️ BAD' : 'GOOD';
        document.getElementById('mq2Val').textContent = j.sensor.mq2_val;
        document.getElementById('flameVal').textContent = j.sensor.flame_val;
        document.getElementById('warmPill').textContent = j.sensor.warm ? 'WARMING' : 'READY';
      }
    }catch(e){
      // ignore
    }
  }
  setInterval(pollStatus, 700);
  pollStatus();
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

    @app.route("/cmd")
    @requires_auth
    def cmd():
        c = (request.args.get("c") or "").strip()
        if not c:
            return jsonify(ok=False, msg="Missing command")

        # SPEED is special: "SPEED 120"
        if c.upper().startswith("SPEED"):
            parts = c.split()
            if len(parts) != 2 or not parts[1].isdigit():
                return jsonify(ok=False, msg="Use: SPEED <0-255>")
            if robot is None:
                return jsonify(ok=False, msg="Robot serial not configured")
            ok = robot.speed(int(parts[1]))
            return jsonify(ok=ok, msg=("Speed set" if ok else "Serial not connected"))

        cmd_u = c.upper()
        if cmd_u not in VALID_CMDS:
            return jsonify(ok=False, msg="Invalid command")

        if robot is None:
            return jsonify(ok=False, msg="Robot serial not configured")

        ok = robot.send(cmd_u)
        return jsonify(ok=ok, msg=(cmd_u if ok else "Serial not connected"))

    @app.route("/status")
    @requires_auth
    def status():
        if robot is None:
            return jsonify(serial_connected=False, sensor=None)
        sensor = None
        try:
            sensor = robot.get_sensor_state().as_dict()
        except Exception:
            sensor = None
        return jsonify(serial_connected=robot.is_connected, sensor=sensor)

    return app
