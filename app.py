from flask import Flask, request, redirect, url_for, flash, send_from_directory, render_template_string
from werkzeug.utils import secure_filename
import os
import requests
from datetime import datetime
import urllib.parse

BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_CONTENT_LENGTH = 8 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = os.environ.get('FLASK_SECRET', 'change_this_secret')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_submission(form, files):
    errors = []

    tg = form.get('telegram', '').strip()
    if not tg:
        errors.append('Telegram Username/ID is required.')

    uid = form.get('uid', '').strip()
    if not uid:
        errors.append('Free Fire UID is required.')
    else:
        if not uid.isdigit():
            errors.append('Free Fire UID must be a number.')
        else:
            val = int(uid)
            if val < 10000001 or val > 1500000000000:
                errors.append('Free Fire UID must be between 10000001 and 1500000000000.')

    r1 = form.get('round1_code', '').strip()
    if not r1:
        errors.append('Round 1 Map Code is required.')
    else:
        if not r1.startswith('#FREEFIRE'):
            errors.append('Round 1 Map Code must start with #FREEFIRE.')

    r3 = form.get('round3_code', '').strip()
    if not r3:
        errors.append('Round 3 Map Code is required.')
    else:
        if not r3.startswith('#FREEFIRE'):
            errors.append('Round 3 Map Code must start with #FREEFIRE.')

    r2 = form.get('round2_code', '').strip()
    r2_file = files.get('round2_file')
    file_provided = r2_file and r2_file.filename != ''

    if not r2 and not file_provided:
        errors.append('Round 2 requires either a Map Code or a Screenshot.')
    else:
        if r2:
            if not r2.startswith('#FREEFIRE'):
                errors.append('Round 2 Map Code must start with #FREEFIRE if provided.')
        if file_provided:
            if not allowed_file(r2_file.filename):
                errors.append('Uploaded Round 2 screenshot must be an image (png/jpg/jpeg/gif/webp).')

    tc1 = form.get('tc1')
    tc2 = form.get('tc2')
    tc3 = form.get('tc3')
    if not (tc1 and tc2 and tc3):
        errors.append('You must check all three Terms & Conditions boxes.')

    return errors

FORM_HTML = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DeadDOS Free Fire Craftmate - Submission</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background: #f5f5f7;
    }
    .card {
      border-radius: 1rem;
    }
    .form-section {
      padding: 1rem;
      border-radius: 0.75rem;
      background: #ffffff;
      box-shadow: 0 0.25rem 0.5rem rgba(0,0,0,0.1);
      margin-bottom: 1rem;
    }
    .btn-primary {
      background: linear-gradient(90deg,#ff5858,#f857a6);
      border: none;
    }
    .btn-primary:hover {
      opacity: 0.9;
    }
    .form-check-label {
      cursor: pointer;
    }
    .input-group-text {
      background-color: #f0f0f0;
    }
  </style>
</head>
<body>
  <div class="container py-5">
    <div class="row justify-content-center">
      <div class="col-lg-8 col-md-10 col-sm-12">
        <div class="card shadow-sm p-4">
          <h2 class="mb-4 text-center">DeadDOS Free Fire Craftmate</h2>
          <p class="text-center text-muted mb-4">Submit your entries for Craftmate below</p>

          {% with messages = get_flashed_messages() %}
            {% if messages %}
              <div class="alert alert-danger">
                <ul class="mb-0">
                {% for m in messages %}
                  <li>{{ m }}</li>
                {% endfor %}
                </ul>
              </div>
            {% endif %}
          {% endwith %}

          <form method="post" action="{{ url_for('submit') }}" enctype="multipart/form-data">

            <!-- Telegram & UID -->
            <div class="form-section">
              <h5>Account Details</h5>
              <div class="mb-3">
                <label class="form-label">Telegram Username/ID</label>
                <input class="form-control" name="telegram" placeholder="Enter your Telegram username or ID" value="{{ formdata.telegram if formdata else '' }}" required>
                <div class="form-text">If no username, enter numeric Telegram ID</div>
              </div>

              <div class="mb-3">
                <label class="form-label">Free Fire UID</label>
                <input class="form-control" id="uid_value" name="uid" type="number" min="10000001" max="1500000000000" placeholder="12345678" value="{{ formdata.uid if formdata else '' }}" required>
                <div class="form-text">Prizes will be delivered to this UID.</div>
                <div id="uid_info" class="mt-2 small text-muted"></div>
              </div>
            </div>

            <!-- Round 1 -->
            <div class="form-section">
              <h5>Round 1: Object Designing</h5>
              <div class="mb-3">
                <label class="form-label">Map Code</label>
                <input class="form-control" id="round1_code" name="round1_code" placeholder="#FREEFIRE..." value="{{ formdata.round1_code if formdata else '' }}" required>
                <div id="round1_info" class="mt-2 small text-muted"></div>
              </div>
            </div>

            <!-- Round 2 -->
            <div class="form-section">
              <h5>Round 2: Scripting</h5>
              <div class="btn-group mb-3" role="group">
                <input type="radio" class="btn-check" name="round2_choice" id="choiceCode" value="code" checked>
                <label class="btn btn-outline-primary" for="choiceCode">Use Map Code</label>
                <input type="radio" class="btn-check" name="round2_choice" id="choiceScreenshot" value="screenshot">
                <label class="btn btn-outline-primary" for="choiceScreenshot">Upload Screenshot</label>
              </div>

              <input class="form-control mb-2" id="round2_code" name="round2_code" placeholder="#FREEFIRE..." value="{{ formdata.round2_code if formdata else '' }}">
              <input class="form-control d-none" id="round2_file" name="round2_file" type="file" accept="image/*">

              <div id="round2_info" class="mt-2 small text-muted"></div>
            </div>

            <!-- Round 3 -->
            <div class="form-section">
              <h5>Round 3: Environment Designing</h5>
              <div class="mb-3">
                <label class="form-label">Map Code</label>
                <input class="form-control" id="round3_code" name="round3_code" placeholder="#FREEFIRE..." value="{{ formdata.round3_code if formdata else '' }}" required>
                <div id="round3_info" class="mt-2 small text-muted"></div>
              </div>
            </div>

            <!-- Terms -->
            <div class="form-section">
              <h5>Terms & Conditions</h5>
              <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" id="tc1" name="tc1">
                <label class="form-check-label" for="tc1">I have read and understood the rules of this contest.</label>
              </div>
              <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" id="tc2" name="tc2">
                <label class="form-check-label" for="tc2">I solemnly affirm that my entry follows the UGC Policies of Garena.</label>
              </div>
              <div class="form-check mb-2">
                <input class="form-check-input" type="checkbox" id="tc3" name="tc3">
                <label class="form-check-label" for="tc3">The information submitted through this form is true and accurate.</label>
              </div>
            </div>

            <button class="btn btn-primary w-100 py-2 mt-3" type="submit">Submit</button>
          </form>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
<script>
document.addEventListener("DOMContentLoaded", () => {
  const codeRadio = document.getElementById("choiceCode");
  const screenshotRadio = document.getElementById("choiceScreenshot");
  const codeInput = document.getElementById("round2_code");
  const fileInput = document.getElementById("round2_file");

  function toggleInputs() {
    if (codeRadio.checked) {
      codeInput.classList.remove("d-none");
      fileInput.classList.add("d-none");
      fileInput.value = "";
    } else {
      fileInput.classList.remove("d-none");
      codeInput.classList.add("d-none");
      codeInput.value = "";
    }
  }

  codeRadio.addEventListener("change", toggleInputs);
  screenshotRadio.addEventListener("change", toggleInputs);

  toggleInputs(); // run once on load
});

async function fetchMapInfo(inputId, infoId, region="ind") {
  const code = document.getElementById(inputId).value.trim();
  const infoBox = document.getElementById(infoId);
  if (!code.startsWith("#FREEFIRE")) {
    infoBox.innerHTML = "<span class='text-danger'>Code must start with #FREEFIRE</span>";
    return;
  }
  try {
    infoBox.innerHTML = "Loading...";
    const res = await fetch(`/map_info?code=${encodeURIComponent(code)}&region=ind`);
    const data = await res.json();
    if (data.map_info) {
      const m = data.map_info;
    infoBox.innerHTML = `
      <div class="alert alert-info p-2 mt-2">
        <b>${m.map_name}</b><br>
        Creator: ${m.nickname}<br>
        Likes: ${m.liked}, Subs: ${m.subscriptions}<br>
        UID: ${m.uid}
      </div>
    `;
    } else {
      infoBox.innerHTML = "<span class='text-danger'>Not found</span>";
    }
  } catch (err) {
    infoBox.innerHTML = "<span class='text-danger'>Error fetching info</span>";
  }
}

function debounce(fn, delay) {
  let timer = null;
  return function(...args) {
    clearTimeout(timer);
    timer = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

async function fetchAccountInfoDebounced(inputId, infoId, region="ind") {
  const uid = document.getElementById(inputId).value.trim();
  const infoBox = document.getElementById(infoId);
  if (!uid) {
    infoBox.innerHTML = "";
    return;
  }

  try {
    infoBox.innerHTML = "Loading...";
    const res = await fetch(`/account_info?uid=${uid}&region=${region}`);
    const data = await res.json();
    if (data.basicInfo) {
      const m = data.basicInfo;
      infoBox.innerHTML = `
        <div class="alert alert-info p-2 mt-2">
          <b>${m.nickname}</b><br>
          Lv.${m.level}
        </div>
      `;
    } else {
      infoBox.innerHTML = "<span class='text-danger'>Not found</span>";
    }
  } catch (err) {
    infoBox.innerHTML = "<span class='text-danger'>Error fetching info</span>";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const uidInput = document.getElementById("uid_value");
  const uidInfo = "uid_info";
  if (uidInput) {
    const debouncedFetch = debounce(() => fetchAccountInfoDebounced("uid_value", uidInfo), 1000);
    uidInput.addEventListener("input", debouncedFetch);
    uidInput.addEventListener("blur", () => fetchAccountInfoDebounced("uid_value", uidInfo)); // fetch on blur too
  }

  // Map info remains real-time
  ["round1_code","round2_code","round3_code"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", () => {
        fetchMapInfo(id, `${id.replace("_code","")}_info`);
      });
    }
  });
});

</script>
</html>
'''

@app.route('/')
def index():
    return render_template_string(FORM_HTML)

@app.route('/account_info')
def account_info():
    uid = request.args.get('uid', '').strip()
    region = request.args.get('region', 'ind')
    if not uid:
        return {"error": "Missing UID"}, 400

    url = f"https://ff.deaddos.online/api/data?region={region}&uid={uid}&key=Craftmate"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/140.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        try:
            data = r.json()
        except Exception:
            return {"error": "Failed to parse JSON", "status_code": r.status_code, "text": r.text}, 500
        return data, r.status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/map_info')
def map_info():
    code = request.args.get('code', '').strip()
    region = request.args.get('region', 'ind')
    if not code.startswith('#FREEFIRE'):
        return {"error": "Invalid map code"}, 400

    encoded_code = urllib.parse.quote(code, safe='')
    url = f"https://map-info.craftland.ff.deaddos.online/api/{region}?code={encoded_code}&key=Craftmate"
    app.logger.info(f"Fetching map info: {url}")
    try:
        r = requests.get(url, timeout=10)
        app.logger.info(f"Craftland API status: {r.status_code}, body: {r.text[:200]}")
        return r.json(), r.status_code
    except Exception as e:
        return {"error": str(e)}, 500


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/submit', methods=['POST'])
def submit():
    form = request.form
    files = request.files

    errors = validate_submission(form, files)
    if errors:
        for e in errors:
            flash(e)
        return render_template_string(FORM_HTML, formdata=form)

    r2_file = files.get('round2_file')
    saved_filename = None
    if r2_file and r2_file.filename != '':
        filename = secure_filename(r2_file.filename)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{filename}"
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        r2_file.save(save_path)
        saved_filename = filename

    telegram_username = form.get('telegram').strip()
    uid = form.get('uid').strip()
    round1 = form.get('round1_code').strip()
    round2 = form.get('round2_code').strip()
    round3 = form.get('round3_code').strip()

    text = (
        f"<b>New Craftmate Submission</b>\n"
        f"<b>Telegram:</b> {telegram_username}\n"
        f"<b>Free Fire UID:</b> {uid}\n"
        f"<b>Round 1 Map Code:</b> {round1}\n"
        f"<b>Round 2 Map Code:</b> {round2 if round2 else '(not provided)'}\n"
        f"<b>Round 3 Map Code:</b> {round3}\n"
        f"<b>Screenshot attached:</b> {'Yes' if saved_filename else 'No'}\n"
        f"<b>Timestamp (UTC):</b> {datetime.utcnow().isoformat()}"
    )

    send_ok = send_telegram_message(BOT_TOKEN, CHAT_ID, text)

    if saved_filename:
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
        send_telegram_photo(BOT_TOKEN, CHAT_ID, photo_path, caption=f"Screenshot from {telegram_username}")

    if not send_ok:
        flash('Failed to send message to Telegram. Please contact the admin.')
        return redirect(url_for('index'))

    return render_template_string('''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Submission Successful</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {
      background: #f5f5f7;
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100vh;
      text-align: center;
    }
    .card {
      padding: 2rem;
      border-radius: 1rem;
      box-shadow: 0 0.25rem 0.5rem rgba(0,0,0,0.1);
      background: #ffffff;
    }
    .btn-home {
      margin-top: 1.5rem;
      background: linear-gradient(90deg,#ff5858,#f857a6);
      border: none;
      color: white;
    }
    .btn-home:hover {
      opacity: 0.9;
    }
  </style>
</head>
<body>
  <div class="card">
    <h3 class="mb-3">✅ Your entry has been submitted successfully!</h3>
    <p class="text-muted">Thank you for participating in the DeadDOS Free Fire Craftmate.</p>
    <a href="/" class="btn btn-home">Submit Another Entry</a>
  </div>
</body>
</html>
''')

TELEGRAM_API = 'https://api.telegram.org/bot{token}/{method}'

def send_telegram_message(token, chat_id, text):
    url = TELEGRAM_API.format(token=token, method='sendMessage')
    try:
        r = requests.post(url, data={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }, timeout=10)
        return r.status_code == 200 and r.json().get('ok')
    except Exception as e:
        app.logger.exception('Error sending Telegram message: %s', e)
        return False

def send_telegram_photo(token, chat_id, photo_path, caption=None):
    url = TELEGRAM_API.format(token=token, method='sendPhoto')
    try:
        with open(photo_path, 'rb') as f:
            files = {'photo': f}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
                data['parse_mode'] = 'HTML'
            r = requests.post(url, data=data, files=files, timeout=20)
            return r.status_code == 200 and r.json().get('ok')
    except Exception as e:
        app.logger.exception('Error sending photo to Telegram: %s', e)
        return False

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)