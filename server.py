from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import uuid

app = Flask(__name__)
app.secret_key = 'secretkey'
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# In-memory user store
users = {}  # username: password
user_drawings = {}  # username: {page_id: drawing_data}

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real-Time Drawing</title>
    <style>
        * { margin: 0; padding: 0; overflow: hidden; }
        body { font-family: Arial, sans-serif; text-align: center; }
        .canvas-container { position: relative; width: 100vw; height: 100vh; }
        canvas { position: absolute; top: 0; left: 0; touch-action: none; background: white; }
        .button-container {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 10px;
            z-index: 1000;
            flex-direction: column;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px;
            border-radius: 10px;
            display: none;
        }
        button {
            padding: 12px 20px;
            font-size: 16px;
            background: gray;
            color: white;
            border: none;
            cursor: pointer;
            border-radius: 8px;
        }
        #eraserBtn { background: gray; }
        #addCanvasBtn { background: blue; }
        #toggleMenuBtn {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: black;
            color: white;
            font-size: 24px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            text-align: center;
            line-height: 50px;
            cursor: pointer;
            z-index: 2000;
        }
        .color-picker {
            display: flex;
            gap: 5px;
        }
        .color-picker div {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            border: 2px solid transparent;
        }
    </style>
</head>
<body>
    <div id="toggleMenuBtn">☰</div>
    <div class="button-container" id="buttonContainer">
        <button id="eraserBtn">Eraser OFF</button>
        <button id="addCanvasBtn">Add New Canvas</button>
        <button id="saveCanvasBtn">Save Page</button>
        <button id="logoutBtn">Logout</button>
        <input id="loadPageInput" placeholder="Page ID" />
        <button id="loadPageBtn">Load Page</button>
        <div class="color-picker">
            <div style="background: black;" data-color="black"></div>
            <div style="background: red;" data-color="red"></div>
            <div style="background: blue;" data-color="blue"></div>
            <div style="background: green;" data-color="green"></div>
            <div style="background: orange;" data-color="orange"></div>
        </div>
    </div>
    <div class="canvas-container" id="canvasContainer">
        <canvas class="drawingCanvas"></canvas>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.4.1/socket.io.js"></script>
    <script>
        const socket = io();
        const canvasContainer = document.getElementById("canvasContainer");
        const eraserBtn = document.getElementById("eraserBtn");
        const addCanvasBtn = document.getElementById("addCanvasBtn");
        const toggleMenuBtn = document.getElementById("toggleMenuBtn");
        const buttonContainer = document.getElementById("buttonContainer");
        const colorPicker = document.querySelectorAll(".color-picker div");
        const saveCanvasBtn = document.getElementById("saveCanvasBtn");
        const loadPageBtn = document.getElementById("loadPageBtn");
        const loadPageInput = document.getElementById("loadPageInput");
        const logoutBtn = document.getElementById("logoutBtn");
        let canvasList = [];
        let erasing = false;
        let penColor = "black";

        function createCanvas(sync = true) {
            const canvas = document.createElement("canvas");
            canvas.classList.add("drawingCanvas");
            canvasContainer.appendChild(canvas);
            setupCanvas(canvas);

            if (sync) {
                socket.emit("add_canvas");
            }
        }

        function setupCanvas(canvas) {
            const ctx = canvas.getContext("2d");

            function resizeCanvas() {
                canvas.width = window.innerWidth;
                canvas.height = window.innerHeight;
            }
            resizeCanvas();
            window.addEventListener("resize", resizeCanvas);

            let drawing = false;
            let lastX = null, lastY = null;

            function getPosition(e) {
                if (e.touches) {
                    return { x: e.touches[0].clientX, y: e.touches[0].clientY };
                }
                return { x: e.clientX, y: e.clientY };
            }

            function startDrawing(e) {
                e.preventDefault();
                drawing = true;
                lastX = lastY = null;
            }

            function stopDrawing() {
                drawing = false;
                lastX = lastY = null;
            }

            function draw(e) {
                if (!drawing) return;
                e.preventDefault();

                let { x, y } = getPosition(e);

                ctx.lineWidth = erasing ? 20 : 3;
                ctx.strokeStyle = erasing ? "white" : penColor;

                if (lastX !== null && lastY !== null) {
                    ctx.beginPath();
                    ctx.moveTo(lastX, lastY);
                    ctx.lineTo(x, y);
                    ctx.stroke();

                    socket.emit("draw", {
                        lastX: lastX / canvas.width,
                        lastY: lastY / canvas.height,
                        x: x / canvas.width,
                        y: y / canvas.height,
                        erasing,
                        color: penColor
                    });
                }

                lastX = x;
                lastY = y;
            }

            socket.on("draw", (data) => {
                ctx.lineWidth = data.erasing ? 20 : 3;
                ctx.strokeStyle = data.erasing ? "white" : data.color;
                ctx.beginPath();
                ctx.moveTo(data.lastX * canvas.width, data.lastY * canvas.height);
                ctx.lineTo(data.x * canvas.width, data.y * canvas.height);
                ctx.stroke();
            });

            canvas.addEventListener("mousedown", startDrawing);
            canvas.addEventListener("mouseup", stopDrawing);
            canvas.addEventListener("mousemove", draw);
            canvas.addEventListener("touchstart", startDrawing);
            canvas.addEventListener("touchend", stopDrawing);
            canvas.addEventListener("touchmove", draw);

            canvasList.push(canvas);
        }

        createCanvas(false);

        eraserBtn.addEventListener("click", () => {
            erasing = !erasing;
            eraserBtn.textContent = erasing ? "Eraser ON" : "Eraser OFF";
            eraserBtn.style.background = erasing ? "red" : "gray";
        });

        addCanvasBtn.addEventListener("click", () => {
            createCanvas(true);
        });

        toggleMenuBtn.addEventListener("click", () => {
            buttonContainer.style.display = buttonContainer.style.display === "flex" ? "none" : "flex";
        });

        colorPicker.forEach(color => {
            color.addEventListener("click", () => {
                erasing = false;
                eraserBtn.textContent = "Eraser OFF";
                eraserBtn.style.background = "gray";
                penColor = color.getAttribute("data-color");
            });
        });

        saveCanvasBtn.addEventListener("click", () => {
            const canvas = canvasList[0];
            const data = canvas.toDataURL();
            fetch("/save", {
                method: "POST",
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ data })
            }).then(res => res.json()).then(res => alert("Saved with page ID: " + res.page_id));
        });

        loadPageBtn.addEventListener("click", () => {
            const id = loadPageInput.value;
            fetch(`/load/${id}`).then(res => res.json()).then(res => {
                const img = new Image();
                img.onload = () => {
                    const ctx = canvasList[0].getContext("2d");
                    ctx.clearRect(0, 0, canvasList[0].width, canvasList[0].height);
                    ctx.drawImage(img, 0, 0);
                };
                img.src = res.data;
            });
        });

        logoutBtn.addEventListener("click", () => {
            fetch("/logout").then(() => location.reload());
        });

        socket.on("add_canvas", () => {
            createCanvas(false);
        });
    </script>
</body>
</html>
"""

# New enhanced login/signup template
auth_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StylusSphere - Authentication</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        body {
            background: linear-gradient(135deg, #74ebd5, #ACB6E5);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            overflow: hidden;
        }
        
        .auth-container {
            background: rgba(255, 255, 255, 0.9);
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
            width: 400px;
            overflow: hidden;
            padding: 40px;
            text-align: center;
            animation: fadeIn 0.5s ease;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .logo {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 30px;
            color: #333;
        }
        
        .logo span {
            color: #4a90e2;
        }
        
        h2 {
            color: #333;
            margin-bottom: 30px;
            font-size: 24px;
        }
        
        .input-group {
            margin-bottom: 20px;
            position: relative;
        }
        
        input {
            width: 100%;
            padding: 15px;
            border: none;
            background: rgba(255, 255, 255, 0.8);
            border-radius: 10px;
            font-size: 16px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            border: 1px solid #eee;
        }
        
        input:focus {
            outline: none;
            box-shadow: 0 5px 15px rgba(74, 144, 226, 0.1);
            border-color: #4a90e2;
        }
        
        button {
            width: 100%;
            padding: 15px;
            border: none;
            background: #4a90e2;
            color: white;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 5px 15px rgba(74, 144, 226, 0.2);
            margin-top: 10px;
        }
        
        button:hover {
            background: #3a7bc8;
            transform: translateY(-2px);
            box-shadow: 0 7px 20px rgba(74, 144, 226, 0.3);
        }
        
        .switch-form {
            margin-top: 30px;
            color: #666;
        }
        
        .switch-form a {
            color: #4a90e2;
            text-decoration: none;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .switch-form a:hover {
            color: #3a7bc8;
            text-decoration: underline;
        }
        
        .decorative-shape {
            position: absolute;
            border-radius: 50%;
            z-index: -1;
            opacity: 0.5;
        }
        
        .shape1 {
            width: 300px;
            height: 300px;
            background: linear-gradient(45deg, #74ebd5, #74ebd5);
            top: -150px;
            left: -100px;
        }
        
        .shape2 {
            width: 200px;
            height: 200px;
            background: linear-gradient(45deg, #ACB6E5, #ACB6E5);
            bottom: -100px;
            right: -50px;
        }
        
        .error-message {
            color: #e74c3c;
            background-color: rgba(231, 76, 60, 0.1);
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="decorative-shape shape1"></div>
    <div class="decorative-shape shape2"></div>
    
    <div class="auth-container">
        <div class="logo">Stylus<span>Sphere</span></div>
        
        <!-- Login Form -->
        {% if request.path == '/login' %}
        <h2>Welcome Back</h2>
        {% if request.method == 'POST' %}
        <div class="error-message">Invalid credentials</div>
        {% endif %}
        <form method="POST">
            <div class="input-group">
                <input name="username" placeholder="Username" required />
            </div>
            <div class="input-group">
                <input name="password" type="password" placeholder="Password" required />
            </div>
            <button>Sign In</button>
        </form>
        <div class="switch-form">
            New user? <a href="/signup">Signup</a>
        </div>
        {% endif %}

        <!-- Signup Form -->
        {% if request.path == '/signup' %}
        <h2>Create Account</h2>
        {% if request.method == 'POST' %}
        <div class="error-message">User already exists</div>
        {% endif %}
        <form method="POST">
            <div class="input-group">
                <input name="username" placeholder="Choose a Username" required />
            </div>
            <div class="input-group">
                <input name="password" type="password" placeholder="Create a Password" required />
            </div>
            <button>Sign Up</button>
        </form>
        <div class="switch-form">
            Already have an account? <a href="/login">Login</a>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    if 'username' not in session:
        return redirect('/login')
    return render_template_string(html_template)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username] == password:
            session['username'] = username
            return redirect('/')
        return render_template_string(auth_template)
    return render_template_string(auth_template)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            return render_template_string(auth_template)
        users[username] = password
        user_drawings[username] = {}
        session['username'] = username
        return redirect('/')
    return render_template_string(auth_template)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/save', methods=['POST'])
def save():
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json['data']
    page_id = str(uuid.uuid4())[:8]
    user_drawings[session['username']][page_id] = data
    return jsonify({"page_id": page_id})

@app.route('/load/<page_id>')
def load(page_id):
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    drawings = user_drawings.get(session['username'], {})
    if page_id in drawings:
        return jsonify({"data": drawings[page_id]})
    return jsonify({"error": "Page not found"}), 404

@socketio.on('draw')
def handle_draw(data):
    emit('draw', data, broadcast=True)

@socketio.on('add_canvas')
def handle_add_canvas():
    emit('add_canvas', broadcast=True)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)






# from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
# from flask_socketio import SocketIO, emit
# from flask_cors import CORS
# import uuid

# app = Flask(__name__)
# app.secret_key = 'secretkey'
# socketio = SocketIO(app, cors_allowed_origins="*")
# CORS(app)

# # In-memory user store
# users = {}  # username: password
# user_drawings = {}  # username: {page_id: drawing_data}

# html_template = """
# <!DOCTYPE html>
# <html lang="en">
# <head>
#     <meta charset="UTF-8">
#     <meta name="viewport" content="width=device-width, initial-scale=1.0">
#     <title>Real-Time Drawing</title>
#     <style>
#         * { margin: 0; padding: 0; overflow: hidden; }
#         body { font-family: Arial, sans-serif; text-align: center; }
#         .canvas-container { position: relative; width: 100vw; height: 100vh; }
#         canvas { position: absolute; top: 0; left: 0; touch-action: none; background: white; }
#         .button-container {
#             position: fixed;
#             bottom: 20px;
#             left: 50%;
#             transform: translateX(-50%);
#             display: flex;
#             gap: 10px;
#             z-index: 1000;
#             flex-direction: column;
#             background: rgba(255, 255, 255, 0.9);
#             padding: 10px;
#             border-radius: 10px;
#             display: none;
#         }
#         button {
#             padding: 12px 20px;
#             font-size: 16px;
#             background: gray;
#             color: white;
#             border: none;
#             cursor: pointer;
#             border-radius: 8px;
#         }
#         #eraserBtn { background: gray; }
#         #addCanvasBtn { background: blue; }
#         #toggleMenuBtn {
#             position: fixed;
#             bottom: 20px;
#             right: 20px;
#             background: black;
#             color: white;
#             font-size: 24px;
#             width: 50px;
#             height: 50px;
#             border-radius: 50%;
#             text-align: center;
#             line-height: 50px;
#             cursor: pointer;
#             z-index: 2000;
#         }
#         .color-picker {
#             display: flex;
#             gap: 5px;
#         }
#         .color-picker div {
#             width: 30px;
#             height: 30px;
#             border-radius: 50%;
#             cursor: pointer;
#             border: 2px solid transparent;
#         }
#     </style>
# </head>
# <body>
#     <div id="toggleMenuBtn">☰</div>
#     <div class="button-container" id="buttonContainer">
#         <button id="eraserBtn">Eraser OFF</button>
#         <button id="addCanvasBtn">Add New Canvas</button>
#         <button id="saveCanvasBtn">Save Page</button>
#         <button id="logoutBtn">Logout</button>
#         <input id="loadPageInput" placeholder="Page ID" />
#         <button id="loadPageBtn">Load Page</button>
#         <div class="color-picker">
#             <div style="background: black;" data-color="black"></div>
#             <div style="background: red;" data-color="red"></div>
#             <div style="background: blue;" data-color="blue"></div>
#             <div style="background: green;" data-color="green"></div>
#             <div style="background: orange;" data-color="orange"></div>
#         </div>
#     </div>
#     <div class="canvas-container" id="canvasContainer">
#         <canvas class="drawingCanvas"></canvas>
#     </div>
#     <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.4.1/socket.io.js"></script>
#     <script>
#         const socket = io();
#         const canvasContainer = document.getElementById("canvasContainer");
#         const eraserBtn = document.getElementById("eraserBtn");
#         const addCanvasBtn = document.getElementById("addCanvasBtn");
#         const toggleMenuBtn = document.getElementById("toggleMenuBtn");
#         const buttonContainer = document.getElementById("buttonContainer");
#         const colorPicker = document.querySelectorAll(".color-picker div");
#         const saveCanvasBtn = document.getElementById("saveCanvasBtn");
#         const loadPageBtn = document.getElementById("loadPageBtn");
#         const loadPageInput = document.getElementById("loadPageInput");
#         const logoutBtn = document.getElementById("logoutBtn");
#         let canvasList = [];
#         let erasing = false;
#         let penColor = "black";

#         function createCanvas(sync = true) {
#             const canvas = document.createElement("canvas");
#             canvas.classList.add("drawingCanvas");
#             canvasContainer.appendChild(canvas);
#             setupCanvas(canvas);

#             if (sync) {
#                 socket.emit("add_canvas");
#             }
#         }

#         function setupCanvas(canvas) {
#             const ctx = canvas.getContext("2d");

#             function resizeCanvas() {
#                 canvas.width = window.innerWidth;
#                 canvas.height = window.innerHeight;
#             }
#             resizeCanvas();
#             window.addEventListener("resize", resizeCanvas);

#             let drawing = false;
#             let lastX = null, lastY = null;

#             function getPosition(e) {
#                 if (e.touches) {
#                     return { x: e.touches[0].clientX, y: e.touches[0].clientY };
#                 }
#                 return { x: e.clientX, y: e.clientY };
#             }

#             function startDrawing(e) {
#                 e.preventDefault();
#                 drawing = true;
#                 lastX = lastY = null;
#             }

#             function stopDrawing() {
#                 drawing = false;
#                 lastX = lastY = null;
#             }

#             function draw(e) {
#                 if (!drawing) return;
#                 e.preventDefault();

#                 let { x, y } = getPosition(e);

#                 ctx.lineWidth = erasing ? 20 : 3;
#                 ctx.strokeStyle = erasing ? "white" : penColor;

#                 if (lastX !== null && lastY !== null) {
#                     ctx.beginPath();
#                     ctx.moveTo(lastX, lastY);
#                     ctx.lineTo(x, y);
#                     ctx.stroke();

#                     socket.emit("draw", {
#                         lastX: lastX / canvas.width,
#                         lastY: lastY / canvas.height,
#                         x: x / canvas.width,
#                         y: y / canvas.height,
#                         erasing,
#                         color: penColor
#                     });
#                 }

#                 lastX = x;
#                 lastY = y;
#             }

#             socket.on("draw", (data) => {
#                 ctx.lineWidth = data.erasing ? 20 : 3;
#                 ctx.strokeStyle = data.erasing ? "white" : data.color;
#                 ctx.beginPath();
#                 ctx.moveTo(data.lastX * canvas.width, data.lastY * canvas.height);
#                 ctx.lineTo(data.x * canvas.width, data.y * canvas.height);
#                 ctx.stroke();
#             });

#             canvas.addEventListener("mousedown", startDrawing);
#             canvas.addEventListener("mouseup", stopDrawing);
#             canvas.addEventListener("mousemove", draw);
#             canvas.addEventListener("touchstart", startDrawing);
#             canvas.addEventListener("touchend", stopDrawing);
#             canvas.addEventListener("touchmove", draw);

#             canvasList.push(canvas);
#         }

#         createCanvas(false);

#         eraserBtn.addEventListener("click", () => {
#             erasing = !erasing;
#             eraserBtn.textContent = erasing ? "Eraser ON" : "Eraser OFF";
#             eraserBtn.style.background = erasing ? "red" : "gray";
#         });

#         addCanvasBtn.addEventListener("click", () => {
#             createCanvas(true);
#         });

#         toggleMenuBtn.addEventListener("click", () => {
#             buttonContainer.style.display = buttonContainer.style.display === "flex" ? "none" : "flex";
#         });

#         colorPicker.forEach(color => {
#             color.addEventListener("click", () => {
#                 erasing = false;
#                 eraserBtn.textContent = "Eraser OFF";
#                 eraserBtn.style.background = "gray";
#                 penColor = color.getAttribute("data-color");
#             });
#         });

#         saveCanvasBtn.addEventListener("click", () => {
#             const canvas = canvasList[0];
#             const data = canvas.toDataURL();
#             fetch("/save", {
#                 method: "POST",
#                 headers: { 'Content-Type': 'application/json' },
#                 body: JSON.stringify({ data })
#             }).then(res => res.json()).then(res => alert("Saved with page ID: " + res.page_id));
#         });

#         loadPageBtn.addEventListener("click", () => {
#             const id = loadPageInput.value;
#             fetch(`/load/${id}`).then(res => res.json()).then(res => {
#                 const img = new Image();
#                 img.onload = () => {
#                     const ctx = canvasList[0].getContext("2d");
#                     ctx.clearRect(0, 0, canvasList[0].width, canvasList[0].height);
#                     ctx.drawImage(img, 0, 0);
#                 };
#                 img.src = res.data;
#             });
#         });

#         logoutBtn.addEventListener("click", () => {
#             fetch("/logout").then(() => location.reload());
#         });

#         socket.on("add_canvas", () => {
#             createCanvas(false);
#         });
#     </script>
# </body>
# </html>
# """

# @app.route('/')
# def index():
#     if 'username' not in session:
#         return redirect('/login')
#     return render_template_string(html_template)

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if username in users and users[username] == password:
#             session['username'] = username
#             return redirect('/')
#         return 'Invalid credentials'
#     return '''<form method="POST"><h2>Login</h2><input name="username" /><input name="password" type="password"/><button>Login</button></form>
#     <p>New user? <a href="/signup">Signup</a></p>'''


# @app.route('/signup', methods=['GET', 'POST'])
# def signup():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         if username in users:
#             return 'User already exists'
#         users[username] = password
#         user_drawings[username] = {}
#         session['username'] = username
#         return redirect('/')
#     return '''<form method="POST"><h2>Signup</h2><input name="username" /><input name="password" type="password"/><button>Signup</button></form>'''


# @app.route('/logout')
# def logout():
#     session.clear()
#     return redirect('/login')

# @app.route('/save', methods=['POST'])
# def save():
#     if 'username' not in session:
#         return jsonify({"error": "Unauthorized"}), 401
#     data = request.json['data']
#     page_id = str(uuid.uuid4())[:8]
#     user_drawings[session['username']][page_id] = data
#     return jsonify({"page_id": page_id})

# @app.route('/load/<page_id>')
# def load(page_id):
#     if 'username' not in session:
#         return jsonify({"error": "Unauthorized"}), 401
#     drawings = user_drawings.get(session['username'], {})
#     if page_id in drawings:
#         return jsonify({"data": drawings[page_id]})
#     return jsonify({"error": "Page not found"}), 404

# @socketio.on('draw')
# def handle_draw(data):
#     emit('draw', data, broadcast=True)

# @socketio.on('add_canvas')
# def handle_add_canvas():
#     emit('add_canvas', broadcast=True)

# if __name__ == "__main__":
#     socketio.run(app, host="0.0.0.0", port=5000)